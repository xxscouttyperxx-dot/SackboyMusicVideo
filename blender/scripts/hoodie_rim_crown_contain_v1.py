import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "hoodie_rim_crown_contain_v1"
REP = ROOT / "reports" / "hoodie_rim_crown_contain_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "Apricot Pullover Hoodie"
PREV_HOODIE_KEYS = ["HOODIEFIT_CrownSmoothExpand_v1", "HOODIEFIT_CrownSleeveTaper_v1", "HOODIEFIT_NarrowSackboy_v1"]
NEW_HOODIE_KEY = "HOODIEFIT_RimCrownContain_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "HoodieRimCrownContain_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "HoodieRimCrownContain_report.txt").write_text("", encoding="utf-8")

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
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

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

def radial(nx, ny, sx, sy):
    r = (nx/max(sx,1e-6))**2 + (ny/max(sy,1e-6))**2
    return max(0.0, 1.0 - min(1.0, r))

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

def keep_character_baseline():
    hero = bpy.data.objects.get(HERO_NAME)
    disabled = []
    if hero and hero.type == "MESH" and hero.data.shape_keys:
        for kb in hero.data.shape_keys.key_blocks:
            if kb.name.startswith("BODYFIT_"):
                before = float(kb.value)
                kb.value = 0.0
                disabled.append({"name": kb.name, "before": round(before,4), "after": 0.0})
    log("[character] F2 baseline preserved; BODYFIT keys kept disabled")
    return disabled

def ensure_hoodie_key(obj):
    if obj.type != "MESH":
        raise RuntimeError(f"{HOODIE_NAME} is not a mesh")
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    if obj.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
        bpy.ops.object.shape_key_remove()

    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value = 0.0

    source = None
    for key_name in PREV_HOODIE_KEYS:
        kb = obj.data.shape_keys.key_blocks.get(key_name)
        if kb:
            kb.value = 1.0
            source = key_name
            break

    new_key = obj.shape_key_add(name=NEW_HOODIE_KEY, from_mix=True)

    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value = 0.0
    new_key.value = 1.0
    obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
    return new_key, source

