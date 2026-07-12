import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "hoodie_crown_smooth_expand_v1"
REP = ROOT / "reports" / "hoodie_crown_smooth_expand_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "Apricot Pullover Hoodie"
PREV_HOODIE_KEYS = ["HOODIEFIT_CrownSleeveTaper_v1", "HOODIEFIT_NarrowSackboy_v1"]
NEW_HOODIE_KEY = "HOODIEFIT_CrownSmoothExpand_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)


def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "HoodieCrownSmoothExpand_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "HoodieCrownSmoothExpand_report.txt").write_text("", encoding="utf-8")


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


def radial_falloff(nx, ny, sx=1.0, sy=1.0):
    r = (nx / max(sx, 1e-6))**2 + (ny / max(sy, 1e-6))**2
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


def apply_hoodie_crown_smooth_expand(obj):
    key, source = ensure_hoodie_key(obj)
    lb = bounds_from_key_data(key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]
    dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    touched = 0
    max_delta = 0.0
    counts = {
        "crown_expanded_more": 0,
        "top_dip_smoothed": 0,
        "crown_transition_smoothed": 0,
        "elbow_valley_filled": 0,
        "sleeve_side_smoothed": 0,
    }

    for p in key.data:
        co = p.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        crown_top = band(zn, 0.78, 0.86, 1.00, 1.00)
        crown_mid = band(zn, 0.66, 0.74, 0.90, 0.98)
        crown_base = band(zn, 0.54, 0.62, 0.78, 0.88)
        shoulder = band(zn, 0.42, 0.50, 0.64, 0.74)
        elbow = band(zn, 0.24, 0.30, 0.48, 0.58)
        sleeve_mid = band(zn, 0.18, 0.24, 0.54, 0.64)

        central = radial_falloff(nx, ny, 0.80, 0.95)
        top_core = radial_falloff(nx, ny, 0.55, 0.70)
        broad_core = radial_falloff(nx, ny, 0.92, 1.02)
        sleeve_outer = smoothstep(0.44, 0.86, nx)
        sleeve_centerline = 1.0 - smoothstep(0.22, 0.72, ny)

        new = co.copy()

        # Further expand the hood to contain Sackboy's oversized head, but in stacked soft bands.
        top_expand_x = 0.11 * crown_top * broad_core + 0.05 * crown_mid * broad_core
        top_expand_y = 0.15 * crown_top * broad_core + 0.07 * crown_mid * broad_core
        top_lift = dz * (0.040 * crown_top * broad_core + 0.020 * crown_mid * broad_core)
        new.x = cx + (new.x - cx) * (1.0 + top_expand_x)
        new.y = cy + (new.y - cy) * (1.0 + top_expand_y)
        new.z += top_lift

        # Fill the crown dip / self-overlap tendency by lifting the top center and gently flattening the cap.
        top_dip_fill = crown_top * top_core
        if top_dip_fill > 0.0:
            new.z += dz * 0.040 * top_dip_fill
            new.x = cx + (new.x - cx) * (1.0 + 0.035 * top_dip_fill)
            new.y = cy + (new.y - cy) * (1.0 + 0.045 * top_dip_fill)

        # Smooth transition so the expansion does not form banded indentations below the crown.
        trans = (0.75 * crown_mid + 0.45 * crown_base) * central
        if trans > 0.0:
            new.x = cx + (new.x - cx) * (1.0 + 0.030 * trans)
            new.y = cy + (new.y - cy) * (1.0 + 0.038 * trans)
            new.z += dz * 0.010 * trans

        # Keep the lower torso/shoulder region from re-broadening too much.
        narrow = (0.040 * shoulder + 0.028 * crown_base) * central
        if narrow > 0.0:
            new.x = cx + (new.x - cx) * (1.0 - min(narrow, 0.08))
            new.y = cy + (new.y - cy) * (1.0 - min(narrow * 0.55, 0.05))

        # Fix elbow "two camel humps": lift the center dip and smooth sleeve silhouette.
        elbow_fill = elbow * sleeve_outer * sleeve_centerline
        if elbow_fill > 0.0:
            new.z += dz * 0.028 * elbow_fill
            side_center_x = cx + (1 if nx_signed > 0 else -1) * hx * 0.60
            side_center_y = cy
            new.x = side_center_x + (new.x - side_center_x) * (1.0 - 0.10 * elbow_fill)
            new.y = side_center_y + (new.y - side_center_y) * (1.0 - 0.08 * elbow_fill)

        # Soft extra smoothing along sleeve sidewalls to remove humps/indent bands.
        sleeve_smooth = sleeve_mid * sleeve_outer * max(0.0, 1.0 - 0.8 * sleeve_centerline)
        if sleeve_smooth > 0.0:
            side_center_x = cx + (1 if nx_signed > 0 else -1) * hx * 0.58
            side_center_y = cy
            new.x = side_center_x + (new.x - side_center_x) * (1.0 - 0.08 * sleeve_smooth)
            new.y = side_center_y + (new.y - side_center_y) * (1.0 - 0.05 * sleeve_smooth)

        delta = (new - co).length
        if delta > 1e-7:
            if crown_top > 0.10 or crown_mid > 0.10: counts["crown_expanded_more"] += 1
            if top_dip_fill > 0.10: counts["top_dip_smoothed"] += 1
            if trans > 0.10: counts["crown_transition_smoothed"] += 1
            if elbow_fill > 0.10: counts["elbow_valley_filled"] += 1
            if sleeve_smooth > 0.10: counts["sleeve_side_smoothed"] += 1
            p.co = new
            touched += 1
            if delta > max_delta:
                max_delta = delta

    obj["hoodie_fit_pass"] = "HoodieCrownSmoothExpand_v1"
    obj["hoodie_fit_shape_key"] = NEW_HOODIE_KEY
    log(f"[hoodie] added active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; max_delta_local={max_delta:.6f}")
    return {
        "shape_key": NEW_HOODIE_KEY,
        "source_key": source,
        "value": 1.0,
        "touched_vertices": touched,
        "max_delta_local": max_delta,
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
    return {
        "name": name,
        "status": "present",
        "type": o.type,
        "visible": visible(o),
        "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
        "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
        "vertices": len(o.data.vertices) if o.type == "MESH" else 0,
        "faces": len(o.data.polygons) if o.type == "MESH" else 0,
        "shape_keys": shape_keys,
        "modifiers": [{"name": m.name, "type": m.type} for m in o.modifiers],
        "collections": [c.name for c in o.users_collection],
    }


def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x: x.name):
        rows.append({
            "name": o.name,
            "type": o.data.type,
            "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            "energy": getattr(o.data, "energy", None),
            "color": [round(v,6) for v in getattr(o.data, "color", [])] if hasattr(o.data, "color") else None,
        })
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
        target.z = hb["min_z"] + hb["dim_z"] * 0.60

    setups = [
        ("CAM_REVIEW_HoodTopFront", (target.x, target.y - 5.8, target.z + 0.9), target + Vector((0,0,0.25)), 62, "01_HoodTopFront.png"),
        ("CAM_REVIEW_HoodTopProfile", (target.x + 4.8, target.y - 0.8, target.z + 0.95), target + Vector((0,0,0.22)), 70, "02_HoodTopProfile.png"),
        ("CAM_REVIEW_SleeveElbowCheck", (target.x + 3.2, target.y - 5.2, target.z + 0.55), target + Vector((0.15,0,0.0)), 58, "03_SleeveElbowCheck.png"),
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
        "pass": "hoodie_crown_smooth_expand_v1",
        "hoodie_fit": hoodie_fit,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "Continues from HOODIEFIT_CrownSleeveTaper_v1.",
            "Further expands the hood crown for Sackboy's massive head silhouette.",
            "Attempts to smooth the top crown dip / inner-through-outer overlap look.",
            "Fills the elbow valley between the sleeve camel-hump shapes.",
            "F2 baseline remains unchanged.",
        ],
        "next_goals": [
            "Check whether the hood crown fully contains the intended head silhouette.",
            "If hood top artifacts are gone, proceed to pants and shoes fit.",
            "If necessary, do a final hoodie polish-only pass before pants.",
        ],
    }
    (REP / "hoodie_crown_smooth_expand_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "HoodieCrownSmoothExpand_status.json").write_text(json.dumps({
        "ok": True,
        "hoodie_shape_key": NEW_HOODIE_KEY,
        "touched_vertices": hoodie_fit.get("touched_vertices"),
        "review_cameras": [c["name"] for c in cams],
    }, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Crown Smooth Expand v1",
        "",
        "## Changes",
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        "- Continued enlarging the hood crown for Sackboy's oversized head silhouette.",
        "- Added a top-cap smoothing/fill treatment to reduce the visible dip / overlap artifact on the hood top.",
        "- Smoothed the crown transition to avoid banded indentations.",
        "- Lifted and softened the sleeve elbow valley so the camel-hump shape is reduced.",
        "- Kept F2 restored/baseline with all BODYFIT keys disabled.",
        "",
        "## Next package goal",
        "- If the hood is now clean enough, move to pants and shoes fit.",
        "- If tiny hoodie artifacts remain, run one last hoodie polish-only pass.",
    ]
    (REP / "Hoodie_Crown_Smooth_Expand_v1.md").write_text("\n".join(md), encoding="utf-8")


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
        "# Scene Layout Summary\n\nUpdated by Hoodie Crown Smooth Expand v1.\n\n"
        "- Added hoodie crown smoothing/expansion and sleeve elbow smoothing shape key.\n"
        "- F2 remains restored baseline; BODYFIT keys disabled.\n"
        "- Preserved reflection setup and approved scene lighting.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_crown_smooth_expand_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")


def main():
    reset()
    log("[pass] hoodie crown smooth expand v1")
    hoodie = bpy.data.objects.get(HOODIE_NAME)
    if not hoodie:
        raise RuntimeError(f"{HOODIE_NAME} object was not found")
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    setup_render_settings()
    hoodie_fit = apply_hoodie_crown_smooth_expand(hoodie)
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
        with (OUT / "HoodieCrownSmoothExpand_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
