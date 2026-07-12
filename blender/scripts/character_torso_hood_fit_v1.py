import json, traceback, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "character_torso_hood_fit_v1"
REP = ROOT / "reports" / "character_torso_hood_fit_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
PREV_KEY = "BODYFIT_HoodiePantsPrep_v1"
NEW_KEY = "BODYFIT_TorsoHoodFit_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "CharacterTorsoHoodFit_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "CharacterTorsoHoodFit_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center_from_bounds(b):
    return Vector(((b["min_x"] + b["max_x"]) * 0.5, (b["min_y"] + b["max_y"]) * 0.5, (b["min_z"] + b["max_z"]) * 0.5))

def bounds_from_key_data(key):
    coords = [p.co for p in key.data]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def band(zn, a, b, c, d):
    return smoothstep(a, b, zn) * (1.0 - smoothstep(c, d, zn))

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

    # Remove old v2 so reruns are deterministic.
    existing = obj.data.shape_keys.key_blocks.get(NEW_KEY)
    if existing:
        obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(NEW_KEY)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shape_key_remove()

    # Capture the current approved body-fit if v1 exists, then move to a new v2 key.
    for kb in obj.data.shape_keys.key_blocks:
        kb.value = 0.0
    prev = obj.data.shape_keys.key_blocks.get(PREV_KEY)
    if prev:
        prev.value = 1.0

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    new_key = obj.shape_key_add(name=NEW_KEY, from_mix=True)

    # Keep v2 as the active body-fit key so edits do not stack unpredictably.
    for kb in obj.data.shape_keys.key_blocks:
        kb.value = 0.0
    new_key.value = 1.0
    obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(NEW_KEY)
    return new_key, bool(prev)

def apply_torso_hood_fit(obj):
    new_key, included_prev = ensure_shape_key_stack(obj)
    lb = bounds_from_key_data(new_key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    touched = 0
    max_delta = 0.0
    regions = {"torso_significant_thickness_reduction": 0, "hood_head_depth_clearance": 0, "neck_shoulder_settle": 0, "lower_body_pants_prep": 0, "protected_hands": 0}

    for i, point in enumerate(new_key.data):
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx = abs((co.x - cx) / hx)
        ny = abs((co.y - cy) / hy)

        # Keep hand region protected. The user wants body/clothing work, not another hand pass.
        if 0.22 < zn < 0.62 and nx > 0.70:
            regions["protected_hands"] += 1
            continue

        central = (1.0 - smoothstep(0.56, 0.96, nx)) * (1.0 - smoothstep(0.82, 1.08, ny))
        torso = band(zn, 0.26, 0.33, 0.57, 0.68)
        upper_torso = band(zn, 0.43, 0.50, 0.66, 0.75)
        head = band(zn, 0.58, 0.66, 0.95, 1.00)
        lower = band(zn, 0.08, 0.15, 0.35, 0.45)
        neck = band(zn, 0.53, 0.58, 0.70, 0.78)

        new = co.copy()

        # Stronger central body fit: less thick/deep so hoodie/pants can wrap easier.
        x_reduce = central * (0.10 * torso + 0.055 * upper_torso + 0.035 * head + 0.06 * lower)
        y_reduce = central * (0.22 * torso + 0.13 * upper_torso + 0.12 * head + 0.08 * lower)
        new.x = cx + (co.x - cx) * (1.0 - x_reduce)
        new.y = cy + (co.y - cy) * (1.0 - y_reduce)

        # Hood clearance: lower/settle the neck and rear-ish head volume by reducing depth and slightly compressing height.
        if neck > 0 and central > 0:
            new.z -= dz * 0.020 * neck * central
        if head > 0 and central > 0:
            new.z -= dz * 0.006 * head * central

        delta = (new - co).length
        if delta > 1e-7:
            touched += 1
            max_delta = max(max_delta, delta)
            if torso > 0.1: regions["torso_significant_thickness_reduction"] += 1
            if head > 0.1: regions["hood_head_depth_clearance"] += 1
            if neck > 0.1 or upper_torso > 0.1: regions["neck_shoulder_settle"] += 1
            if lower > 0.1: regions["lower_body_pants_prep"] += 1
            point.co = new

    obj["body_fit_pass"] = "CharacterTorsoHoodFit_v1"
    obj["body_fit_shape_key"] = NEW_KEY
    log(f"[body] added active shape key {NEW_KEY}; included_previous_v1={included_prev}; touched_vertices={touched}; max_delta_local={max_delta:.6f}")
    return {"shape_key": NEW_KEY, "value": 1.0, "included_previous_v1": included_prev, "touched_vertices": touched, "max_delta_local": max_delta, "regions": regions, "local_bounds_after_v1": lb}

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
            "shape_keys": shape_keys, "collections": [c.name for c in o.users_collection]}

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type, "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)], "energy": getattr(d, "energy", None),
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
        scene.cycles.diffuse_bounces = 1
        scene.cycles.glossy_bounces = 4
    except Exception:
        pass
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    log("[render] Cycles review renders enabled; viewport preview samples lowered to 12")

