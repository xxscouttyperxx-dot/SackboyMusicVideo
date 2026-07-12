import json, traceback, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "circular_reflection_refine_v1"
REP = ROOT / "reports" / "circular_reflection_refine_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)


def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "CircularReflectionRefine_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "CircularReflectionRefine_report.txt").write_text("", encoding="utf-8")


def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)


def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in coords]; ys = [c.y for c in coords]; zs = [c.z for c in coords]
    return {
        "min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys), "min_z": min(zs), "max_z": max(zs),
        "dim_x": max(xs) - min(xs), "dim_y": max(ys) - min(ys), "dim_z": max(zs) - min(zs),
    }


def counts(o):
    if o and o.type == "MESH":
        return {"vertices": len(o.data.vertices), "faces": len(o.data.polygons)}
    return {"vertices": 0, "faces": 0}


def ensure_col(name, hide=False):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = hide
    col.hide_render = hide
    return col


def link_to(o, col):
    try:
        if o.name not in col.objects:
            col.objects.link(o)
    except Exception:
        pass


def obj_text(o):
    return (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()


def mat_text(o):
    if not o or o.type != "MESH":
        return ""
    return " ".join([s.material.name for s in o.material_slots if s.material]).lower()


def restore_underglow():
    o = bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log("[lock] underglow missing")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(o.location.x, 6), round(o.location.y, 6), round(o.location.z, 6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x, 6), round(o.location.y, 6), round(o.location.z, 6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after}


def find_glass_objects():
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        text = obj_text(o) + " " + mat_text(o)
        if any(k in text for k in ["glass", "window", "pane"]):
            b = bounds(o)
            if b and b["dim_x"] > 0.05 and b["dim_z"] > 0.05:
                out.append(o)
    return out


def glass_bounds():
    objs = find_glass_objects()
    bs = [bounds(o) for o in objs if bounds(o)]
    if not bs:
        fallback = {"min_x": -7, "max_x": 7, "min_y": 7.0, "max_y": 7.6, "min_z": 0.8, "max_z": 3.0, "dim_x": 14, "dim_y": 0.6, "dim_z": 2.2}
        return {"objects": [], "bounds": fallback}
    b = {
        "min_x": min(x["min_x"] for x in bs), "max_x": max(x["max_x"] for x in bs),
        "min_y": min(x["min_y"] for x in bs), "max_y": max(x["max_y"] for x in bs),
        "min_z": min(x["min_z"] for x in bs), "max_z": max(x["max_z"] for x in bs),
    }
    b["dim_x"] = b["max_x"] - b["min_x"]
    b["dim_y"] = b["max_y"] - b["min_y"]
    b["dim_z"] = b["max_z"] - b["min_z"]
    return {"objects": [o.name for o in objs], "bounds": b}


def look_at(o, target, track="-Z", up="Y"):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat(track, up).to_euler()


def remove_old_reflection_cards_and_overlays():
    prefixes = ("FX_ReflectCard_", "FX_GlassStreak_", "FX_WindowGlow_")
    removed = []
    names = [o.name for o in bpy.data.objects if o.name.startswith(prefixes)]
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj:
            removed.append(name)
            bpy.data.objects.remove(obj, do_unlink=True)
    log(f"[cleanup] removed old reflection cards/overlays: {removed}")
    return removed


def emission_mat(name, color, strength):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    try:
        mat.blend_method = "OPAQUE"
    except Exception:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_disk_mesh(name, radius=0.08, segments=32):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    verts = [(0.0, 0.0, 0.0)]
    edges = []
    faces = []
    for i in range(segments):
        ang = (math.pi * 2.0 * i) / segments
        verts.append((math.cos(ang) * radius, 0.0, math.sin(ang) * radius))
    faces.append(tuple(range(0, segments + 1)))
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    return mesh


def create_or_replace_disk(name, radius, mat):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    obj = bpy.data.objects.new(name, make_disk_mesh(name, radius, 32))
    obj.data.materials.append(mat)
    return obj


def configure_cycles_visibility(obj):
    obj.hide_render = False
    obj.hide_viewport = False
    for attr, val in [("visible_camera", False), ("visible_shadow", False), ("visible_diffuse", False), ("visible_glossy", True), ("visible_transmission", True), ("visible_volume_scatter", False)]:
        try:
            setattr(obj, attr, val)
        except Exception:
            pass
    try:
        obj.cycles_visibility.camera = False
        obj.cycles_visibility.shadow = False
        obj.cycles_visibility.diffuse = False
        obj.cycles_visibility.glossy = True
        obj.cycles_visibility.transmission = True
    except Exception:
        pass
    obj.display_type = 'WIRE'
    obj["intent"] = "Cycles reflection-only circular emissive source"
    obj["traffic_cycle_ready"] = True


def setup_circular_cards(gb):
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    mats = {
        "red": emission_mat("FX_MAT_CyclesReflect_Red", (1.0, 0.02, 0.01, 1), 22.0),
        "yellow": emission_mat("FX_MAT_CyclesReflect_Yellow", (1.0, 0.82, 0.05, 1), 20.0),
        "green": emission_mat("FX_MAT_CyclesReflect_Green", (0.05, 1.0, 0.16, 1), 18.0),
    }
    y = gb["min_y"] - 0.42
    zmid = gb["min_z"] + gb["dim_z"] * 0.58
    specs = [
        ("FX_ReflectCard_Red_01", "red", gb["min_x"] + gb["dim_x"] * 0.22, y, zmid + gb["dim_z"] * 0.06, 0.11),
        ("FX_ReflectCard_Red_02", "red", gb["min_x"] + gb["dim_x"] * 0.28, y - 0.02, zmid - gb["dim_z"] * 0.07, 0.07),
        ("FX_ReflectCard_Yellow_01", "yellow", gb["min_x"] + gb["dim_x"] * 0.50, y, zmid + gb["dim_z"] * 0.04, 0.10),
        ("FX_ReflectCard_Yellow_02", "yellow", gb["min_x"] + gb["dim_x"] * 0.56, y - 0.02, zmid - gb["dim_z"] * 0.10, 0.065),
        ("FX_ReflectCard_Green_01", "green", gb["min_x"] + gb["dim_x"] * 0.76, y, zmid + gb["dim_z"] * 0.05, 0.11),
        ("FX_ReflectCard_Green_02", "green", gb["min_x"] + gb["dim_x"] * 0.70, y - 0.02, zmid - gb["dim_z"] * 0.08, 0.07),
    ]
    rows = []
    for name, key, x, yy, z, radius in specs:
        obj = create_or_replace_disk(name, radius, mats[key])
        link_to(obj, col)
        obj.location = Vector((x, yy, z))
        obj.rotation_euler = (math.radians(90), 0, 0)
        configure_cycles_visibility(obj)
        rows.append({"name": name, "color": key, "loc": [round(x,6), round(yy,6), round(z,6)], "radius": radius})
    log(f"[cards] created {len(rows)} circular reflection-only cards")
    return rows


def setup_traffic_lights(gb):
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    target = Vector(((gb["min_x"] + gb["max_x"]) * 0.5, gb["min_y"], gb["min_z"] + gb["dim_z"] * 0.58))
    front_y = gb["min_y"] - 4.2
    specs = [
        ("FX_TrafficLight_Red", (gb["min_x"] + gb["dim_x"] * 0.22, front_y, gb["min_z"] + gb["dim_z"] * 0.62), (1.0, 0.02, 0.01), 450.0, 0.30),
        ("FX_TrafficLight_Yellow", (gb["min_x"] + gb["dim_x"] * 0.50, front_y - 0.25, gb["min_z"] + gb["dim_z"] * 0.64), (1.0, 0.82, 0.05), 420.0, 0.31),
        ("FX_TrafficLight_Green", (gb["min_x"] + gb["dim_x"] * 0.78, front_y, gb["min_z"] + gb["dim_z"] * 0.62), (0.05, 1.0, 0.16), 360.0, 0.32),
    ]
    rows = []
    for name, loc, color, energy, spot in specs:
        obj = bpy.data.objects.get(name)
        if not obj:
            data = bpy.data.lights.new(name + "_Data", "SPOT")
            obj = bpy.data.objects.new(name, data)
            col.objects.link(obj)
        link_to(obj, col)
        obj.location = Vector(loc)
        look_at(obj, target)
        obj.data.energy = energy
        obj.data.color = color
        obj.data.spot_size = spot
        obj.data.spot_blend = 0.94
        obj.data.use_shadow = False
        obj["traffic_cycle_ready"] = True
        rows.append({"name": name, "loc": [round(v,6) for v in obj.location], "energy": energy, "color": list(color)})
    log("[lights] preserved/tuned red-yellow-green spotlights")
    return rows


def tune_glass_materials():
    changed = []
    for obj in find_glass_objects():
        if len(obj.material_slots) == 0:
            obj.data.materials.append(bpy.data.materials.new("WINDOW_MAT_CyclesReflectiveGlass"))
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            mat.use_nodes = True
            try:
                mat.blend_method = "BLEND"
            except Exception:
                pass
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                vals = {
                    "Base Color": (0.006, 0.009, 0.013, 0.62),
                    "Alpha": 0.62,
                    "Roughness": 0.003,
                    "Metallic": 0.0,
                    "Specular IOR Level": 1.0,
                    "Coat Weight": 1.0,
                    "Coat Roughness": 0.004,
                }
                for k, v in vals.items():
                    if k in bsdf.inputs:
                        bsdf.inputs[k].default_value = v
            changed.append({"object": obj.name, "material": mat.name})
    log(f"[glass] tuned {len(changed)} glass/window material slots for tighter reflections")
    return changed


def setup_cycles_scene():
    scene = bpy.context.scene
    old = {"engine": scene.render.engine}
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.samples = 96
        scene.cycles.preview_samples = 24
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 1
        scene.cycles.glossy_bounces = 4
        scene.cycles.transparent_max_bounces = 6
    except Exception:
        pass
    try:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "Medium High Contrast"
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
    except Exception:
        pass
    log("[render] scene render engine set to Cycles for reflection refinement")
    return old


def ensure_camera(name, loc, rot):
    cam = bpy.data.objects.get(name)
    if not cam or cam.type != "CAMERA":
        data = bpy.data.cameras.new(name + "_Data")
        cam = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    cam.rotation_euler = rot
    cam.data.lens = 38
    return cam


def render_still(filename, cam):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
    log(f"[render] {filename}")


def copy_current_review():
    mapping = {
        "01_CircularReflectionClose.png": "01_CircularReflectionClose.png",
        "02_CircularReflectionOblique.png": "02_CircularReflectionOblique.png",
        "03_ReflectionSourceLayout.png": "03_ReflectionSourceLayout.png",
        "04_CharacterReadyUnchanged.png": "04_CharacterReadyUnchanged.png",
        "CircularReflectionRefine_report.txt": "CircularReflectionRefine_report.txt",
        "CircularReflectionRefine_status.json": "CircularReflectionRefine_status.json",
    }
    for src, dst in mapping.items():
        (CUR / dst).write_bytes((OUT / src).read_bytes())


def scan_fx():
    rows = []
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        if o.name.startswith("FX_ReflectCard_") or o.name.startswith("FX_TrafficLight"):
            b = bounds(o)
            row = {
                "name": o.name, "type": o.type, "visible": visible(o),
                "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
                "collections": [c.name for c in o.users_collection],
                "intent": o.get("intent", ""),
            }
            if o.type == "LIGHT":
                row["energy"] = getattr(o.data, "energy", None)
                row["color"] = [round(v,6) for v in getattr(o.data, "color", [])]
            else:
                row["visible_camera"] = getattr(o, "visible_camera", None)
                row["visible_glossy"] = getattr(o, "visible_glossy", None)
            rows.append(row)
    return rows


def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {"name": name, "status": "missing"}
    b = bounds(o); c = counts(o)
    return {
        "name": name, "status": "present", "visible": visible(o),
        "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
        "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
        "faces": c["faces"],
    }


def write_reports(removed, gbdata, under, cards, lights, glass, fxscan):
    fit = {"key_objects": [object_report(n) for n in ["F2", "Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]]}
    payload = {
        "removed_old_reflection_objects": removed,
        "glass_objects": gbdata["objects"],
        "glass_bounds": gbdata["bounds"],
        "underglow_lock": under,
        "circular_reflection_cards": cards,
        "traffic_lights": lights,
        "glass_materials_updated": glass,
        "fx_scan": fxscan,
        "fit_scan": fit,
        "note": "This pass preserves the good Cycles glass look and refines the reflection-only sources into tighter circular emissive cards."
    }
    (REP / "circular_reflection_refine_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        "# Circular Reflection Refine v1",
        "",
        "## What changed",
        f"- Old reflection cards/overlays removed: **{len(removed)}**",
        f"- Circular reflection-only cards created: **{len(cards)}**",
        f"- Red/yellow/green spotlights preserved/tuned: **{len(lights)}**",
        f"- Glass material slots tuned: **{len(glass)}**",
        "",
        "## Important",
        "- This pass keeps the successful Cycles-based reflection approach.",
        "- `FX_ReflectCard_*` objects are smaller circular emissive sources.",
        "- They remain hidden from the direct camera and visible to glossy / transmission rays for storefront reflections.",
        "- No character deformation was applied in this pass.",
        "",
        "## Locked",
        f"- Underglow locked to: **{under.get('after')}**",
    ]
    (REP / "Circular_Reflection_Refine_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "CircularReflectionRefine_status.json").write_text(json.dumps({
        "pass": "circular_reflection_refine_v1",
        "ok": True,
        "cards": len(cards),
        "lights": len(lights),
        "glass_material_slots": len(glass),
    }, indent=2), encoding="utf-8")


def main():
    reset()
    log("[pass] circular reflection refine v1")
    scene_old = setup_cycles_scene()
    removed = remove_old_reflection_cards_and_overlays()
    under = restore_underglow()
    gbdata = glass_bounds(); gb = gbdata["bounds"]
    cards = setup_circular_cards(gb)
    lights = setup_traffic_lights(gb)
    glass = tune_glass_materials()
    fxscan = scan_fx()

    cam1 = ensure_camera("REVIEW_CircularReflection_Close", (0.0, 2.1, 1.9), (math.radians(78), 0, 0))
    cam2 = ensure_camera("REVIEW_CircularReflection_Oblique", (-4.2, 1.8, 2.0), (math.radians(74), 0, math.radians(-18)))
    cam3 = ensure_camera("REVIEW_ReflectionSource_Layout", (0.0, -0.8, 4.8), (math.radians(58), 0, 0))
    cam4 = ensure_camera("REVIEW_Character_Ready", (-1.4, 0.8, 1.4), (math.radians(82), 0, math.radians(10)))

    render_still("01_CircularReflectionClose.png", cam1)
    render_still("02_CircularReflectionOblique.png", cam2)
    render_still("03_ReflectionSourceLayout.png", cam3)
    render_still("04_CharacterReadyUnchanged.png", cam4)
    write_reports(removed, gbdata, under, cards, lights, glass, fxscan)
    copy_current_review()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        raise
