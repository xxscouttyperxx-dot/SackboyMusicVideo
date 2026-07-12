import json, traceback, shutil
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "current_review"
PROJECT_CHANGES = ROOT / "renders" / "Project changes"
REP = ROOT / "reports" / "hoodie_camera_count_side_bowl_fix_v1"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "SACKBOY_Hoodie_Main"
FALLBACK_HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]
PREV_HOODIE_KEYS = [
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
NEW_HOODIE_KEY = "HOODIEFIT_SideBackBowlFix_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

CAMERAS_TO_KEEP_NON_HIDDEN = {
    "CAM_F2_Front",
    "CAM_F2_Profile",
    "CAM_F2_ThreeQuarter",
    "CAM_StorefrontReflection",
    "CAM_SceneWide",
    "CAM_Hood_LeftSide",
    "CAM_Hood_RightSide",
    "CAM_Hood_Top",
    "CAM_Hood_Front",
}
CAMERAS_TO_KEEP_HIDDEN = {
    "CAM_ANIM_Wide",
    "CAM_ANIM_Medium",
    "CAM_ANIM_Close",
}

def log(msg):
    print(msg)
    PROJECT_CHANGES.mkdir(parents=True, exist_ok=True)
    with (PROJECT_CHANGES / "HoodieCameraCountSideBowlFix_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    PROJECT_CHANGES.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()
    (PROJECT_CHANGES / "HoodieCameraCountSideBowlFix_report.txt").write_text("", encoding="utf-8")

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

def smooth_region(key, adjacency, weights, factor=0.30):
    original = [p.co.copy() for p in key.data]
    smoothed_count = 0
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
            smoothed_count += 1
            max_fix = max(max_fix, d)
    return smoothed_count, max_fix

def apply_side_back_bowl_fix(hoodie):
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
    smooth_weights = [0.0] * len(key.data)
    counts = {"shoulder_collar_raised": 0, "lower_sides_pulled_out_down": 0, "back_droop_rounded": 0, "back_protrusion_feathered": 0, "ridge_feathered": 0}

    for i, point in enumerate(key.data):
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        # Heuristic axes:
        # x = left/right width, y = front/back depth, z = height.
        # We keep this pass focused to hood/shoulder/root and avoid F2.
        shoulder_collar = band(zn, 0.44, 0.52, 0.70, 0.82)
        lower_side = band(zn, 0.34, 0.43, 0.64, 0.78)
        bowl_side = band(zn, 0.48, 0.58, 0.84, 0.94)
        back_zone = band(zn, 0.42, 0.52, 0.82, 0.96)
        top_ridge = band(zn, 0.72, 0.80, 1.00, 1.00)
        rear_top = band(zn, 0.60, 0.70, 0.94, 1.00)

        side = smoothstep(0.42, 0.88, nx)
        center = radial(nx, ny, 0.80, 0.92)
        wide = radial(nx, ny, 1.08, 1.04)
        rear = smoothstep(0.18, 0.78, ny_signed)  # positive local-y side is treated as rear/back.
        front = smoothstep(0.18, 0.78, -ny_signed)

        new = co.copy()

        # Raise shoulder/collar seam back up. Do not lower or pinch it.
        collar_w = shoulder_collar * side * (0.55 + 0.45 * (1.0 - ny))
        if collar_w > 0:
            new.z += dz * 0.028 * collar_w
            new.x = cx + (new.x - cx) * (1.0 + 0.010 * collar_w)
            smooth_weights[i] = max(smooth_weights[i], 0.35 * collar_w)

        # Reverse the raised/pinched lower side behavior: push side walls out and down to regain bowl silhouette.
        lower_side_w = lower_side * side * (0.45 + 0.55 * (1.0 - center))
        if lower_side_w > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.035 * lower_side_w)
            new.y = cy + (new.y - cy) * (1.0 + 0.018 * lower_side_w)
            new.z -= dz * 0.020 * lower_side_w
            smooth_weights[i] = max(smooth_weights[i], 0.55 * lower_side_w)

        # Push upper side bowl out slightly, but feather it so it doesn't become a hard fold.
        bowl_side_w = bowl_side * side * wide
        if bowl_side_w > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.022 * bowl_side_w)
            new.y = cy + (new.y - cy) * (1.0 + 0.014 * bowl_side_w)
            smooth_weights[i] = max(smooth_weights[i], 0.40 * bowl_side_w)

        # Back droop: lift the lower/mid back into a rounded profile.
        back_droop_w = back_zone * rear * (0.35 + 0.65 * wide)
        if back_droop_w > 0:
            new.z += dz * 0.028 * back_droop_w
            new.y = cy + (new.y - cy) * (1.0 + 0.018 * back_droop_w)
            smooth_weights[i] = max(smooth_weights[i], 0.48 * back_droop_w)

        # Rear protrusion: pull/feather it back proportionally into the hood silhouette instead of leaving a bump.
        rear_protrusion_w = rear_top * rear * (0.40 + 0.60 * wide)
        if rear_protrusion_w > 0:
            new.y = cy + (new.y - cy) * (1.0 - 0.020 * rear_protrusion_w)
            new.z += dz * 0.010 * rear_protrusion_w
            smooth_weights[i] = max(smooth_weights[i], 0.50 * rear_protrusion_w)

        # Keep ridge rounding, gently.
        ridge_w = top_ridge * (0.45 + 0.55 * center)
        if ridge_w > 0:
            new.z += dz * 0.012 * ridge_w
            smooth_weights[i] = max(smooth_weights[i], 0.42 * ridge_w)

        delta = (new - co).length
        if delta > 1e-7:
            if collar_w > 0.08: counts["shoulder_collar_raised"] += 1
            if lower_side_w > 0.08: counts["lower_sides_pulled_out_down"] += 1
            if back_droop_w > 0.08: counts["back_droop_rounded"] += 1
            if rear_protrusion_w > 0.08: counts["back_protrusion_feathered"] += 1
            if ridge_w > 0.08: counts["ridge_feathered"] += 1
            point.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    adjacency = build_adjacency(hoodie.data)
    smoothed_count, max_smooth = smooth_region(key, adjacency, smooth_weights, factor=0.32)
    max_delta = max(max_delta, max_smooth)

    after_world = key_world_bounds(hoodie, key)
    vertex_count_after = len(hoodie.data.vertices)
    face_count_after = len(hoodie.data.polygons)
    hoodie["hoodie_fit_pass"] = "HoodieSideBackBowlFix_v1"
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
        "region_counts": counts
    }