def apply_rim_crown_containment(hoodie, hero):
    key, source = ensure_hoodie_key(hoodie)
    lb = bounds_from_key_data(key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    hb = bounds_world(hero) if hero else None
    world_head_top = hb["max_z"] if hb else None
    world_head_center = center_from_bounds(hb) if hb else None
    world_head_radius_x = max(hb["dim_x"] * 0.34, 0.18) if hb else 0.55
    world_head_radius_y = max(hb["dim_y"] * 0.38, 0.18) if hb else 0.55

    inv = hoodie.matrix_world.inverted()
    touched = 0
    max_delta = 0.0
    counts = {"rim_stretched_vertical": 0, "crown_lifted_over_head": 0, "top_artifact_covered": 0, "transition_feathered": 0, "sleeve_elbow_smooth_kept": 0}

    for point in key.data:
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny = abs((co.y - cy) / hy)

        crown = band(zn, 0.66, 0.76, 1.00, 1.00)
        crown_cap = band(zn, 0.78, 0.88, 1.00, 1.00)
        crown_transition = band(zn, 0.52, 0.62, 0.82, 0.93)
        rim_band = band(zn, 0.45, 0.56, 0.75, 0.88)
        sleeve_elbow = band(zn, 0.24, 0.30, 0.50, 0.58)

        center_weight = radial(nx, ny, 0.92, 1.05)
        rim_weight = rim_band * (0.45 + 0.55 * center_weight)
        cap_weight = crown_cap * radial(nx, ny, 0.72, 0.88)
        crown_weight = crown * radial(nx, ny, 1.0, 1.1)
        trans_weight = crown_transition * center_weight

        new = co.copy()

        # Stretch the hood opening/rim vertically and proportionally.
        if rim_weight > 0.0:
            new.z += dz * 0.060 * rim_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.040 * rim_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.055 * rim_weight)

        # Crown containment: expand/lift a little more without an abrupt band.
        if crown_weight > 0.0:
            new.z += dz * 0.060 * crown_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.050 * crown_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.070 * crown_weight)

        # Top cap fill: raise center of the hood top to hide the red head/show-through artifact.
        if cap_weight > 0.0:
            new.z += dz * 0.075 * cap_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.035 * cap_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.045 * cap_weight)

        # Use actual F2 head top as a minimum clearance reference for upper central hood points.
        # This helps when the head is visibly poking through the crown.
        world_before = hoodie.matrix_world @ co
        world_new = hoodie.matrix_world @ new
        if hb and world_head_center:
            dx = abs(world_before.x - world_head_center.x) / world_head_radius_x
            dy = abs(world_before.y - world_head_center.y) / world_head_radius_y
            head_xy = max(0.0, 1.0 - min(1.0, dx*dx + dy*dy))
            cover_weight = max(crown_weight, cap_weight) * head_xy
            if cover_weight > 0.0:
                target_z = world_head_top + 0.045 + 0.055 * cover_weight
                if world_new.z < target_z:
                    world_new.z = world_new.z * (1.0 - cover_weight) + target_z * cover_weight
                    new = inv @ world_new

        # Feather the slope below the expanded crown to reduce banding/indentations.
        if trans_weight > 0.0:
            new.z += dz * 0.025 * trans_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.025 * trans_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.030 * trans_weight)

        # Preserve and slightly improve elbow valley smoothing.
        outer = smoothstep(0.46, 0.88, nx)
        sleeve_centerline = 1.0 - smoothstep(0.22, 0.72, ny)
        elbow_fill = sleeve_elbow * outer * sleeve_centerline
        if elbow_fill > 0:
            new.z += dz * 0.018 * elbow_fill
            side_center_x = cx + (1 if nx_signed > 0 else -1) * hx * 0.60
            new.x = side_center_x + (new.x - side_center_x) * (1.0 - 0.055 * elbow_fill)
            new.y = cy + (new.y - cy) * (1.0 - 0.045 * elbow_fill)

        delta = (new - co).length
        if delta > 1e-7:
            if rim_weight > 0.08: counts["rim_stretched_vertical"] += 1
            if crown_weight > 0.08: counts["crown_lifted_over_head"] += 1
            if cap_weight > 0.08: counts["top_artifact_covered"] += 1
            if trans_weight > 0.08: counts["transition_feathered"] += 1
            if elbow_fill > 0.08: counts["sleeve_elbow_smooth_kept"] += 1
            point.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    hoodie["hoodie_fit_pass"] = "HoodieRimCrownContain_v1"
    hoodie["hoodie_fit_shape_key"] = NEW_HOODIE_KEY
    log(f"[hoodie] added active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; max_delta_local={max_delta:.6f}; head_top_world={world_head_top}")
    return {"shape_key": NEW_HOODIE_KEY, "source_key": source, "value": 1.0, "touched_vertices": touched, "max_delta_local": max_delta,
            "head_top_world": world_head_top, "region_counts": counts, "local_bounds_after": bounds_from_key_data(key)}

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
            "vertices": len(o.data.vertices) if o.type == "MESH" else 0, "faces": len(o.data.polygons) if o.type == "MESH" else 0,
            "shape_keys": shape_keys, "modifiers": [{"name": m.name, "type": m.type} for m in o.modifiers], "collections": [c.name for c in o.users_collection]}

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x: x.name):
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
    log("[render] Cycles review renders retained; viewport preview samples remain low")

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
    hoodie = bpy.data.objects.get(HOODIE_NAME)
    hb = bounds_world(hero) or bounds_world(hoodie)
    target = center_from_bounds(hb) if hb else Vector((0,0,1.4))
    if hb:
        target.z = hb["min_z"] + hb["dim_z"] * 0.62

    setups = [
        ("CAM_REVIEW_HoodRimFront", (target.x, target.y - 5.8, target.z + 0.95), target + Vector((0,0,0.28)), 62, "01_HoodRimFront.png"),
        ("CAM_REVIEW_HoodRimProfile", (target.x + 4.8, target.y - 0.8, target.z + 0.95), target + Vector((0,0,0.25)), 70, "02_HoodRimProfile.png"),
        ("CAM_REVIEW_HoodTopArtifactCheck", (target.x + 1.0, target.y - 3.8, target.z + 1.55), target + Vector((0,0,0.55)), 72, "03_HoodTopArtifactCheck.png"),
        ("CAM_REVIEW_StorefrontReflection", (target.x + 7.8, target.y - 10.0, target.z + 1.4), (target.x, target.y + 4.2, target.z + 0.9), 48, "04_StorefrontReflectionPreserved.png"),
    ]
    old = scene.camera
    cams = []
    for name, loc, tgt, lens, fn in setups:
        cam = make_or_update_cam(name, loc, tgt, lens)
        cams.append({"name": name, "render": fn, "loc": [round(cam.location.x,6), round(cam.location.y,6), round(cam.location.z,6)], "lens": lens})
        scene.camera = cam
        scene.render.filepath = str(OUT / fn)
        bpy.ops.render.render(write_still=True)
        log("[render] " + fn)
    scene.camera = old
    return cams

