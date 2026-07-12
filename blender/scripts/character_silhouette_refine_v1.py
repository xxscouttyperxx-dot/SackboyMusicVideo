import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "character_silhouette_refine_v1"
REP = ROOT / "reports" / "character_silhouette_refine_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
PREV_KEYS = ["BODYFIT_TorsoHoodFit_v1", "BODYFIT_HoodiePantsPrep_v1"]
NEW_KEY = "BODYFIT_SilhouetteRefine_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "CharacterSilhouetteRefine_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "CharacterSilhouetteRefine_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def band(zn, a, b, c, d):
    return smoothstep(a, b, zn) * (1.0 - smoothstep(c, d, zn))

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def bounds_from_key_data(key):
    coords = [p.co for p in key.data]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center_from_bounds(b):
    return Vector(((b["min_x"] + b["max_x"]) * 0.5, (b["min_y"] + b["max_y"]) * 0.5, (b["min_z"] + b["max_z"]) * 0.5))

def restore_underglow():
    o = bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log("[lock] underglow missing")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after}

def ensure_shape_key_stack(obj):
    if obj.type != "MESH":
        raise RuntimeError(f"{HERO_NAME} is not a mesh")
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    # deterministic reruns
    key_blocks = obj.data.shape_keys.key_blocks
    if key_blocks.get(NEW_KEY):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = key_blocks.keys().index(NEW_KEY)
        bpy.ops.object.shape_key_remove()

    for kb in obj.data.shape_keys.key_blocks:
        kb.value = 0.0

    chosen = None
    for k in PREV_KEYS:
        kb = obj.data.shape_keys.key_blocks.get(k)
        if kb:
            kb.value = 1.0
            chosen = k
            break

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    new_key = obj.shape_key_add(name=NEW_KEY, from_mix=True)

    for kb in obj.data.shape_keys.key_blocks:
        kb.value = 0.0
    new_key.value = 1.0
    obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(NEW_KEY)
    return new_key, chosen