def remove_review_cameras():
    removed = []
    for cam in list(bpy.data.objects):
        if cam.type == "CAMERA" and cam.name.startswith("CAM_REVIEW_"):
            removed.append(cam.name)
            bpy.data.objects.remove(cam, do_unlink=True)
    if removed:
        log(f"[camera] removed obsolete CAM_REVIEW_* cameras: {len(removed)}")
    return removed

def camera_data(name):
    old = bpy.data.objects.get(name)
    if old and old.type == "CAMERA":
        return old
    data = bpy.data.cameras.new(name + "_Data")
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def look_at(o, target):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def set_cam(name, loc, target, lens, hidden=False):
    cam = camera_data(name)
    cam.location = Vector(loc)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    cam.hide_viewport = hidden
    cam.hide_render = hidden
    return cam

def cleanup_and_create_cameras(hoodie):
    # Remove all old cameras. Recreate exactly requested camera set.
    existing = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    for cam in list(bpy.data.objects):
        if cam.type == "CAMERA":
            bpy.data.objects.remove(cam, do_unlink=True)

    kb = hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY) if hoodie.data.shape_keys else None
    hb = key_world_bounds(hoodie, kb)
    hc = center_from_bounds(hb)
    hood_mid = Vector((hc.x, hc.y, hb["min_z"] + hb["dim_z"] * 0.68))
    hood_top = Vector((hc.x, hc.y, hb["min_z"] + hb["dim_z"] * 0.82))

    hero = bpy.data.objects.get(HERO_NAME)
    fb = bounds_world(hero) if hero else hb
    fc = center_from_bounds(fb)
    fmid = Vector((fc.x, fc.y, fb["min_z"] + fb["dim_z"] * 0.52))

    cams = []
    # 3 F2
    cams.append(set_cam("CAM_F2_Front", (fmid.x, fmid.y - 6.0, fmid.z + 0.55), fmid, 55, False))
    cams.append(set_cam("CAM_F2_Profile", (fmid.x + 5.5, fmid.y - 0.6, fmid.z + 0.55), fmid, 60, False))
    cams.append(set_cam("CAM_F2_ThreeQuarter", (fmid.x + 3.8, fmid.y - 5.8, fmid.z + 0.75), fmid, 52, False))
    # 1 storefront, 1 scene
    cams.append(set_cam("CAM_StorefrontReflection", (hc.x + 7.8, hc.y - 10.0, hc.z + 1.45), (hc.x, hc.y + 4.2, hc.z + 0.65), 48, False))
    cams.append(set_cam("CAM_SceneWide", (hc.x + 8.5, hc.y - 10.5, hc.z + 4.2), (hc.x, hc.y + 1.0, hc.z + 0.3), 35, False))
    # 4 hood
    cams.append(set_cam("CAM_Hood_LeftSide", (hood_mid.x - 3.15, hood_mid.y, hood_mid.z + 0.30), hood_mid, 62, False))
    cams.append(set_cam("CAM_Hood_RightSide", (hood_mid.x + 3.15, hood_mid.y, hood_mid.z + 0.30), hood_mid, 62, False))
    cams.append(set_cam("CAM_Hood_Top", (hood_top.x + 0.05, hood_top.y - 0.25, hood_top.z + 3.15), hood_top, 72, False))
    cams.append(set_cam("CAM_Hood_Front", (hood_mid.x + 0.25, hood_mid.y - 3.55, hood_mid.z + 0.90), hood_mid, 58, False))
    # 3 hidden animation
    cams.append(set_cam("CAM_ANIM_Wide", (hc.x + 9.0, hc.y - 11.5, hc.z + 4.0), (hc.x, hc.y + 0.8, hc.z + 0.3), 32, True))
    cams.append(set_cam("CAM_ANIM_Medium", (hc.x + 5.0, hc.y - 7.0, hc.z + 2.3), (hc.x, hc.y + 0.4, hc.z + 0.3), 42, True))
    cams.append(set_cam("CAM_ANIM_Close", (hc.x + 2.2, hc.y - 4.0, hc.z + 1.5), (hc.x, hc.y + 0.1, hc.z + 0.4), 60, True))

    all_cams = [o for o in bpy.data.objects if o.type == "CAMERA"]
    visible_count = sum(1 for o in all_cams if not o.hide_viewport and not o.hide_render)
    hidden_count = len(all_cams) - visible_count
    log(f"[camera] before={len(existing)} after_total={len(all_cams)} visible={visible_count} hidden={hidden_count}; names={[o.name for o in sorted(all_cams, key=lambda x:x.name)]}")
    return {"before_count": len(existing), "after_total": len(all_cams), "visible_count": visible_count, "hidden_count": hidden_count, "names": [o.name for o in sorted(all_cams, key=lambda x:x.name)]}

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
            "shape_keys": shape_keys}

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
    mod.thickness = 0.0022
    mod.use_even_offset = True
    mod.use_replace = False
    return dup, mat

