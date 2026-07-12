import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "hoodie_bowl_rim_refine_v1"
REP = ROOT / "reports" / "hoodie_bowl_rim_refine_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "SACKBOY_Hoodie_Main"
FALLBACK_HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]
PREV_HOODIE_KEYS = [
    "HOODIEFIT_BowlRidgePolish_v1",
    "HOODIEFIT_TopArtifactFix_v1",
    "HOODIEFIT_RimCrownContain_v1",
    "HOODIEFIT_CrownSmoothExpand_v1",
    "HOODIEFIT_CrownSleeveTaper_v1",
    "HOODIEFIT_NarrowSackboy_v1",
]
NEW_HOODIE_KEY = "HOODIEFIT_BowlRimRefine_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "HoodieBowlRimRefine_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "HoodieBowlRimRefine_report.txt").write_text("", encoding="utf-8")

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

def radial(nx, ny, sx, sy):
    r = (nx/max(sx, 1e-6))**2 + (ny/max(sy, 1e-6))**2
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

def find_hoodie():
    for name in FALLBACK_HOODIE_NAMES:
        o = bpy.data.objects.get(name)
        if o and o.type == "MESH":
            if o.name != HOODIE_NAME:
                old = o.name
                o.name = HOODIE_NAME
                o.data.name = HOODIE_NAME + "_Mesh"
                log(f"[rename] hoodie renamed {old} -> {o.name}")
            return o
    matches = [o for o in bpy.data.objects if o.type == "MESH" and ("hoodie" in o.name.lower() or "pullover" in o.name.lower() or "apricot" in o.name.lower())]
    if not matches:
        raise RuntimeError("No hoodie mesh found")
    o = sorted(matches, key=lambda x: (not visible(x), -len(x.data.vertices), x.name))[0]
    old = o.name
    o.name = HOODIE_NAME
    o.data.name = HOODIE_NAME + "_Mesh"
    log(f"[rename] hoodie renamed {old} -> {o.name}")
    return o

def ensure_hoodie_key(obj):
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

def apply_bowl_rim_refine(hoodie, hero):
    key, source = ensure_hoodie_key(hoodie)
    lb = bounds_from_key_data(key)
    before_world = key_world_bounds(hoodie, key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    vertex_count_before = len(hoodie.data.vertices)
    face_count_before = len(hoodie.data.polygons)

    touched = 0
    max_delta = 0.0
    counts = {"ridge_lifted": 0, "ridge_feathered": 0, "rim_vertically_widened": 0, "lower_sides_concaved": 0, "top_rim_unflattened": 0}

    for point in key.data:
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        # Hood-only zones.
        top_ridge = band(zn, 0.76, 0.84, 1.00, 1.00)
        upper_bowl = band(zn, 0.64, 0.72, 0.94, 1.00)
        rim_top = band(zn, 0.56, 0.64, 0.84, 0.95)
        rim_lower = band(zn, 0.38, 0.48, 0.66, 0.80)
        lower_side = band(zn, 0.34, 0.44, 0.62, 0.76)
        transition = band(zn, 0.48, 0.58, 0.84, 0.94)

        center = radial(nx, ny, 0.75, 0.88)
        wide = radial(nx, ny, 1.10, 1.05)
        side = smoothstep(0.38, 0.86, nx)
        frontback = smoothstep(0.34, 0.86, ny)

        new = co.copy()

        # Raise the remaining ridge a little more and feather it into the bowl.
        ridge_weight = top_ridge * (0.45 + 0.55 * center)
        if ridge_weight > 0:
            new.z += dz * 0.040 * ridge_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.014 * ridge_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.020 * ridge_weight)

        # Make the hood cavity read more like a bowl: rounded upper bowl, not a folded peak.
        bowl_weight = upper_bowl * wide
        if bowl_weight > 0:
            new.z += dz * 0.030 * bowl_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.028 * bowl_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.038 * bowl_weight)

        # Vertically widen the hood rim: lift top rim and gently drop lower rim edge.
        top_rim_weight = rim_top * (0.45 + 0.55 * wide)
        if top_rim_weight > 0:
            new.z += dz * 0.065 * top_rim_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.020 * top_rim_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.026 * top_rim_weight)

        lower_rim_weight = rim_lower * (0.25 + 0.75 * max(side, frontback))
        if lower_rim_weight > 0:
            new.z -= dz * 0.018 * lower_rim_weight
            # Keep side clearance without making the hood wider overall.
            new.x = cx + (new.x - cx) * (1.0 + 0.018 * lower_rim_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.022 * lower_rim_weight)

        # Lower sides were convex/folded inward; pull them outward and slightly back/down to form concave side walls.
        side_weight = lower_side * side * (0.55 + 0.45 * (1.0 - center))
        if side_weight > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.045 * side_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.030 * side_weight)
            new.z -= dz * 0.010 * side_weight

        # Feather all slope transitions to avoid a new hard band/ridge.
        trans_weight = transition * wide
        if trans_weight > 0:
            new.z += dz * 0.012 * trans_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.010 * trans_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.014 * trans_weight)

        delta = (new - co).length
        if delta > 1e-7:
            if ridge_weight > 0.08: counts["ridge_lifted"] += 1
            if trans_weight > 0.08: counts["ridge_feathered"] += 1
            if top_rim_weight > 0.08 or lower_rim_weight > 0.08: counts["rim_vertically_widened"] += 1
            if side_weight > 0.08: counts["lower_sides_concaved"] += 1
            if top_rim_weight > 0.08: counts["top_rim_unflattened"] += 1
            point.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    after_world = key_world_bounds(hoodie, key)
    vertex_count_after = len(hoodie.data.vertices)
    face_count_after = len(hoodie.data.polygons)
    hoodie["hoodie_fit_pass"] = "HoodieBowlRimRefine_v1"
    hoodie["hoodie_fit_shape_key"] = NEW_HOODIE_KEY

    log(f"[hoodie] active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; max_delta_local={max_delta:.6f}; vertices={vertex_count_before}->{vertex_count_after}; faces={face_count_before}->{face_count_after}")
    return {
        "shape_key": NEW_HOODIE_KEY,
        "source_key": source,
        "value": 1.0,
        "touched_vertices": touched,
        "max_delta_local": max_delta,
        "vertex_count_before": vertex_count_before,
        "vertex_count_after": vertex_count_after,
        "vertex_count_delta": vertex_count_after - vertex_count_before,
        "face_count_before": face_count_before,
        "face_count_after": face_count_after,
        "face_count_delta": face_count_after - face_count_before,
        "world_dimensions_before": [round(before_world["dim_x"],6), round(before_world["dim_y"],6), round(before_world["dim_z"],6)],
        "world_dimensions_after": [round(after_world["dim_x"],6), round(after_world["dim_y"],6), round(after_world["dim_z"],6)],
        "world_dimension_delta": [round(after_world["dim_x"]-before_world["dim_x"],6), round(after_world["dim_y"]-before_world["dim_y"],6), round(after_world["dim_z"]-before_world["dim_z"],6)],
        "region_counts": counts
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
            "shape_keys": shape_keys, "collections": [c.name for c in o.users_collection]}

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type, "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def set_workbench(scene, color_type):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = color_type
    scene.display.shading.show_xray = False
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = True