def apply_silhouette_refine(obj):
    key, source_key = ensure_shape_key_stack(obj)
    lb = bounds_from_key_data(key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    # approximate centers for separate limbs
    left_hand_cx = cx - hx * 0.78
    right_hand_cx = cx + hx * 0.78
    hand_cy = cy
    left_leg_cx = cx - hx * 0.34
    right_leg_cx = cx + hx * 0.34
    leg_cy = cy

    touched = 0
    max_delta = 0.0
    region_counts = {
        "torso_gut_flattened": 0,
        "legs_thinned": 0,
        "hands_reduced": 0,
        "nose_face_flattened": 0,
        "head_hood_clearance": 0
    }

    for p in key.data:
        co = p.co.copy()
        zn = (co.z - zmin) / dz
        nx = abs((co.x - cx) / hx)
        ny = abs((co.y - cy) / hy)

        torso = band(zn, 0.25, 0.32, 0.57, 0.66)
        upper_torso = band(zn, 0.42, 0.50, 0.66, 0.76)
        head = band(zn, 0.62, 0.69, 0.96, 1.0)
        face = band(zn, 0.67, 0.73, 0.86, 0.93)
        lower = band(zn, 0.06, 0.12, 0.37, 0.45)
        hands = band(zn, 0.22, 0.28, 0.60, 0.67)
        legs = band(zn, 0.02, 0.08, 0.33, 0.40)

        central = (1.0 - smoothstep(0.50, 0.98, nx)) * (1.0 - smoothstep(0.78, 1.05, ny))
        face_center = (1.0 - smoothstep(0.18, 0.42, nx)) * (1.0 - smoothstep(0.36, 0.76, ny))
        head_center = (1.0 - smoothstep(0.38, 0.82, nx)) * (1.0 - smoothstep(0.52, 0.96, ny))

        new = co.copy()

        # Stronger torso thinning / gut flattening
        x_reduce = central * (0.10 * torso + 0.06 * upper_torso + 0.05 * lower)
        y_reduce = central * (0.22 * torso + 0.14 * upper_torso + 0.09 * lower)
        new.x = cx + (new.x - cx) * (1.0 - x_reduce)
        new.y = cy + (new.y - cy) * (1.0 - y_reduce)

        # Slight vertical settle to soften belly / chest volume
        if torso > 0 and central > 0:
            new.z -= dz * 0.010 * torso * central

        # Head/hood clearance overall
        if head > 0 and head_center > 0:
            new.x = cx + (new.x - cx) * (1.0 - 0.025 * head * head_center)
            new.y = cy + (new.y - cy) * (1.0 - 0.085 * head * head_center)
            new.z -= dz * 0.007 * head * head_center

        # Face / "snout" flattening
        if face > 0 and face_center > 0:
            new.y = cy + (new.y - cy) * (1.0 - 0.16 * face * face_center)
            new.x = cx + (new.x - cx) * (1.0 - 0.03 * face * face_center)

        # Thinner legs using per-leg centers so the gap stays more natural
        if legs > 0.01 and lower > 0.01 and nx > 0.10:
            leg_center_x = left_leg_cx if co.x < cx else right_leg_cx
            leg_local = 1.0 - smoothstep(0.0, 0.85, abs((co.x - leg_center_x) / max(hx*0.22, 1e-6)))
            leg_depth = 1.0 - smoothstep(0.0, 0.9, abs((co.y - leg_cy) / max(hy*0.40, 1e-6)))
            leg_w = legs * max(leg_local, 0.0) * max(leg_depth, 0.0)
            if leg_w > 0:
                new.x = leg_center_x + (new.x - leg_center_x) * (1.0 - 0.16 * leg_w)
                new.y = leg_cy + (new.y - leg_cy) * (1.0 - 0.18 * leg_w)

        # Smaller Sackboy-like hands
        if hands > 0.01 and nx > 0.70:
            hand_center_x = left_hand_cx if co.x < cx else right_hand_cx
            hand_local = 1.0 - smoothstep(0.0, 1.0, abs((co.x - hand_center_x) / max(hx*0.24, 1e-6)))
            hand_depth = 1.0 - smoothstep(0.0, 1.0, abs((co.y - hand_cy) / max(hy*0.36, 1e-6)))
            hand_vert = 1.0 - smoothstep(0.0, 1.0, abs(zn - 0.43) / 0.22)
            hw = max(hand_local, 0.0) * max(hand_depth, 0.0) * max(hand_vert, 0.0)
            if hw > 0:
                new.x = hand_center_x + (new.x - hand_center_x) * (1.0 - 0.14 * hw)
                new.y = hand_cy + (new.y - hand_cy) * (1.0 - 0.14 * hw)
                wrist_mid = zmin + dz * 0.43
                new.z = wrist_mid + (new.z - wrist_mid) * (1.0 - 0.08 * hw)

        delta = (new - co).length
        if delta > 1e-7:
            if torso > 0.15: region_counts["torso_gut_flattened"] += 1
            if legs > 0.15 and lower > 0.08: region_counts["legs_thinned"] += 1
            if hands > 0.15 and nx > 0.70: region_counts["hands_reduced"] += 1
            if face > 0.12 and face_center > 0.10: region_counts["nose_face_flattened"] += 1
            if head > 0.12 and head_center > 0.10: region_counts["head_hood_clearance"] += 1
            p.co = new
            touched += 1
            if delta > max_delta:
                max_delta = delta

    obj["body_fit_pass"] = "CharacterSilhouetteRefine_v1"
    obj["body_fit_shape_key"] = NEW_KEY
    log(f"[body] added active shape key {NEW_KEY}; source_key={source_key}; touched_vertices={touched}; max_delta_local={max_delta:.6f}")
    return {
        "shape_key": NEW_KEY,
        "value": 1.0,
        "source_key": source_key,
        "touched_vertices": touched,
        "max_delta_local": max_delta,
        "region_counts": region_counts,
        "local_bounds_after": bounds_from_key_data(key)
    }

def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {"name": name, "status": "missing"}
    b = bounds_world(o)
    shape_keys = []
    if o.type == "MESH" and o.data.shape_keys:
        shape_keys = [{"name": kb.name, "value": round(float(kb.value), 4)} for kb in o.data.shape_keys.key_blocks]
    return {"name": name, "status": "present", "type": o.type, "visible": visible(o),
            "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "vertices": len(o.data.vertices) if o.type == "MESH" else 0,
            "faces": len(o.data.polygons) if o.type == "MESH" else 0,
            "shape_keys": shape_keys,
            "collections": [c.name for c in o.users_collection]}

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type, "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def setup_render_settings():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.samples = 80
        scene.cycles.preview_samples = 12
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.glossy_bounces = 4
    except Exception:
        pass
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    log("[render] kept Cycles for review; preview samples remain lowered for viewport sanity")

def look_at(o, target):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def make_or_update_cam(name, loc, target, lens):
    cam = bpy.data.objects.get(name)
    if not cam or cam.type != "CAMERA":
        data = bpy.data.cameras.new(name + "_Data")
        cam = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    return cam

def render_review():
    scene = bpy.context.scene
    hero = bpy.data.objects.get(HERO_NAME)
    hb = bounds_world(hero)
    target = center_from_bounds(hb) if hb else Vector((0,0,1.4))
    if hb:
        target.z = hb["min_z"] + hb["dim_z"] * 0.50

    setups = [
        ("CAM_REVIEW_Silhouette_Front", (target.x, target.y - 6.0, target.z + 0.45), target, 58, "01_SilhouetteFront.png"),
        ("CAM_REVIEW_Silhouette_Profile", (target.x + 5.2, target.y - 0.8, target.z + 0.42), target, 62, "02_ProfileGutLegHand.png"),
        ("CAM_REVIEW_Face_Hands", (target.x + 1.65, target.y - 3.25, target.z + 1.42), (target.x, target.y - 0.1, target.z + 1.05), 70, "03_FaceHandCheck.png"),
        ("CAM_REVIEW_StorefrontReflection", (target.x + 7.8, target.y - 10.0, target.z + 1.4), (target.x, target.y + 4.2, target.z + 0.9), 48, "04_StorefrontReflectionCamera.png"),
    ]
    made = []
    old = scene.camera
    for name, loc, tgt, lens, fn in setups:
        cam = make_or_update_cam(name, loc, tgt, lens)
        made.append({"name": name, "render": fn, "loc": [round(cam.location.x,6), round(cam.location.y,6), round(cam.location.z,6)], "lens": lens})
        scene.camera = cam
        scene.render.filepath = str(OUT / fn)
        bpy.ops.render.render(write_still=True)
        log("[render] " + fn)
    scene.camera = old
    return made

def copy_current_review():
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR / p.name).write_bytes(p.read_bytes())

