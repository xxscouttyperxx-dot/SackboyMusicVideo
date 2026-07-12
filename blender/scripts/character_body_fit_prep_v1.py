import json, traceback, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "character_body_fit_prep_v1"
REP = ROOT / "reports" / "character_body_fit_prep_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
SHAPE_KEY_NAME = "BODYFIT_HoodiePantsPrep_v1"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "CharacterBodyFitPrep_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "CharacterBodyFitPrep_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def bounds_local_mesh(obj):
    verts = [v.co.copy() for v in obj.data.vertices]
    xs=[v.x for v in verts]; ys=[v.y for v in verts]; zs=[v.z for v in verts]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {"name": name, "status": "missing"}
    b = bounds_world(o)
    faces = len(o.data.polygons) if o.type == "MESH" else 0
    verts = len(o.data.vertices) if o.type == "MESH" else 0
    mods = [{"name": m.name, "type": m.type} for m in o.modifiers]
    shape_keys = []
    if o.type == "MESH" and o.data.shape_keys:
        shape_keys = [{"name": kb.name, "value": round(float(kb.value), 4)} for kb in o.data.shape_keys.key_blocks]
    return {"name": name, "status": "present", "type": o.type, "visible": visible(o),
            "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "vertices": verts, "faces": faces, "modifiers": mods, "shape_keys": shape_keys,
            "collections": [c.name for c in o.users_collection]}

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

def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def band(zn, a, b, c, d):
    return smoothstep(a, b, zn) * (1.0 - smoothstep(c, d, zn))

def prepare_shape_key(obj):
    if obj.type != "MESH":
        raise RuntimeError(f"{HERO_NAME} is not a mesh")
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    # Remove prior copy of this specific prep key so the package is repeatable.
    existing = obj.data.shape_keys.key_blocks.get(SHAPE_KEY_NAME)
    if existing:
        obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(SHAPE_KEY_NAME)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shape_key_remove()
    key = obj.shape_key_add(name=SHAPE_KEY_NAME, from_mix=False)
    key.value = 1.0
    return key

def deform_body_fit(obj):
    lb = bounds_local_mesh(obj)
    cx = (lb["min_x"] + lb["max_x"]) * 0.5
    cy = (lb["min_y"] + lb["max_y"]) * 0.5
    zmin = lb["min_z"]; dz = max(lb["dim_z"], 1e-6)
    hx = max(lb["dim_x"] * 0.5, 1e-6)
    hy = max(lb["dim_y"] * 0.5, 1e-6)

    key = prepare_shape_key(obj)
    touched = 0
    max_delta = 0.0
    region_counts = {"central_torso": 0, "head_depth": 0, "leg_fit": 0, "protected_outer_hands": 0}

    for i, vert in enumerate(obj.data.vertices):
        co = vert.co.copy()
        zn = (co.z - zmin) / dz
        nx = abs((co.x - cx) / hx)
        ny = abs((co.y - cy) / hy)

        # Protect the outer side/hand zones. This keeps the mitten direction untouched for this body-fit pass.
        hand_protect = 1.0 if (0.22 < zn < 0.62 and nx > 0.72) else 0.0
        if hand_protect:
            region_counts["protected_outer_hands"] += 1
            key.data[i].co = co
            continue

        central = max(0.0, 1.0 - smoothstep(0.55, 0.92, nx))
        central *= max(0.0, 1.0 - smoothstep(0.80, 1.05, ny))

        torso = band(zn, 0.26, 0.34, 0.58, 0.68)
        head = band(zn, 0.58, 0.66, 0.94, 1.00)
        legs = band(zn, 0.08, 0.14, 0.34, 0.42)
        shoulder_blend = band(zn, 0.48, 0.56, 0.66, 0.74)

        # Non-destructive visual fit: slimmer middle, softer hood/head clearance, slightly narrower lower body.
        sx = 1.0 - central * (0.055 * torso + 0.030 * head + 0.045 * legs + 0.020 * shoulder_blend)
        sy = 1.0 - central * (0.085 * torso + 0.055 * head + 0.055 * legs)

        new = co.copy()
        new.x = cx + (co.x - cx) * sx
        new.y = cy + (co.y - cy) * sy

        # Slightly settle shoulders/upper torso without touching hands; helps hoodie sit less blocky.
        if central > 0 and shoulder_blend > 0:
            new.z -= dz * 0.010 * shoulder_blend * central

        d = (new - co).length
        if d > 1e-7:
            touched += 1
            max_delta = max(max_delta, d)
            if torso > 0.1: region_counts["central_torso"] += 1
            if head > 0.1: region_counts["head_depth"] += 1
            if legs > 0.1: region_counts["leg_fit"] += 1
        key.data[i].co = new

    obj["body_fit_pass"] = "CharacterBodyFitPrep_v1"
    obj["body_fit_shape_key"] = SHAPE_KEY_NAME
    log(f"[body] added active shape key {SHAPE_KEY_NAME}; touched_vertices={touched}; max_delta_local={max_delta:.6f}")
    return {"shape_key": SHAPE_KEY_NAME, "value": 1.0, "touched_vertices": touched, "max_delta_local": max_delta, "region_counts": region_counts,
            "local_bounds": lb, "protected_hand_rule": "mid-height outer-x vertices preserved"}

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type,
                     "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def setup_cycles_scene():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.samples = 72
        scene.cycles.preview_samples = 16
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 1
        scene.cycles.glossy_bounces = 4
        scene.cycles.transparent_max_bounces = 6
    except Exception:
        pass
    log("[render] kept Cycles for review renders; lowered preview samples to reduce harsh viewport noise")

