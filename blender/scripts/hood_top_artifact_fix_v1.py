import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "hood_top_artifact_fix_v1"
REP = ROOT / "reports" / "hood_top_artifact_fix_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "Apricot Pullover Hoodie"
PREV_HOODIE_KEYS = ["HOODIEFIT_RimCrownContain_v1", "HOODIEFIT_CrownSmoothExpand_v1", "HOODIEFIT_CrownSleeveTaper_v1", "HOODIEFIT_NarrowSackboy_v1"]
NEW_HOODIE_KEY = "HOODIEFIT_TopArtifactFix_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "HoodTopArtifactFix_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "HoodTopArtifactFix_report.txt").write_text("", encoding="utf-8")

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

def radial(dx, dy, rx, ry):
    r = (dx / max(rx, 1e-6))**2 + (dy / max(ry, 1e-6))**2
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

def apply_top_artifact_fix(hoodie, hero):
    key, source = ensure_hoodie_key(hoodie)
    lb = bounds_from_key_data(key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    hb = bounds_world(hero) if hero else None
    hcenter = center_from_bounds(hb) if hb else None
    head_top = hb["max_z"] if hb else None
    head_rx = max(hb["dim_x"] * 0.42, 0.35) if hb else 0.7
    head_ry = max(hb["dim_y"] * 0.46, 0.35) if hb else 0.7

    inv = hoodie.matrix_world.inverted()

    touched = 0
    max_delta = 0.0
    counts = {"hard_clearance_lift": 0, "top_cap_dome": 0, "rim_kept_open": 0, "slope_feathered": 0}
    min_clearance_before = None
    min_clearance_after = None

    # Conservative, local-only correction:
    # focus on high crown/top cap and the vertical hood rim, not sleeve, torso, pants, or character body.
    for point in key.data:
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        top_cap = band(zn, 0.76, 0.84, 1.00, 1.00)
        upper_crown = band(zn, 0.66, 0.74, 0.94, 1.00)
        rim = band(zn, 0.46, 0.55, 0.76, 0.88)
        transition = band(zn, 0.55, 0.63, 0.82, 0.92)

        world_before = hoodie.matrix_world @ co
        head_xy = 0.0
        if hcenter:
            head_xy = radial(world_before.x - hcenter.x, world_before.y - hcenter.y, head_rx, head_ry)

        local_center = radial(nx, ny, 0.82, 0.92)
        central_top = max(head_xy, local_center) * top_cap
        central_crown = max(head_xy, local_center) * upper_crown
        rim_weight = rim * (0.35 + 0.65 * local_center)
        transition_weight = transition * (0.35 + 0.65 * local_center)

        new = co.copy()

        # 1) Actual clearance fix: hood top must sit above the F2 head top in the central head zone.
        if head_top is not None and head_xy > 0.06 and (top_cap > 0.02 or upper_crown > 0.08):
            target_z = head_top + 0.145 + 0.055 * head_xy
            if min_clearance_before is None or (world_before.z - head_top) < min_clearance_before:
                min_clearance_before = world_before.z - head_top
            world_new = hoodie.matrix_world @ new
            if world_new.z < target_z:
                # Pull fully to the target for the central area; blend only toward edges.
                force = min(1.0, 0.55 + 0.65 * head_xy)
                world_new.z = world_new.z * (1.0 - force) + target_z * force
                new = inv @ world_new

        # 2) Dome the top cap so it does not leave a central dip.
        if central_top > 0.0:
            new.z += dz * 0.055 * central_top
            new.x = cx + (new.x - cx) * (1.0 + 0.020 * central_top)
            new.y = cy + (new.y - cy) * (1.0 + 0.030 * central_top)

        # 3) Keep rim vertically stretched, but this is not a broad resculpt.
        if rim_weight > 0.0:
            new.z += dz * 0.035 * rim_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.020 * rim_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.030 * rim_weight)

        # 4) Feather the slope below the lifted top to avoid creating a new band.
        if transition_weight > 0.0:
            new.z += dz * 0.018 * transition_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.012 * transition_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.018 * transition_weight)

        if head_top is not None:
            world_after = hoodie.matrix_world @ new
            if hcenter and head_xy > 0.06 and (top_cap > 0.02 or upper_crown > 0.08):
                if min_clearance_after is None or (world_after.z - head_top) < min_clearance_after:
                    min_clearance_after = world_after.z - head_top

        delta = (new - co).length
        if delta > 1e-7:
            if head_xy > 0.06 and (top_cap > 0.02 or upper_crown > 0.08): counts["hard_clearance_lift"] += 1
            if central_top > 0.08: counts["top_cap_dome"] += 1
            if rim_weight > 0.08: counts["rim_kept_open"] += 1
            if transition_weight > 0.08: counts["slope_feathered"] += 1
            point.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    hoodie["hoodie_fit_pass"] = "HoodTopArtifactFix_v1"
    hoodie["hoodie_fit_shape_key"] = NEW_HOODIE_KEY
    log(f"[hoodie] added active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; max_delta_local={max_delta:.6f}; clearance_before={min_clearance_before}; clearance_after={min_clearance_after}")
    return {"shape_key": NEW_HOODIE_KEY, "source_key": source, "value": 1.0, "touched_vertices": touched, "max_delta_local": max_delta,
            "head_top_world": head_top, "min_clearance_before": min_clearance_before, "min_clearance_after": min_clearance_after,
            "region_counts": counts, "local_bounds_after": bounds_from_key_data(key)}

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
            "shape_keys": shape_keys, "modifiers": [{"name": m.name, "type": m.type} for m in o.modifiers],
            "collections": [c.name for c in o.users_collection]}

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
        scene.cycles.samples = 96
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
    log("[render] focused hood artifact review renders; one preservation camera kept")

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
        target.z = hb["min_z"] + hb["dim_z"] * 0.70

    # New rule: mostly focused cameras for the current work area, plus one scene preservation view.
    setups = [
        ("CAM_REVIEW_HoodTop_Artifact_Close", (target.x + 0.55, target.y - 2.2, target.z + 1.25), target + Vector((0,0,0.45)), 88, "01_HoodArtifactClose.png"),
        ("CAM_REVIEW_HoodTop_Overhead", (target.x + 0.15, target.y - 0.9, target.z + 3.05), target + Vector((0,0,0.65)), 78, "02_HoodTopOverhead.png"),
        ("CAM_REVIEW_HoodRim_ProfileClose", (target.x + 3.15, target.y - 0.65, target.z + 0.85), target + Vector((0,0,0.38)), 82, "03_HoodRimProfileClose.png"),
        ("CAM_REVIEW_CharacterScenePreserved", (target.x + 4.6, target.y - 7.8, target.z + 1.25), (target.x, target.y + 1.4, target.z + 0.2), 46, "04_CharacterScenePreserved.png"),
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
        "pass": "hood_top_artifact_fix_v1",
        "hoodie_fit": hoodie_fit,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Focused-only pass for the hood-top artifact.",
            "Uses F2 head top and XY head footprint as a direct clearance reference.",
            "Cameras are mostly close-up hood/top/rim views plus one broader preservation view."
        ],
        "next_goals": ["If fixed, resume lower clothing fit.", "If still visible, use manual/local mesh editing rather than another broad procedural deformation."]
    }
    (REP / "hood_top_artifact_fix_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "HoodTopArtifactFix_status.json").write_text(json.dumps({"ok": True, "hoodie_shape_key": NEW_HOODIE_KEY, "touched_vertices": hoodie_fit.get("touched_vertices"), "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Hood Top Artifact Fix v1",
        "",
        "## Changes",
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        "- Focused exclusively on the hood-top red/show-through artifact and rim clearance.",
        "- Used F2 head top plus XY head footprint as a stronger clearance reference.",
        "- Domed the top cap and kept the hood rim vertically open.",
        "- Feathered the slope below the lifted top to avoid banding.",
        "- Kept F2 restored/baseline with all BODYFIT keys disabled.",
        "",
        "## Camera rule applied",
        "- Three close-up cameras focus on the hood artifact/rim.",
        "- One wider camera checks character/scene preservation.",
    ]
    (REP / "Hood_Top_Artifact_Fix_v1.md").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render), "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(o)
        item = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection], "visible": visible(o), "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)], "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
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
        "# Scene Layout Summary\n\nUpdated by Hood Top Artifact Fix v1.\n\n"
        "- Focused hood-top artifact corrective shape key added to hoodie.\n"
        "- F2 remains restored baseline; BODYFIT keys disabled.\n"
        "- Cameras now prioritize the active deformation area plus one preservation view.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hood_top_artifact_fix_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] hood top artifact fix v1")
    hoodie = bpy.data.objects.get(HOODIE_NAME)
    if not hoodie:
        raise RuntimeError(f"{HOODIE_NAME} object was not found")
    hero = bpy.data.objects.get(HERO_NAME)
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    setup_render_settings()
    hoodie_fit = apply_top_artifact_fix(hoodie, hero)
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
        with (OUT / "HoodTopArtifactFix_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
