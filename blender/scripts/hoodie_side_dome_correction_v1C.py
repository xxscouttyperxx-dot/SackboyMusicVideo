import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "current_review"
REP = ROOT / "reports" / "hoodie_side_dome_correction_v1C"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "SACKBOY_Hoodie_Main"
FALLBACK_HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]

PREV_HOODIE_KEYS = [
    "HOODIEFIT_DomeSideDepressionFix_v1B",
    "HOODIEFIT_SideBackBowlFix_v1",
    "HOODIEFIT_CameraCleanupShapeFix_v1",
    "HOODIEFIT_SpikeSleeveSideFix_v1",
    "HOODIEFIT_BowlRimRefine_v1",
    "HOODIEFIT_BowlRidgePolish_v1",
    "HOODIEFIT_TopArtifactFix_v1",
    "HOODIEFIT_RimCrownContain_v1",
    "HOODIEFIT_CrownSmoothExpand_v1",
    "HOODIEFIT_CrownSleeveTaper_v1",
    "HOODIEFIT_NarrowSackboy_v1",
]
NEW_HOODIE_KEY = "HOODIEFIT_SideDomeCorrection_v1C"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    REP.mkdir(parents=True, exist_ok=True)
    with (REP / "HoodieSideDomeCorrection_v1C_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_outputs():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()
    (REP / "HoodieSideDomeCorrection_v1C_report.txt").write_text("", encoding="utf-8")

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
    return t*t*(3.0-2.0*t)

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
        obj = bpy.data.objects.get(name)
        if obj and obj.type == "MESH":
            if obj.name != HOODIE_NAME:
                old = obj.name
                obj.name = HOODIE_NAME
                obj.data.name = HOODIE_NAME + "_Mesh"
                log(f"[rename] hoodie renamed {old} -> {obj.name}")
            return obj
    matches = [o for o in bpy.data.objects if o.type == "MESH" and ("hoodie" in o.name.lower() or "pullover" in o.name.lower() or "apricot" in o.name.lower())]
    if not matches:
        raise RuntimeError("No hoodie mesh found")
    obj = sorted(matches, key=lambda x: (not visible(x), -len(x.data.vertices), x.name))[0]
    old = obj.name
    obj.name = HOODIE_NAME
    obj.data.name = HOODIE_NAME + "_Mesh"
    log(f"[rename] hoodie renamed {old} -> {obj.name}")
    return obj

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
    for name in PREV_HOODIE_KEYS:
        kb = obj.data.shape_keys.key_blocks.get(name)
        if kb:
            kb.value = 1.0
            source = name
            break

    new_key = obj.shape_key_add(name=NEW_HOODIE_KEY, from_mix=True)

    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value = 0.0
    new_key.value = 1.0
    obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
    return new_key, source

def build_adjacency(mesh):
    adj = [set() for _ in range(len(mesh.vertices))]
    for poly in mesh.polygons:
        vs = list(poly.vertices)
        n = len(vs)
        for i, a in enumerate(vs):
            for b in (vs[(i-1)%n], vs[(i+1)%n]):
                if a != b:
                    adj[a].add(b)
                    adj[b].add(a)
    return adj

def smooth_region(key, adjacency, weights, factor=0.38):
    original = [p.co.copy() for p in key.data]
    count = 0
    max_fix = 0.0
    for i, w in enumerate(weights):
        if w <= 0:
            continue
        nbrs = adjacency[i]
        if not nbrs:
            continue
        avg = Vector((0,0,0))
        for n in nbrs:
            avg += original[n]
        avg /= len(nbrs)
        before = key.data[i].co.copy()
        key.data[i].co = before.lerp(avg, min(1.0, factor*w))
        d = (key.data[i].co - before).length
        if d > 1e-8:
            count += 1
            max_fix = max(max_fix, d)
    return count, max_fix

def apply_side_dome_correction(hoodie):
    key, source = ensure_hoodie_key(hoodie)
    before_world = key_world_bounds(hoodie, key)
    lb = bounds_from_key_data(key)
    cx = (lb["min_x"]+lb["max_x"])*0.5
    cy = (lb["min_y"]+lb["max_y"])*0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"]*0.5, 1e-6)
    hy = max(lb["dim_y"]*0.5, 1e-6)

    vertex_count_before = len(hoodie.data.vertices)
    face_count_before = len(hoodie.data.polygons)
    touched = 0
    max_delta = 0.0
    smooth_weights = [0.0] * len(key.data)
    counts = {
        "left_front_depression_down_out": 0,
        "right_front_depression_down_out": 0,
        "left_rear_droop_up_out": 0,
        "right_rear_droop_up_out": 0,
        "side_dome_feathered": 0,
        "front_rim_preserved": 0,
    }

    for i, p in enumerate(key.data):
        co = p.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        side = smoothstep(0.34, 0.86, nx)
        extreme_side = smoothstep(0.50, 0.92, nx)
        center = radial(nx, ny, 0.82, 0.92)
        wide = radial(nx, ny, 1.12, 1.10)
        front = smoothstep(0.12, 0.78, -ny_signed)
        rear = smoothstep(0.12, 0.78, ny_signed)

        # Focus regions
        upper_side = band(zn, 0.52, 0.62, 0.84, 0.94)
        mid_side = band(zn, 0.40, 0.50, 0.74, 0.86)
        lower_side = band(zn, 0.30, 0.40, 0.62, 0.78)
        rear_mid = band(zn, 0.36, 0.48, 0.78, 0.94)
        rear_lower = band(zn, 0.28, 0.38, 0.62, 0.80)
        crown = band(zn, 0.68, 0.78, 1.00, 1.00)
        front_rim = (upper_side + mid_side + lower_side) * front * (0.50 + 0.50*side)

        new = co.copy()

        # Front-facing convex depressions:
        # Left depression: down + left. Right depression: down + right.
        front_side_w = (0.70*mid_side + 0.50*upper_side + 0.40*lower_side) * side * front * (1.0 - 0.35*center)
        if front_side_w > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.034 * front_side_w)
            new.z -= dz * 0.018 * front_side_w
            # Slightly un-pinches the face-facing fold without closing the opening.
            new.y = cy + (new.y - cy) * (1.0 + 0.008 * front_side_w)
            smooth_weights[i] = max(smooth_weights[i], 0.72 * front_side_w)

        # Side/back droop:
        # From right side view push up+right. From left side view push up+left.
        rear_side_w = (0.70*rear_mid + 0.55*rear_lower) * side * rear * (0.50 + 0.50*wide)
        if rear_side_w > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.030 * rear_side_w)
            new.z += dz * 0.038 * rear_side_w
            new.y = cy + (new.y - cy) * (1.0 + 0.010 * rear_side_w)
            smooth_weights[i] = max(smooth_weights[i], 0.70 * rear_side_w)

        # General side dome feather: make side shell continuous from crown to lower side.
        dome_w = (0.40*upper_side + 0.50*mid_side + 0.30*lower_side) * side * (1.0 - 0.25*front)
        if dome_w > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.012 * dome_w)
            new.y = cy + (new.y - cy) * (1.0 + 0.006 * dome_w)
            smooth_weights[i] = max(smooth_weights[i], 0.60 * dome_w)

        # Crown stays softly feathered; don't broadly scale the hood yet.
        crown_w = crown * (0.50 + 0.50*center)
        if crown_w > 0:
            smooth_weights[i] = max(smooth_weights[i], 0.35 * crown_w)

        # Keep front rim readable; only light smoothing there.
        rim_w = min(1.0, front_rim)
        if rim_w > 0.08:
            smooth_weights[i] = max(smooth_weights[i], 0.20 * rim_w)

        delta = (new - co).length
        if delta > 1e-7:
            if front_side_w > 0.08 and nx_signed < 0: counts["left_front_depression_down_out"] += 1
            if front_side_w > 0.08 and nx_signed > 0: counts["right_front_depression_down_out"] += 1
            if rear_side_w > 0.08 and nx_signed < 0: counts["left_rear_droop_up_out"] += 1
            if rear_side_w > 0.08 and nx_signed > 0: counts["right_rear_droop_up_out"] += 1
            if dome_w > 0.08: counts["side_dome_feathered"] += 1
            if rim_w > 0.08: counts["front_rim_preserved"] += 1
            p.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    adjacency = build_adjacency(hoodie.data)
    smoothed_count, max_smooth = smooth_region(key, adjacency, smooth_weights, factor=0.38)
    max_delta = max(max_delta, max_smooth)

    after_world = key_world_bounds(hoodie, key)
    vertex_count_after = len(hoodie.data.vertices)
    face_count_after = len(hoodie.data.polygons)

    hoodie["hoodie_fit_pass"] = "HoodieSideDomeCorrection_v1C"
    hoodie["hoodie_fit_shape_key"] = NEW_HOODIE_KEY

    log(f"[hoodie] active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; smoothed_vertices={smoothed_count}; max_delta_local={max_delta:.6f}; vertices={vertex_count_before}->{vertex_count_after}; faces={face_count_before}->{face_count_after}")
    return {
        "shape_key": NEW_HOODIE_KEY,
        "source_key": source,
        "value": 1.0,
        "touched_vertices": touched,
        "smoothed_vertices": smoothed_count,
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
        "region_counts": counts,
    }

