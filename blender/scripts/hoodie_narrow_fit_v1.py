import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "hoodie_narrow_fit_v1"
REP = ROOT / "reports" / "hoodie_narrow_fit_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "Apricot Pullover Hoodie"
HOODIE_KEY = "HOODIEFIT_NarrowSackboy_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "HoodieNarrowFit_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "HoodieNarrowFit_report.txt").write_text("", encoding="utf-8")

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
    if disabled:
        log(f"[character] kept F2 baseline; disabled BODYFIT keys: {[d['name'] for d in disabled]}")
    else:
        log("[character] F2 baseline preserved; no active BODYFIT keys found")
    return disabled

def ensure_hoodie_key(obj):
    if obj.type != "MESH":
        raise RuntimeError(f"{HOODIE_NAME} is not a mesh")
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)

    # Remove only this package key on rerun.
    if obj.data.shape_keys.key_blocks.get(HOODIE_KEY):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(HOODIE_KEY)
        bpy.ops.object.shape_key_remove()

    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value = 0.0

    key = obj.shape_key_add(name=HOODIE_KEY, from_mix=True)
    key.value = 1.0
    obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(HOODIE_KEY)
    return key

def apply_hoodie_narrow_fit(obj):
    key = ensure_hoodie_key(obj)
    lb = bounds_from_key_data(key)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    touched = 0
    max_delta = 0.0
    counts = {
        "shoulder_width_reduced": 0,
        "torso_width_reduced": 0,
        "torso_depth_reduced": 0,
        "sleeve_roots_tucked": 0,
        "hood_softened": 0,
    }

    for p in key.data:
        co = p.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny = abs((co.y - cy) / hy)

        torso = band(zn, 0.12, 0.22, 0.58, 0.70)
        shoulder = band(zn, 0.46, 0.56, 0.72, 0.82)
        hood = band(zn, 0.62, 0.72, 0.96, 1.0)
        lower_band = band(zn, 0.05, 0.12, 0.22, 0.32)

        central = (1.0 - smoothstep(0.42, 0.96, nx)) * (1.0 - smoothstep(0.78, 1.08, ny))
        outer = smoothstep(0.46, 0.88, nx)

        new = co.copy()

        # Main hoodie correction: broad human shoulders -> narrower Sackboy shoulder/torso read.
        shoulder_reduce = 0.18 * shoulder * (0.55 + 0.45 * outer)
        torso_reduce = 0.13 * torso * central
        lower_reduce = 0.07 * lower_band * central
        hood_reduce = 0.055 * hood * central

        total_x_reduce = shoulder_reduce + torso_reduce + lower_reduce + hood_reduce
        total_x_reduce = min(total_x_reduce, 0.28)

        # Depth is reduced less than width so it doesn't become paper-thin.
        depth_reduce = min(0.11 * torso * central + 0.065 * shoulder * central + 0.035 * hood * central, 0.16)

        new.x = cx + (new.x - cx) * (1.0 - total_x_reduce)
        new.y = cy + (new.y - cy) * (1.0 - depth_reduce)

        # Tuck sleeve-root / shoulder caps in and slightly down so hoodie doesn't look like a human broad-shoulder garment.
        sleeve_root = shoulder * outer
        if sleeve_root > 0.02:
            new.x -= (1 if nx_signed > 0 else -1) * hx * 0.030 * sleeve_root
            new.z -= dz * 0.025 * sleeve_root

        # Slightly lower/soften hood crown so it reads like it is wrapping the rounded head, not floating bulky above it.
        if hood > 0.02 and central > 0.01:
            new.z -= dz * 0.015 * hood * central

        delta = (new - co).length
        if delta > 1e-7:
            if shoulder > 0.1: counts["shoulder_width_reduced"] += 1
            if torso > 0.1: counts["torso_width_reduced"] += 1
            if depth_reduce > 0.01: counts["torso_depth_reduced"] += 1
            if sleeve_root > 0.05: counts["sleeve_roots_tucked"] += 1
            if hood > 0.1: counts["hood_softened"] += 1
            p.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    obj["hoodie_fit_pass"] = "HoodieNarrowFit_v1"
    obj["hoodie_fit_shape_key"] = HOODIE_KEY
    log(f"[hoodie] added active shape key {HOODIE_KEY}; touched_vertices={touched}; max_delta_local={max_delta:.6f}")
    return {"shape_key": HOODIE_KEY, "value": 1.0, "touched_vertices": touched, "max_delta_local": max_delta,
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
            "vertices": len(o.data.vertices) if o.type == "MESH" else 0,
            "faces": len(o.data.polygons) if o.type == "MESH" else 0,
            "shape_keys": shape_keys,
            "modifiers": [{"name": m.name, "type": m.type} for m in o.modifiers],
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
        target.z = hb["min_z"] + hb["dim_z"] * 0.56

    setups = [
        ("CAM_REVIEW_HoodieFit_Front", (target.x, target.y - 6.0, target.z + 0.45), target, 56, "01_HoodieNarrowFront.png"),
        ("CAM_REVIEW_HoodieFit_Profile", (target.x + 5.1, target.y - 1.0, target.z + 0.45), target, 62, "02_HoodieNarrowProfile.png"),
        ("CAM_REVIEW_HoodieFit_ThreeQuarter", (target.x + 3.4, target.y - 5.7, target.z + 0.65), target, 55, "03_HoodieNarrowThreeQuarter.png"),
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
        "pass": "hoodie_narrow_fit_v1",
        "hoodie_fit": hoodie_fit,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in [HERO_NAME, HOODIE_NAME, "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "This pass changes the hoodie shape, not Sackboy body geometry.",
            "F2 remains visually restored/baseline; all BODYFIT_* keys are kept at 0.",
            "The hoodie is narrowed at shoulders/torso and sleeve roots are tucked down/in.",
            "Scene reflections and approved lighting are preserved."
        ],
        "next_goals": [
            "Assess hoodie shoulder/torso width.",
            "If approved, fit pants and shoes next.",
            "Only apply tiny body edits later if clothing absolutely requires clearance."
        ]
    }
    (REP / "hoodie_narrow_fit_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "HoodieNarrowFit_status.json").write_text(json.dumps({"ok": True, "hoodie_shape_key": HOODIE_KEY, "touched_vertices": hoodie_fit.get("touched_vertices"), "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Hoodie Narrow Fit v1",
        "",
        "## Changes",
        f"- Added active hoodie shape key: **{HOODIE_KEY}**.",
        "- Narrowed hoodie shoulders and upper torso so it reads less like a broad human sweatshirt.",
        "- Reduced hoodie torso depth/width around the narrow Sackboy body.",
        "- Tucked sleeve-root/shoulder caps inward and slightly downward.",
        "- Slightly softened the hood crown so it wraps the character better.",
        "- Kept F2 baseline by disabling all `BODYFIT_*` shape key values.",
        "",
        "## Preserved",
        "- Character mesh Basis shape.",
        "- Successful Cycles reflection setup.",
        "- Traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting.",
        "",
        "## Next goals",
        "- Approve or refine hoodie shape.",
        "- Then fit pants and shoes.",
    ]
    (REP / "Hoodie_Narrow_Fit_v1.md").write_text("\n".join(md), encoding="utf-8")

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
        "# Scene Layout Summary\n\nUpdated by Hoodie Narrow Fit v1.\n\n"
        "- Added non-destructive hoodie shape key for narrower Sackboy proportions.\n"
        "- F2 remains restored baseline; BODYFIT keys disabled.\n"
        "- Preserved current reflection setup and scene lighting.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "hoodie_narrow_fit_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] hoodie narrow fit v1")
    hoodie = bpy.data.objects.get(HOODIE_NAME)
    if not hoodie:
        raise RuntimeError(f"{HOODIE_NAME} object was not found")
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    setup_render_settings()
    hoodie_fit = apply_hoodie_narrow_fit(hoodie)
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
        with (OUT / "HoodieNarrowFit_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