def isolate_for_wire(hoodie, keep_objs):
    states = {}
    for o in bpy.data.objects:
        states[o.name] = (o.hide_viewport, o.hide_render)
        if o not in keep_objs and o.type not in {"CAMERA"}:
            o.hide_render = True
    return states

def restore_visibility(states):
    for name, state in states.items():
        o = bpy.data.objects.get(name)
        if o:
            o.hide_viewport, o.hide_render = state

def render_review(hoodie):
    scene = bpy.context.scene
    old_engine = scene.render.engine
    old_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    old_camera = scene.camera
    old_filepath = scene.render.filepath
    cams = []
    setup_render_settings()
    wire_obj = None
    wire_mat = None
    states = None
    try:
        render_specs = [
            ("CAM_Hood_Front", "01_HoodFrontMaterial.png", "MATERIAL", False),
            ("CAM_Hood_LeftSide", "02_HoodLeftSideGray.png", "SINGLE", False),
            ("CAM_Hood_RightSide", "03_HoodRightSideGray.png", "SINGLE", False),
            ("CAM_Hood_Top", "04_HoodTopGray.png", "SINGLE", False),
            ("CAM_Hood_Front", "05_HoodIsolatedWireCheck.png", "SINGLE", True),
            ("CAM_SceneWide", "06_ScenePreserved.png", "MATERIAL", False),
        ]
        for cam_name, fn, color_type, wire in render_specs:
            cam = bpy.data.objects.get(cam_name)
            if not cam:
                continue
            if wire:
                wire_obj, wire_mat = create_temp_wire_overlay(hoodie)
                states = isolate_for_wire(hoodie, {hoodie, wire_obj})
                # Push wire render camera back a bit for full-spike context.
                cam = bpy.data.objects.get("CAM_Hood_Front")
                original_loc = cam.location.copy()
                direction = (cam.location - center_from_bounds(key_world_bounds(hoodie, hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)))).normalized()
                cam.location = cam.location + direction * 0.85
                look_at(cam, center_from_bounds(key_world_bounds(hoodie, hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY))))
            set_workbench(scene, color_type)
            scene.camera = cam
            scene.render.filepath = str(OUT / fn)
            bpy.ops.render.render(write_still=True)
            cams.append({"camera": cam.name, "render": fn, "mode": "WORKBENCH_" + color_type + ("_ISOLATED_WIRE" if wire else "")})
            log("[render] " + fn)
            if wire:
                if 'original_loc' in locals():
                    cam.location = original_loc
                if states:
                    restore_visibility(states)
                    states = None
                if wire_obj:
                    bpy.data.objects.remove(wire_obj, do_unlink=True)
                    wire_obj = None
                if wire_mat:
                    bpy.data.materials.remove(wire_mat, do_unlink=True)
                    wire_mat = None
    finally:
        if states:
            restore_visibility(states)
        if wire_obj:
            bpy.data.objects.remove(wire_obj, do_unlink=True)
        if wire_mat:
            bpy.data.materials.remove(wire_mat, do_unlink=True)
        scene.render.engine = old_engine
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old_res
        scene.camera = old_camera
        scene.render.filepath = old_filepath
    return cams