def setup_render_settings():
    scene = bpy.context.scene
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    log("[render] smaller 960x540 Workbench/solid/wire evidence renders for clearer shape reading")

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

def create_temp_wire_overlay(hoodie):
    dup = hoodie.copy()
    dup.data = hoodie.data.copy()
    dup.name = "TMP_Hoodie_WireOverlay_DO_NOT_SAVE"
    dup.data.name = "TMP_Hoodie_WireOverlay_Mesh"
    bpy.context.scene.collection.objects.link(dup)
    if dup.data.shape_keys:
        # Keep same active visual deformation by copying shape key values.
        for kb in dup.data.shape_keys.key_blocks:
            kb.value = 0.0
            if kb.name == NEW_HOODIE_KEY:
                kb.value = 1.0
    mat = bpy.data.materials.new("TMP_Wire_Black_DO_NOT_SAVE")
    mat.diffuse_color = (0.0, 0.0, 0.0, 1.0)
    dup.data.materials.clear()
    dup.data.materials.append(mat)
    mod = dup.modifiers.new("TMP_RenderWire", "WIREFRAME")
    mod.thickness = 0.003
    mod.use_even_offset = True
    mod.use_replace = False
    dup.show_in_front = True
    return dup, mat

def render_review(hoodie):
    scene = bpy.context.scene
    old_engine = scene.render.engine
    old_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    old_camera = scene.camera

    kb = hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY) if hoodie.data.shape_keys else None
    hb = key_world_bounds(hoodie, kb)
    center = center_from_bounds(hb)
    hood_top = Vector((center.x, center.y, hb["min_z"] + hb["dim_z"] * 0.82))
    rim = Vector((center.x, center.y, hb["min_z"] + hb["dim_z"] * 0.64))

    # Pulled back compared to previous closeups so the full hood shape is visible.
    camspecs = [
        ("CAM_REVIEW_Hoodie_MaterialPreview", (hood_top.x + 0.65, hood_top.y - 3.35, hood_top.z + 1.15), hood_top, 58, "01_HoodieMaterialPreviewShape.png", "MATERIAL", False),
        ("CAM_REVIEW_Hoodie_SolidGray", (hood_top.x + 0.20, hood_top.y - 3.10, hood_top.z + 1.65), hood_top, 58, "02_HoodieSolidGrayShape.png", "SINGLE", False),
        ("CAM_REVIEW_Hoodie_WireEdges", (hood_top.x + 0.45, hood_top.y - 3.25, hood_top.z + 1.40), hood_top, 60, "03_HoodieWireEdgeShape.png", "SINGLE", True),
        ("CAM_REVIEW_Hoodie_ScenePreserved", (center.x + 5.0, center.y - 7.5, center.z + 1.35), center + Vector((0,1.0,0.1)), 44, "04_HoodieScenePreserved.png", "MATERIAL", False),
    ]

    cams = []
    wire_obj = None
    wire_mat = None
    try:
        setup_render_settings()
        for name, loc, tgt, lens, fn, color_type, use_wire in camspecs:
            if use_wire:
                wire_obj, wire_mat = create_temp_wire_overlay(hoodie)
            set_workbench(scene, color_type)
            cam = make_or_update_cam(name, loc, tgt, lens)
            cams.append({"name": name, "render": fn, "loc": [round(cam.location.x,6), round(cam.location.y,6), round(cam.location.z,6)], "lens": lens, "mode": "WORKBENCH_" + color_type + ("_WIREFRAME" if use_wire else "")})
            scene.camera = cam
            scene.render.filepath = str(OUT / fn)
            bpy.ops.render.render(write_still=True)
            log("[render] " + fn)
            if wire_obj:
                bpy.data.objects.remove(wire_obj, do_unlink=True)
                wire_obj = None
            if wire_mat:
                bpy.data.materials.remove(wire_mat, do_unlink=True)
                wire_mat = None
    finally:
        if wire_obj:
            bpy.data.objects.remove(wire_obj, do_unlink=True)
        if wire_mat:
            bpy.data.materials.remove(wire_mat, do_unlink=True)
        scene.render.engine = old_engine
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old_res
        scene.camera = old_camera
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
        "pass": "hoodie_bowl_rim_refine_v1",
        "hoodie_fit": hoodie_fit,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Vertex is singular; vertices is plural.",
            "This shape-key pass does not add/remove topology, so vertex and face counts should remain unchanged.",
            "Review renders are 960x540 Workbench/material/solid/wire-style views to show shape irregularities more clearly."
        ],
    }
    (REP / "hoodie_bowl_rim_refine_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "HoodieBowlRimRefine_status.json").write_text(json.dumps({"ok": True, "hoodie_shape_key": NEW_HOODIE_KEY, "touched_vertices": hoodie_fit["touched_vertices"], "vertex_delta": hoodie_fit["vertex_count_delta"], "face_delta": hoodie_fit["face_count_delta"], "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Bowl Rim Refine v1",
        "",
        "## Changes",
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        "- Raised the remaining top ridge a bit more.",
        "- Feathered the ridge into the hood bowl.",
        "- Vertically widened the hood rim by lifting the top rim and slightly lowering/opening the lower rim.",
        "- Pulled lower side walls outward to reduce the convex/folded-in look and make the cavity read more concave.",
        "- Review renders switched to smaller 960x540 Workbench/material/solid/wire evidence views.",
        "",
        "## Counts",
        "- Vertex is singular; vertices is plural.",
        f"- Hoodie vertices: {hoodie_fit['vertex_count_before']} -> {hoodie_fit['vertex_count_after']} (delta {hoodie_fit['vertex_count_delta']})",
        f"- Hoodie faces: {hoodie_fit['face_count_before']} -> {hoodie_fit['face_count_after']} (delta {hoodie_fit['face_count_delta']})",
        f"- Touched vertices in shape key: {hoodie_fit['touched_vertices']}",
        f"- Max local vertex movement: {hoodie_fit['max_delta_local']:.6f}",
        f"- World dimensions before: {hoodie_fit['world_dimensions_before']}",
        f"- World dimensions after: {hoodie_fit['world_dimensions_after']}",
        f"- World dimension delta: {hoodie_fit['world_dimension_delta']}",
        "",
        "## Camera rule applied",
        "- Three cameras focus on hoodie shape using hoodie bounds and pulled-back views.",
        "- One wider camera checks scene preservation.",
    ]
    (REP / "Hoodie_Bowl_Rim_Refine_v1.md").write_text("\n".join(md), encoding="utf-8")

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
        "# Scene Layout Summary\n\nUpdated by Hoodie Bowl Rim Refine v1.\n\n"
        "- Focused hoodie rim/bowl corrective shape key added.\n"
        "- Review renders use Workbench/material/solid/wire views at 960x540.\n"
        "- Render engine restored after evidence renders.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_bowl_rim_refine_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] hoodie bowl rim refine v1")
    hoodie = find_hoodie()
    hero = bpy.data.objects.get(HERO_NAME)
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    hoodie_fit = apply_bowl_rim_refine(hoodie, hero)
    cams = render_review(hoodie)
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
        with (OUT / "HoodieBowlRimRefine_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
