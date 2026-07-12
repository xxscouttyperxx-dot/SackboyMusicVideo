import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "hoodie_bowl_ridge_polish_v1"
REP = ROOT / "reports" / "hoodie_bowl_ridge_polish_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
PRIMARY_HOODIE_NAME = "SACKBOY_Hoodie_Main"
OLD_HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]
PREV_HOODIE_KEYS = [
    "HOODIEFIT_TopArtifactFix_v1",
    "HOODIEFIT_RimCrownContain_v1",
    "HOODIEFIT_CrownSmoothExpand_v1",
    "HOODIEFIT_CrownSleeveTaper_v1",
    "HOODIEFIT_NarrowSackboy_v1",
]
NEW_HOODIE_KEY = "HOODIEFIT_BowlRidgePolish_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "HoodieBowlRidgePolish_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "HoodieBowlRidgePolish_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

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

def key_world_bounds(obj, key=None):
    coords = []
    if key:
        coords = [obj.matrix_world @ p.co for p in key.data]
    elif obj.type == "MESH":
        coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    else:
        return bounds_world(obj)
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center_from_bounds(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def band(zn, a, b, c, d):
    return smoothstep(a, b, zn) * (1.0 - smoothstep(c, d, zn))

def radial(dx, dy, rx, ry):
    r = (dx/max(rx,1e-6))**2 + (dy/max(ry,1e-6))**2
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

def find_hoodie_candidates():
    matches = []
    for obj in bpy.data.objects:
        lname = obj.name.lower()
        if obj.type == "MESH" and ("hoodie" in lname or "pullover" in lname or "apricot" in lname):
            matches.append(obj)
    # Prefer named main or old exact name first, then visible/highest vertex count.
    ordered = []
    for name in OLD_HOODIE_NAMES:
        o = bpy.data.objects.get(name)
        if o and o.type == "MESH" and o not in ordered:
            ordered.append(o)
    for o in sorted(matches, key=lambda x: (not visible(x), -len(x.data.vertices), x.name)):
        if o not in ordered:
            ordered.append(o)
    return ordered

def rename_hoodies():
    cands = find_hoodie_candidates()
    if not cands:
        raise RuntimeError("No hoodie/apricot/pullover mesh object found.")
    main = cands[0]
    renames = []
    if main.name != PRIMARY_HOODIE_NAME:
        old = main.name
        main.name = PRIMARY_HOODIE_NAME
        main.data.name = PRIMARY_HOODIE_NAME + "_Mesh"
        renames.append({"old": old, "new": main.name, "role": "main"})
    else:
        renames.append({"old": main.name, "new": main.name, "role": "main_already_named"})

    idx = 1
    for obj in cands[1:]:
        old = obj.name
        target = f"SACKBOY_Hoodie_Duplicate_{idx:02d}"
        if obj.name != target:
            obj.name = target
            obj.data.name = target + "_Mesh"
        renames.append({"old": old, "new": obj.name, "role": "duplicate"})
        idx += 1
    log(f"[rename] hoodie objects renamed/standardized: {renames}")
    return main, renames

def ensure_hoodie_key(obj):
    if obj.type != "MESH":
        raise RuntimeError(f"{obj.name} is not a mesh")
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

def apply_bowl_ridge_polish(hoodie, hero):
    key, source = ensure_hoodie_key(hoodie)
    lb = bounds_from_key_data(key)
    before_world = key_world_bounds(hoodie, key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    hb = bounds_world(hero) if hero else None
    hcenter = center_from_bounds(hb) if hb else None
    head_top = hb["max_z"] if hb else None
    inv = hoodie.matrix_world.inverted()

    touched = 0
    max_delta = 0.0
    counts = {"ridge_rounded": 0, "bowl_concavity_shaped": 0, "rim_vertical_kept": 0, "transition_feathered": 0}
    vertex_count_before = len(hoodie.data.vertices)
    face_count_before = len(hoodie.data.polygons)

    for point in key.data:
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        # Localize this pass to hood/rim/top only.
        top_cap = band(zn, 0.78, 0.86, 1.0, 1.0)
        ridge_zone = band(zn, 0.70, 0.78, 0.96, 1.0)
        bowl_zone = band(zn, 0.58, 0.66, 0.90, 1.0)
        rim_zone = band(zn, 0.42, 0.52, 0.78, 0.90)
        transition = band(zn, 0.50, 0.58, 0.82, 0.94)

        center = radial(nx, ny, 0.74, 0.86)
        wide_center = radial(nx, ny, 1.05, 1.08)
        rim_edge = smoothstep(0.42, 0.88, max(nx, ny * 0.72))

        new = co.copy()

        # Build a smoother concave bowl: vertical rim walls higher, center gently domed/rounded,
        # and no sharp ridge line at the crown.
        rim_weight = rim_zone * (0.35 + 0.65 * wide_center)
        if rim_weight > 0.0:
            new.z += dz * 0.045 * rim_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.035 * rim_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.050 * rim_weight)

        bowl_weight = bowl_zone * wide_center
        if bowl_weight > 0.0:
            # Expand sides and lift the center so the hood reads like a rounded concave bowl.
            new.x = cx + (new.x - cx) * (1.0 + 0.022 * bowl_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.032 * bowl_weight)
            new.z += dz * 0.020 * bowl_weight

        ridge_weight = ridge_zone * (0.45 + 0.55 * center)
        if ridge_weight > 0.0:
            # Round down/up hard ridge into a smoother cap.
            new.z += dz * 0.050 * ridge_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.018 * ridge_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.026 * ridge_weight)

        cap_weight = top_cap * center
        if cap_weight > 0.0:
            new.z += dz * 0.040 * cap_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.012 * cap_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.018 * cap_weight)

        # Head-top clearance only if a crown point is still below a safe head-top cushion.
        if head_top is not None and hcenter and (top_cap > 0.02 or ridge_zone > 0.08 or bowl_zone > 0.18):
            world_before = hoodie.matrix_world @ co
            dx = abs(world_before.x - hcenter.x) / max(hb["dim_x"] * 0.42, 0.35)
            dy = abs(world_before.y - hcenter.y) / max(hb["dim_y"] * 0.46, 0.35)
            head_xy = max(0.0, 1.0 - min(1.0, dx*dx + dy*dy))
            if head_xy > 0.04:
                world_new = hoodie.matrix_world @ new
                target_z = head_top + 0.100 + 0.055 * head_xy
                if world_new.z < target_z:
                    blend = min(1.0, 0.45 + 0.55 * head_xy)
                    world_new.z = world_new.z * (1.0 - blend) + target_z * blend
                    new = inv @ world_new

        # Feather the lower slope so the bowl is not separated by a hard band.
        trans_weight = transition * wide_center
        if trans_weight > 0.0:
            new.z += dz * 0.012 * trans_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.010 * trans_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.014 * trans_weight)

        delta = (new - co).length
        if delta > 1e-7:
            if ridge_weight > 0.08 or cap_weight > 0.08: counts["ridge_rounded"] += 1
            if bowl_weight > 0.08: counts["bowl_concavity_shaped"] += 1
            if rim_weight > 0.08: counts["rim_vertical_kept"] += 1
            if trans_weight > 0.08: counts["transition_feathered"] += 1
            point.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    after_world = key_world_bounds(hoodie, key)
    vertex_count_after = len(hoodie.data.vertices)
    face_count_after = len(hoodie.data.polygons)
    hoodie["hoodie_fit_pass"] = "HoodieBowlRidgePolish_v1"
    hoodie["hoodie_fit_shape_key"] = NEW_HOODIE_KEY
    log(f"[hoodie] added active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; max_delta_local={max_delta:.6f}; vertices={vertex_count_before}->{vertex_count_after}; faces={face_count_before}->{face_count_after}")
    return {
        "shape_key": NEW_HOODIE_KEY,
        "source_key": source,
        "value": 1.0,
        "touched_vertices": touched,
        "max_delta_local": max_delta,
        "vertex_count_before": vertex_count_before,
        "vertex_count_after": vertex_count_after,
        "face_count_before": face_count_before,
        "face_count_after": face_count_after,
        "world_dimensions_before": [round(before_world["dim_x"],6), round(before_world["dim_y"],6), round(before_world["dim_z"],6)],
        "world_dimensions_after": [round(after_world["dim_x"],6), round(after_world["dim_y"],6), round(after_world["dim_z"],6)],
        "region_counts": counts,
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
    log("[render] focused hoodie cameras: hood top, overhead, rim/bowl, and one scene preservation view")

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

def render_review(hoodie):
    scene = bpy.context.scene
    # Camera target based on hoodie bounds, not F2.
    kb = hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY) if hoodie.data.shape_keys else None
    hb = key_world_bounds(hoodie, kb)
    center = center_from_bounds(hb)
    hood_top = Vector((center.x, center.y, hb["min_z"] + hb["dim_z"] * 0.82))
    rim_center = Vector((center.x, center.y, hb["min_z"] + hb["dim_z"] * 0.66))

    setups = [
        ("CAM_REVIEW_HoodieTop_Close", (hood_top.x + 0.45, hood_top.y - 2.05, hood_top.z + 0.95), hood_top, 92, "01_HoodieTopClose.png"),
        ("CAM_REVIEW_HoodieTop_Overhead", (hood_top.x + 0.05, hood_top.y - 0.35, hood_top.z + 2.85), hood_top, 82, "02_HoodieTopOverhead.png"),
        ("CAM_REVIEW_HoodieBowl_RimProfile", (rim_center.x + 2.75, rim_center.y - 0.45, rim_center.z + 0.75), rim_center, 86, "03_HoodieBowlRimProfile.png"),
        ("CAM_REVIEW_HoodieScenePreserved", (center.x + 4.8, center.y - 7.2, center.z + 1.2), center + Vector((0,1.2,0.15)), 46, "04_HoodieScenePreserved.png"),
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

def write_reports(hoodie_fit, renamed, disabled_bodyfit, under, cams):
    payload = {
        "pass": "hoodie_bowl_ridge_polish_v1",
        "renamed_hoodie_objects": renamed,
        "hoodie_fit": hoodie_fit,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in [HERO_NAME, PRIMARY_HOODIE_NAME, "SACKBOY_Hoodie_Duplicate_01", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Cameras are now targeted from the hoodie bounds rather than F2 bounds.",
            "This pass focuses on rounding/feathering the top ridge and shaping the hood into a cleaner concave bowl.",
            "Vertex and face counts are reported; this shape-key pass does not add/remove topology."
        ],
        "next_goals": ["If the ridge is resolved, proceed to pants/shoes.", "If ridge remains, next step should be manual/local topology or material/surface investigation."]
    }
    (REP / "hoodie_bowl_ridge_polish_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "HoodieBowlRidgePolish_status.json").write_text(json.dumps({"ok": True, "hoodie_shape_key": NEW_HOODIE_KEY, "touched_vertices": hoodie_fit.get("touched_vertices"), "vertices": [hoodie_fit.get("vertex_count_before"), hoodie_fit.get("vertex_count_after")], "faces": [hoodie_fit.get("face_count_before"), hoodie_fit.get("face_count_after")], "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Bowl Ridge Polish v1",
        "",
        "## Changes",
        f"- Renamed the main hoodie object to **{PRIMARY_HOODIE_NAME}**.",
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        "- Repositioned focused cameras using the hoodie bounds instead of F2 bounds.",
        "- Rounded/feathered the top hood ridge.",
        "- Shaped the hood toward a cleaner concave bowl around Sackboy's head.",
        "- Kept the hood rim vertically open.",
        "- Kept F2 restored/baseline with all BODYFIT keys disabled.",
        "",
        "## Dimensional / topology data",
        f"- Hoodie vertices: {hoodie_fit.get('vertex_count_before')} -> {hoodie_fit.get('vertex_count_after')}",
        f"- Hoodie faces: {hoodie_fit.get('face_count_before')} -> {hoodie_fit.get('face_count_after')}",
        f"- World dimensions before: {hoodie_fit.get('world_dimensions_before')}",
        f"- World dimensions after: {hoodie_fit.get('world_dimensions_after')}",
        "",
        "## Camera rule applied",
        "- Three cameras focus on the hoodie top/rim/bowl.",
        "- One wider camera checks scene preservation.",
    ]
    (REP / "Hoodie_Bowl_Ridge_Polish_v1.md").write_text("\n".join(md), encoding="utf-8")

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
        "# Scene Layout Summary\n\nUpdated by Hoodie Bowl Ridge Polish v1.\n\n"
        "- Main hoodie renamed to SACKBOY_Hoodie_Main.\n"
        "- Focused hoodie bowl/ridge corrective shape key added.\n"
        "- Review cameras target hoodie bounds plus one preservation view.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_bowl_ridge_polish_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] hoodie bowl ridge polish v1")
    hoodie, renamed = rename_hoodies()
    hero = bpy.data.objects.get(HERO_NAME)
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    setup_render_settings()
    hoodie_fit = apply_bowl_ridge_polish(hoodie, hero)
    cams = render_review(hoodie)
    write_reports(hoodie_fit, renamed, disabled_bodyfit, under, cams)
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
        with (OUT / "HoodieBowlRidgePolish_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