def camera_data(name):
    data = bpy.data.cameras.new(name + "_Data")
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj

def look_at(obj, target):
    direction = target - obj.location
    if direction.length:
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def set_cam(name, loc, target, lens, hidden=False):
    obj = camera_data(name)
    obj.location = Vector(loc)
    obj.data.lens = lens
    look_at(obj, Vector(target))
    obj.hide_viewport = hidden
    obj.hide_render = hidden
    return obj

def cleanup_and_create_cameras(hoodie):
    before = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    for cam in list(bpy.data.objects):
        if cam.type == "CAMERA":
            bpy.data.objects.remove(cam, do_unlink=True)

    key = hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)
    hb = key_world_bounds(hoodie, key)
    hc = center_from_bounds(hb)
    hood_mid = Vector((hc.x, hc.y, hb["min_z"] + hb["dim_z"] * 0.68))
    hood_top = Vector((hc.x, hc.y, hb["min_z"] + hb["dim_z"] * 0.86))

    hero = bpy.data.objects.get(HERO_NAME)
    fb = bounds_world(hero) if hero else hb
    fc = center_from_bounds(fb)
    fmid = Vector((fc.x, fc.y, fb["min_z"] + fb["dim_z"]*0.52))

    # 3 F2
    set_cam("CAM_F2_Front", (fmid.x, fmid.y - 6.0, fmid.z + 0.65), fmid + Vector((0,0,0.10)), 55, False)
    set_cam("CAM_F2_Profile", (fmid.x + 5.5, fmid.y - 0.6, fmid.z + 0.65), fmid + Vector((0,0,0.10)), 60, False)
    set_cam("CAM_F2_ThreeQuarter", (fmid.x + 3.8, fmid.y - 5.8, fmid.z + 0.85), fmid + Vector((0,0,0.10)), 52, False)

    # Scene/storefront
    set_cam("CAM_StorefrontReflection", (hc.x + 7.8, hc.y - 10.0, hc.z + 1.65), (hc.x, hc.y + 4.2, hc.z + 0.85), 48, False)
    set_cam("CAM_SceneWide", (hc.x + 8.5, hc.y - 10.5, hc.z + 4.6), (hc.x, hc.y + 1.0, hc.z + 0.55), 35, False)

    # Hood cameras, raised to include the top termination.
    set_cam("CAM_Hood_LeftSide", (hood_mid.x - 3.45, hood_mid.y, hood_mid.z + 0.92), hood_mid + Vector((0,0,0.30)), 58, False)
    set_cam("CAM_Hood_RightSide", (hood_mid.x + 3.45, hood_mid.y, hood_mid.z + 0.92), hood_mid + Vector((0,0,0.30)), 58, False)
    set_cam("CAM_Hood_Top", (hood_top.x + 0.05, hood_top.y - 0.22, hood_top.z + 3.35), hood_top, 72, False)
    set_cam("CAM_Hood_Front", (hood_mid.x + 0.18, hood_mid.y - 3.85, hood_mid.z + 1.18), hood_mid + Vector((0,0,0.28)), 56, False)

    # Hidden anim
    set_cam("CAM_ANIM_Wide", (hc.x + 9.0, hc.y - 11.5, hc.z + 4.2), (hc.x, hc.y + 0.8, hc.z + 0.5), 32, True)
    set_cam("CAM_ANIM_Medium", (hc.x + 5.0, hc.y - 7.0, hc.z + 2.5), (hc.x, hc.y + 0.4, hc.z + 0.5), 42, True)
    set_cam("CAM_ANIM_Close", (hc.x + 2.2, hc.y - 4.0, hc.z + 1.7), (hc.x, hc.y + 0.1, hc.z + 0.55), 60, True)

    all_cams = sorted([o for o in bpy.data.objects if o.type == "CAMERA"], key=lambda o: o.name)
    visible_count = sum(1 for c in all_cams if not c.hide_viewport and not c.hide_render)
    hidden_count = len(all_cams) - visible_count
    names = [c.name for c in all_cams]
    log(f"[camera] before={len(before)} after_total={len(all_cams)} visible={visible_count} hidden={hidden_count}; names={names}")
    return {"before_count": len(before), "after_total": len(all_cams), "visible_count": visible_count, "hidden_count": hidden_count, "names": names}