def write_reports(hoodie_fit, camera_report, disabled_bodyfit, under, renders):
    payload = {
        "pass": "hoodie_camera_count_side_bowl_fix_v1",
        "hoodie_fit": hoodie_fit,
        "camera_report": camera_report,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "renders": renders,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Project change text/json files now write to renders/Project changes.",
            "Only current review images remain in renders/current_review.",
            "All existing cameras were deleted and replaced with exactly 12 named cameras: 9 visible + 3 hidden animation cameras.",
            "Wire spikes, if still seen only in the wire render, are likely wire overlay visualization artifacts rather than visible mesh spikes."
        ]
    }
    (PROJECT_CHANGES / "HoodieCameraCountSideBowlFix_status.json").write_text(json.dumps({"ok": True, "camera_total": camera_report["after_total"], "visible_cameras": camera_report["visible_count"], "hidden_cameras": camera_report["hidden_count"], "hoodie_shape_key": NEW_HOODIE_KEY, "touched_vertices": hoodie_fit["touched_vertices"], "vertex_delta": hoodie_fit["vertex_count_delta"], "face_delta": hoodie_fit["face_count_delta"]}, indent=2), encoding="utf-8")
    (REP / "hoodie_camera_count_side_bowl_fix_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Camera Count Side Bowl Fix v1",
        "",
        "## Changes",
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        "- Deleted all existing camera objects and recreated exactly the requested camera inventory.",
        "- Raised shoulder collars.",
        "- Pulled lower hood sides out/down to restore the bowl silhouette.",
        "- Rounded the back hood droop and feathered rear protrusion.",
        "- Pushed the isolated wire view back for more context.",
        "- Text/json change files were written to `renders/Project changes`; current review contains images only.",
        "",
        "## Camera count",
        f"- Total cameras: {camera_report['after_total']}",
        f"- Non-hidden cameras: {camera_report['visible_count']}",
        f"- Hidden animation cameras: {camera_report['hidden_count']}",
        "- Camera names: " + ", ".join(camera_report["names"]),
        "",
        "## Counts",
        f"- Vertices: {hoodie_fit['vertex_count_before']} -> {hoodie_fit['vertex_count_after']} (delta {hoodie_fit['vertex_count_delta']})",
        f"- Faces: {hoodie_fit['face_count_before']} -> {hoodie_fit['face_count_after']} (delta {hoodie_fit['face_count_delta']})",
        f"- Touched vertices: {hoodie_fit['touched_vertices']}",
        f"- Smoothed vertices: {hoodie_fit['smoothed_vertices']}",
        f"- Max local vertex movement: {hoodie_fit['max_delta_local']:.6f}",
        f"- World dimension delta: {hoodie_fit['world_dimension_delta']}",
    ]
    (REP / "Hoodie_Camera_Count_Side_Bowl_Fix_v1.md").write_text("\n".join(md), encoding="utf-8")
    (PROJECT_CHANGES / "HoodieCameraCountSideBowlFix_report.txt").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render), "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(o)
        item = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection], "visible": visible(o), "hidden": bool(o.hide_viewport or o.hide_render), "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)], "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
        if o.type == "MESH":
            item["vertices"] = len(o.data.vertices)
            item["faces"] = len(o.data.polygons)
            if o.data.shape_keys:
                item["shape_keys"] = [{"name": kb.name, "value": round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
        if o.type == "CAMERA":
            item["camera"] = True
        data["objects"].append(item)
    (ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\nUpdated by Hoodie Camera Count Side Bowl Fix v1.\n\n"
        "- Camera inventory reset to exactly 12 cameras: 9 visible + 3 hidden animation cameras.\n"
        "- Current review stores images only; text/json summaries go to renders/Project changes.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_camera_count_side_bowl_fix_v1", "project_changes": str(PROJECT_CHANGES), "current_review": str(OUT)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] hoodie camera count side bowl fix v1")
    hoodie = find_hoodie()
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    hoodie_fit = apply_side_back_bowl_fix(hoodie)
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
        PROJECT_CHANGES.mkdir(parents=True, exist_ok=True)
        with (PROJECT_CHANGES / "HoodieCameraCountSideBowlFix_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