def write_reports(body, under, cams):
    payload = {
        "pass": "character_silhouette_refine_v1",
        "body_deformation": body,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in ["F2", "Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "next_goals": [
            "Deform hoodie around the new slimmer torso and reduced head depth",
            "Fit pants and shoes after hoodie clearance approval",
            "Preserve current reflections and approved lighting",
            "Rig only after body/clothing fit approval"
        ]
    }
    (REP / "character_silhouette_refine_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "CharacterSilhouetteRefine_status.json").write_text(json.dumps({"ok": True, "shape_key": NEW_KEY, "touched_vertices": body.get("touched_vertices"), "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Character Silhouette Refine v1",
        "",
        "## Changes",
        f"- Added active non-destructive shape key **{NEW_KEY}**.",
        "- Source body-fit key was duplicated into the new key first, then refined.",
        "- Reduced torso/gut thickness more aggressively.",
        "- Thinned the legs with a separate per-leg reduction so they read closer to the arms.",
        "- Reduced hand volume to feel smaller and more Sackboy-like.",
        "- Flattened the face/nose area so it does not read like a snout.",
        "- Preserved the reflection setup and lighting.",
        "",
        "## Next goals",
        "- Deform/fit the hoodie to the refined body.",
        "- Fit pants and shoes.",
        "- Keep current scene look locked.",
    ]
    (REP / "Character_Silhouette_Refine_v1.md").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render),
                                    "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(o)
        item = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection],
                "visible": visible(o), "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
        if o.type == "MESH":
            item["vertices"] = len(o.data.vertices)
            item["faces"] = len(o.data.polygons)
            if o.data.shape_keys:
                item["shape_keys"] = [{"name": kb.name, "value": round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
        if o.type == "LIGHT":
            item["energy"] = getattr(o.data, "energy", None)
            item["color"] = [round(v,6) for v in getattr(o.data, "color", [])] if hasattr(o.data, "color") else None
        if o.type == "CAMERA" and o.name.startswith("CAM_REVIEW_"):
            item["review_camera"] = True
        data["objects"].append(item)
    (ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\nUpdated by Character Silhouette Refine v1.\n\n"
        "- Added stronger silhouette/face/hand body-fit shape key on F2.\n"
        "- Preserved reflection setup and traffic light concept.\n"
        "- Review cameras retained, including storefront reflection view.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "character_silhouette_refine_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] character silhouette refine v1")
    hero = bpy.data.objects.get(HERO_NAME)
    if not hero:
        raise RuntimeError("F2 character mesh was not found")
    under = restore_underglow()
    setup_render_settings()
    body = apply_silhouette_refine(hero)
    cams = render_review()
    write_reports(body, under, cams)
    copy_current_review()
    manifest()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / "CharacterSilhouetteRefine_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