def object_report(name):
    obj = bpy.data.objects.get(name)
    if not obj:
        return {"name": name, "status": "missing"}
    b = bounds_world(obj)
    shape_keys = []
    if obj.type == "MESH" and obj.data.shape_keys:
        shape_keys = [{"name": kb.name, "value": round(float(kb.value),4)} for kb in obj.data.shape_keys.key_blocks]
    return {"name": name, "status": "present", "type": obj.type, "visible": visible(obj),
            "loc": [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "vertices": len(obj.data.vertices) if obj.type == "MESH" else 0,
            "faces": len(obj.data.polygons) if obj.type == "MESH" else 0,
            "shape_keys": shape_keys}

def scan_lights():
    rows = []
    for obj in sorted([o for o in bpy.data.objects if o.type == "LIGHT"], key=lambda x:x.name):
        d = obj.data
        rows.append({"name": obj.name, "type": d.type, "loc": [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)],
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

def save_visibility_state():
    return {obj.name: (obj.hide_viewport, obj.hide_render) for obj in bpy.data.objects}

def restore_visibility_state(state):
    for name, flags in state.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_viewport, obj.hide_render = flags

def isolate_hoodie_for_shape(hoodie):
    state = save_visibility_state()
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA"} and obj != hoodie:
            obj.hide_render = True
    hoodie.hide_render = False
    return state

def create_temp_wire_overlay(hoodie):
    dup = hoodie.copy()
    dup.data = hoodie.data.copy()
    dup.name = "TMP_Hoodie_WireOverlay_DO_NOT_SAVE"
    dup.data.name = "TMP_Hoodie_WireOverlay_Mesh"
    bpy.context.scene.collection.objects.link(dup)
    if dup.data.shape_keys:
        for kb in dup.data.shape_keys.key_blocks:
            kb.value = 0.0
            if kb.name == NEW_HOODIE_KEY:
                kb.value = 1.0
    mat = bpy.data.materials.new("TMP_Wire_Black_DO_NOT_SAVE")
    mat.diffuse_color = (0.0, 0.0, 0.0, 1.0)
    dup.data.materials.clear()
    dup.data.materials.append(mat)
    mod = dup.modifiers.new("TMP_RenderWire", "WIREFRAME")
    mod.thickness = 0.0018
    mod.use_even_offset = True
    mod.use_replace = False
    return dup, mat

def render_review(hoodie):
    scene = bpy.context.scene
    old_engine = scene.render.engine
    old_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    old_camera = scene.camera
    old_filepath = scene.render.filepath
    renders = []
    setup_render_settings()
    wire_obj = None
    wire_mat = None
    state = None
    try:
        specs = [
            ("CAM_Hood_Front", "01_HoodFrontMaterial.png", "MATERIAL", True, False),
            ("CAM_Hood_LeftSide", "02_HoodLeftSideGray.png", "SINGLE", True, False),
            ("CAM_Hood_RightSide", "03_HoodRightSideGray.png", "SINGLE", True, False),
            ("CAM_Hood_Top", "04_HoodTopGray.png", "SINGLE", True, False),
            ("CAM_Hood_Front", "05_HoodIsolatedWireCheck.png", "SINGLE", True, True),
            ("CAM_SceneWide", "06_ScenePreserved.png", "MATERIAL", False, False),
        ]
        for cam_name, filename, color_type, isolate, wire in specs:
            cam = bpy.data.objects.get(cam_name)
            if not cam:
                continue
            if isolate:
                state = isolate_hoodie_for_shape(hoodie)
            if wire:
                wire_obj, wire_mat = create_temp_wire_overlay(hoodie)
                wire_obj.hide_render = False
                center = center_from_bounds(key_world_bounds(hoodie, hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)))
                original_loc = cam.location.copy()
                direction = (cam.location - center).normalized()
                cam.location = cam.location + direction * 1.45
                cam.location.z += 0.42
                look_at(cam, center + Vector((0,0,0.25)))
            set_workbench(scene, color_type)
            scene.camera = cam
            scene.render.filepath = str(OUT / filename)
            bpy.ops.render.render(write_still=True)
            renders.append({"camera": cam.name, "render": filename, "mode": "WORKBENCH_" + color_type + ("_ISOLATED_WIRE" if wire else "_HOODIE_ISOLATED" if isolate else "")})
            log("[render] " + filename)
            if wire:
                cam.location = original_loc
                look_at(cam, center_from_bounds(key_world_bounds(hoodie, hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY))) + Vector((0,0,0.20)))
                if wire_obj:
                    bpy.data.objects.remove(wire_obj, do_unlink=True)
                    wire_obj = None
                if wire_mat:
                    bpy.data.materials.remove(wire_mat, do_unlink=True)
                    wire_mat = None
            if state:
                restore_visibility_state(state)
                state = None
    finally:
        if state:
            restore_visibility_state(state)
        if wire_obj:
            bpy.data.objects.remove(wire_obj, do_unlink=True)
        if wire_mat:
            bpy.data.materials.remove(wire_mat, do_unlink=True)
        scene.render.engine = old_engine
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old_res
        scene.camera = old_camera
        scene.render.filepath = old_filepath
    return renders