def look_at(o, target, track="-Z", up="Y"):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat(track, up).to_euler()

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
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    hero = bpy.data.objects.get(HERO_NAME)
    hb = bounds_world(hero)
    if not hb:
        target = Vector((0,0,1.4))
    else:
        target = Vector(((hb["min_x"]+hb["max_x"])*0.5, (hb["min_y"]+hb["max_y"])*0.5, hb["min_z"] + hb["dim_z"]*0.55))

    old_cam = scene.camera
    cams = [
        (make_cam("TMP_BodyFit_Front", (target.x, target.y - 6.2, target.z + 0.45), target, 58), "01_BodyFitFront.png"),
        (make_cam("TMP_BodyFit_ThreeQuarter", (target.x + 3.6, target.y - 5.6, target.z + 0.55), target, 58), "02_BodyFitThreeQuarter.png"),
        (make_cam("TMP_BodyFit_ClothingContext", (target.x + 2.7, target.y - 6.8, target.z + 0.85), target, 50), "03_ClothingFitContext.png"),
        (make_cam("TMP_BodyFit_ReflectionPreserved", (target.x + 6.0, target.y - 7.2, target.z + 1.2), (target.x, target.y+3.0, target.z+0.5), 44), "04_ReflectionScenePreserved.png"),
    ]
    for cam, fn in cams:
        scene.camera = cam
        scene.render.filepath = str(OUT / fn)
        bpy.ops.render.render(write_still=True)
        log("[render] " + fn)
    scene.camera = old_cam
    for cam, _ in cams:
        bpy.data.objects.remove(cam, do_unlink=True)

def copy_current_review():
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR / p.name).write_bytes(p.read_bytes())

def write_reports(body, under):
    key_names = ["F2", "Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]
    payload = {
        "pass": "character_body_fit_prep_v1",
        "body_deformation": body,
        "underglow_lock": under,
        "key_objects": [object_report(n) for n in key_names],
        "lights_scan": scan_lights(),
        "notes": [
            "This is a non-destructive shape-key based body fit foundation.",
            "Hands are intentionally protected by the outer-mid-height vertex rule.",
            "Clothes were not fitted yet; this pass refines the body/head/torso/legs first as requested.",
            "Reflection setup, traffic lights, car, sky, asphalt, and approved amber lights are preserved.",
        ],
    }
    (REP / "character_body_fit_prep_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "CharacterBodyFitPrep_status.json").write_text(json.dumps({"ok": True, "shape_key": SHAPE_KEY_NAME, "touched_vertices": body.get("touched_vertices")}, indent=2), encoding="utf-8")
    lines = [
        "# Character Body Fit Prep v1",
        "",
        "## What changed",
        f"- Added active non-destructive shape key: **{SHAPE_KEY_NAME}**",
        "- Slimmed central torso/depth for hoodie clearance.",
        "- Slightly softened head/depth for hood clearance.",
        "- Slightly narrowed lower body/legs for pants fit.",
        "- Protected outer mid-height hand zones; no intentional hand sculpting was performed.",
        "",
        "## What did not change",
        "- Clothing was not deformed yet.",
        "- Car, underglow, asphalt, parking strips, approved amber lights, sky/HDRI, and reflection setup were preserved.",
        "- No new guide lines, swatches, or visible helper objects were created.",
        "",
        "## Next recommended pass",
        "- Fit hoodie, pants, and shoes around the body-prepped Sackboy shape.",
    ]
    (REP / "Character_Body_Fit_Prep_v1.md").write_text("\n".join(lines), encoding="utf-8")

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
        data["objects"].append(item)
    (ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\nUpdated by Character Body Fit Prep v1.\n\n"
        "- Added an active non-destructive body-fit shape key to F2.\n"
        "- Protected hands; clothing deformation not applied yet.\n"
        "- Preserved current Cycles reflection setup and scene lighting.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "character_body_fit_prep_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] character body fit prep v1")
    hero = bpy.data.objects.get(HERO_NAME)
    if not hero:
        raise RuntimeError("F2 character mesh was not found")
    under = restore_underglow()
    setup_cycles_scene()
    body = deform_body_fit(hero)
    write_reports(body, under)
    render_review()
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
        with (OUT / "CharacterBodyFitPrep_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