def look_at(o, target):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def make_cam(name, loc, target, lens):
    data = bpy.data.cameras.new(name + "_Data")
    cam = bpy.data.objects.new(name, data)
    cam.location = Vector(loc)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    bpy.context.scene.collection.objects.link(cam)
    return cam

def render_review():
    scene = bpy.context.scene
    hero = bpy.data.objects.get(HERO_NAME)
    hb = bounds_world(hero)
    target = center_from_bounds(hb) if hb else Vector((0,0,1.4))
    if hb:
        target.z = hb["min_z"] + hb["dim_z"] * 0.52

    # Dedicated review cameras so the user can manually render later from Blender.
    cameras = [
        ("CAM_REVIEW_BodyFit_Front", (target.x, target.y - 6.2, target.z + 0.45), target, 58, "01_BodyFitStrongerFront.png"),
        ("CAM_REVIEW_BodyFit_Profile", (target.x + 5.0, target.y - 1.2, target.z + 0.45), target, 62, "02_BodyFitProfileThickness.png"),
        ("CAM_REVIEW_ClothingClearance", (target.x + 3.4, target.y - 6.0, target.z + 0.70), target, 55, "03_HoodiePantsClearance.png"),
        ("CAM_REVIEW_StorefrontReflection", (target.x + 7.8, target.y - 10.0, target.z + 1.4), (target.x, target.y + 4.2, target.z + 0.9), 48, "04_StorefrontReflectionCamera.png"),
    ]
    old = scene.camera
    made = []
    for name, loc, tgt, lens, fn in cameras:
        cam = bpy.data.objects.get(name)
        if not cam or cam.type != "CAMERA":
            cam = make_cam(name, loc, tgt, lens)
        else:
            cam.location = Vector(loc)
            cam.data.lens = lens
            look_at(cam, Vector(tgt))
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
    key_names = ["F2", "Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]
    payload = {"pass": "character_torso_hood_fit_v1", "body_deformation": body, "underglow_lock": under, "review_cameras": cams,
               "key_objects": [object_report(n) for n in key_names], "lights_scan": scan_lights(),
               "next_goals": ["Fit hoodie shell around the newly slimmer body", "Fit cargo pants and shoes", "Keep reflection scene locked", "Rig only after visual fit approval"]}
    (REP / "character_torso_hood_fit_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "CharacterTorsoHoodFit_status.json").write_text(json.dumps({"ok": True, "shape_key": NEW_KEY, "touched_vertices": body.get("touched_vertices"), "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    lines = [
        "# Character Torso Hood Fit v1",
        "",
        "## Changes",
        f"- Added active non-destructive shape key: **{NEW_KEY}**",
        "- Includes the previous body prep shape in this new key, then disables the old key to avoid unpredictable stacking.",
        "- Significantly reduced torso thickness/depth for hoodie clearance.",
        "- Further reduced head/neck depth because the back of the head will live inside the hood.",
        "- Slightly narrowed lower body for pants fit.",
        "- Protected hand zones; no intentional hand sculpting.",
        "- Added review cameras, including **CAM_REVIEW_StorefrontReflection** for checking background/storefront reflections.",
        "",
        "## Next package goals",
        "- Fit/deform the hoodie around this new body shape.",
        "- Fit cargo pants and shoes after hoodie clearance looks acceptable.",
        "- Keep current reflection, car, asphalt, sky, underglow, and approved lighting locked.",
    ]
    (REP / "Character_Torso_Hood_Fit_v1.md").write_text("\n".join(lines), encoding="utf-8")

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
            item["vertices"] = len(o.data.vertices); item["faces"] = len(o.data.polygons)
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
        "# Scene Layout Summary\n\nUpdated by Character Torso Hood Fit v1.\n\n"
        "- Added stronger active F2 body-fit shape key for hoodie/pants prep.\n"
        "- Added persistent review cameras, including storefront reflection review.\n"
        "- Preserved current reflection setup and scene lighting.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "character_torso_hood_fit_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] character torso hood fit v1")
    hero = bpy.data.objects.get(HERO_NAME)
    if not hero:
        raise RuntimeError("F2 character mesh was not found")
    under = restore_underglow()
    setup_render_settings()
    body = apply_torso_hood_fit(hero)
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
        with (OUT / "CharacterTorsoHoodFit_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