def write_reports(hoodie_fit, camera_report, disabled_bodyfit, under, renders):
    payload = {
        "pass": "hoodie_side_dome_correction_v1C",
        "hoodie_fit": hoodie_fit,
        "camera_report": camera_report,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "renders": renders,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Text/json reports are stored only under reports/hoodie_side_dome_correction_v1C.",
            "No files are written to renders/Project changes.",
            "Current_review contains images only.",
            "Cameras were raised so the top of hood and wire termination are more visible.",
            "This pass moves existing vertices only. It should not add or remove vertices/faces."
        ]
    }
    status = {
        "ok": True,
        "hoodie_shape_key": NEW_HOODIE_KEY,
        "camera_total": camera_report["after_total"],
        "visible_cameras": camera_report["visible_count"],
        "hidden_cameras": camera_report["hidden_count"],
        "touched_vertices": hoodie_fit["touched_vertices"],
        "smoothed_vertices": hoodie_fit["smoothed_vertices"],
        "max_local_vertex_movement": hoodie_fit["max_delta_local"],
        "vertex_count_before": hoodie_fit["vertex_count_before"],
        "vertex_count_after": hoodie_fit["vertex_count_after"],
        "face_count_before": hoodie_fit["face_count_before"],
        "face_count_after": hoodie_fit["face_count_after"],
        "vertex_delta": hoodie_fit["vertex_count_delta"],
        "face_delta": hoodie_fit["face_count_delta"],
        "world_dimensions_before": hoodie_fit["world_dimensions_before"],
        "world_dimensions_after": hoodie_fit["world_dimensions_after"],
        "world_dimension_delta": hoodie_fit["world_dimension_delta"],
        "current_review_images": [r["render"] for r in renders],
    }
    (REP / "HoodieSideDomeCorrection_v1C_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    (REP / "hoodie_side_dome_correction_v1C.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Side Dome Correction v1C",
        "",
        "## Deformation Summary",
        "This pass focuses on directional correction of the remaining side depressions and rear droop.",
        "From the front: the left depression was moved down/out-left and the right depression down/out-right.",
        "From the side: rear/lower droop was moved up/out on both sides and feathered into the hood silhouette.",
        "F2/Sackboy was not deformed.",
        "",
        "## Counts",
        f"- Touched vertices: {hoodie_fit['touched_vertices']}",
        f"- Smoothed vertices: {hoodie_fit['smoothed_vertices']}",
        f"- Max local vertex movement: {hoodie_fit['max_delta_local']:.6f}",
        f"- Vertex count before/after: {hoodie_fit['vertex_count_before']} -> {hoodie_fit['vertex_count_after']}",
        f"- Face count before/after: {hoodie_fit['face_count_before']} -> {hoodie_fit['face_count_after']}",
        f"- Vertex delta: {hoodie_fit['vertex_count_delta']}",
        f"- Face delta: {hoodie_fit['face_count_delta']}",
        f"- World dimensions before: {hoodie_fit['world_dimensions_before']}",
        f"- World dimensions after: {hoodie_fit['world_dimensions_after']}",
        f"- World dimension delta: {hoodie_fit['world_dimension_delta']}",
        "",
        "## Camera Count",
        f"- Total cameras: {camera_report['after_total']}",
        f"- Visible/non-hidden cameras: {camera_report['visible_count']}",
        f"- Hidden animation cameras: {camera_report['hidden_count']}",
        "- Camera names: " + ", ".join(camera_report["names"]),
        "",
        "## Render Output",
        "- Current review images are in `renders/current_review`.",
        "- Text/json outputs are in `reports/hoodie_side_dome_correction_v1C`.",
    ]
    (REP / "Hoodie_Side_Dome_Correction_v1C.md").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render), "object_count": len(col.objects), "child_count": len(col.children)})
    for obj in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(obj)
        item = {"name": obj.name, "type": obj.type, "collections": [c.name for c in obj.users_collection], "visible": visible(obj),
                "hidden": bool(obj.hide_viewport or obj.hide_render),
                "location": [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)],
                "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
        if obj.type == "MESH":
            item["vertices"] = len(obj.data.vertices)
            item["faces"] = len(obj.data.polygons)
            if obj.data.shape_keys:
                item["shape_keys"] = [{"name": kb.name, "value": round(float(kb.value),4)} for kb in obj.data.shape_keys.key_blocks]
        if obj.type == "CAMERA":
            item["camera"] = True
        data["objects"].append(item)
    (ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\nUpdated by Hoodie Side Dome Correction v1C.\n\n"
        "- Corrected remaining hoodie side depressions and rear droop directionally.\n"
        "- Raised hood review cameras to include top hood and wire termination.\n"
        "- Current review stores images only; text/json reports go under reports.\n"
        "- Camera inventory remains exactly 12 cameras: 9 visible + 3 hidden animation cameras.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_side_dome_correction_v1C", "reports": str(REP), "current_review": str(OUT)}, indent=2), encoding="utf-8")

def main():
    reset_outputs()
    log("[pass] hoodie side dome correction v1C")
    hoodie = find_hoodie()
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    hoodie_fit = apply_side_dome_correction(hoodie)
    camera_report = cleanup_and_create_cameras(hoodie)
    renders = render_review(hoodie)
    write_reports(hoodie_fit, camera_report, disabled_bodyfit, under, renders)
    manifest()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "HoodieSideDomeCorrection_v1C_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