def copy_current_review():
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR / p.name).write_bytes(p.read_bytes())

def write_reports(hoodie_fit, disabled_bodyfit, under, cams):
    payload = {
        "pass": "hoodie_rim_crown_contain_v1",
        "hoodie_fit": hoodie_fit,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Screenshots showed the hood crown/top artifact and visible head/show-through at the top.",
            "This pass stretches the hood rim vertically and uses F2 head top as a clearance reference for upper central hood points.",
            "F2 baseline remains unchanged."
        ],
        "next_goals": ["If the hood rim/crown is clean, move to pants and shoes.", "If a tiny top artifact remains, do a final local top-cap polish only."]
    }
    (REP / "hoodie_rim_crown_contain_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "HoodieRimCrownContain_status.json").write_text(json.dumps({"ok": True, "hoodie_shape_key": NEW_HOODIE_KEY, "touched_vertices": hoodie_fit.get("touched_vertices"), "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Rim Crown Contain v1",
        "",
        "## Changes",
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        "- Stretched the hood rim vertically and proportionally so it better frames Sackboy's large head.",
        "- Lifted and expanded the crown cap using F2's actual head top as a clearance reference.",
        "- Feathered the transition below the crown to avoid banded indentations.",
        "- Preserved the sleeve elbow smoothing from the previous pass.",
        "- Kept F2 restored/baseline with all BODYFIT keys disabled.",
        "",
        "## Next package goal",
        "- If the top artifact is gone, move to pants and shoes.",
        "- If a tiny top artifact remains, do a very local top-cap polish only.",
    ]
    (REP / "Hoodie_Rim_Crown_Contain_v1.md").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render), "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(o)
        item = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection], "visible": visible(o), "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)], "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
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
        "# Scene Layout Summary\n\nUpdated by Hoodie Rim Crown Contain v1.\n\n"
        "- Added hoodie rim/crown containment shape key.\n"
        "- F2 remains restored baseline; BODYFIT keys disabled.\n"
        "- Preserved reflection setup and approved scene lighting.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_rim_crown_contain_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] hoodie rim crown contain v1")
    hoodie = bpy.data.objects.get(HOODIE_NAME)
    if not hoodie:
        raise RuntimeError(f"{HOODIE_NAME} object was not found")
    hero = bpy.data.objects.get(HERO_NAME)
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    setup_render_settings()
    hoodie_fit = apply_rim_crown_containment(hoodie, hero)
    cams = render_review()
    write_reports(hoodie_fit, disabled_bodyfit, under, cams)
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
        with (OUT / "HoodieRimCrownContain_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
