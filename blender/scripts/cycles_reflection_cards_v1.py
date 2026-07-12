import json, traceback, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "cycles_reflection_cards_v1"
REP = ROOT / "reports" / "cycles_reflection_cards_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "CyclesReflectionCards_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "CyclesReflectionCards_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

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
    before = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
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
    b = {"min_x": min(x["min_x"] for x in bs), "max_x": max(x["max_x"] for x in bs),
         "min_y": min(x["min_y"] for x in bs), "max_y": max(x["max_y"] for x in bs),
         "min_z": min(x["min_z"] for x in bs), "max_z": max(x["max_z"] for x in bs)}
    b["dim_x"] = b["max_x"] - b["min_x"]; b["dim_y"] = b["max_y"] - b["min_y"]; b["dim_z"] = b["max_z"] - b["min_z"]
    return {"objects": [o.name for o in objs], "bounds": b}

def look_at(o, target, track="-Z", up="Y"):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat(track, up).to_euler()

def remove_bad_overlays():
    removed = []
    names = []
    for o in bpy.data.objects:
        if o.name.startswith("FX_GlassStreak_") or o.name.startswith("FX_WindowGlow_"):
            names.append(o.name)
    for name in names:
        o = bpy.data.objects.get(name)
        if o:
            removed.append(name)
            bpy.data.objects.remove(o, do_unlink=True)
    log(f"[cleanup] removed visible overlay leftovers: {removed}")
    return removed

def emission_mat(name, color, strength):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    try: mat.blend_method = "OPAQUE"
    except Exception: pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

def make_card_mesh(name, width, height):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    verts = [(-0.5*width, 0, -0.5*height), (0.5*width, 0, -0.5*height), (0.5*width, 0, 0.5*height), (-0.5*width, 0, 0.5*height)]
    mesh.from_pydata(verts, [], [(0,1,2,3)])
    mesh.update()
    return mesh

def create_or_replace_card(name, width, height, mat):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    obj = bpy.data.objects.new(name, make_card_mesh(name, width, height))
    obj.data.materials.append(mat)
    return obj

def configure_cycles_visibility(obj):
    obj.hide_render = False
    obj.hide_viewport = False
    # Hidden from direct camera; visible to glossy/transmission rays for Cycles reflections.
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
    obj["intent"] = "Cycles reflection-only traffic source; not direct camera prop"
    obj["traffic_cycle_ready"] = True

def setup_cycles_cards(gb):
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    mats = {
        "red": emission_mat("FX_MAT_CyclesReflect_Red", (1.0, 0.015, 0.005, 1), 24.0),
        "yellow": emission_mat("FX_MAT_CyclesReflect_Yellow", (1.0, 0.68, 0.03, 1), 20.0),
        "green": emission_mat("FX_MAT_CyclesReflect_Green", (0.02, 1.0, 0.12, 1), 18.0),
    }
    # Put cards close enough to appear in glass reflections, but keep direct-camera visibility off.
    glass_center = Vector(((gb["min_x"] + gb["max_x"])*0.5, gb["min_y"], gb["min_z"] + gb["dim_z"]*0.58))
    y = gb["min_y"] - 0.55
    specs = [
        ("FX_ReflectCard_Red_01", "red", gb["min_x"] + gb["dim_x"]*0.18, y, gb["min_z"] + gb["dim_z"]*0.58, gb["dim_x"]*0.19, 0.18),
        ("FX_ReflectCard_Red_02", "red", gb["min_x"] + gb["dim_x"]*0.25, y-0.04, gb["min_z"] + gb["dim_z"]*0.72, gb["dim_x"]*0.10, 0.10),
        ("FX_ReflectCard_Yellow_01", "yellow", gb["min_x"] + gb["dim_x"]*0.50, y, gb["min_z"] + gb["dim_z"]*0.56, gb["dim_x"]*0.18, 0.16),
        ("FX_ReflectCard_Yellow_02", "yellow", gb["min_x"] + gb["dim_x"]*0.44, y-0.04, gb["min_z"] + gb["dim_z"]*0.42, gb["dim_x"]*0.10, 0.09),
        ("FX_ReflectCard_Green_01", "green", gb["min_x"] + gb["dim_x"]*0.82, y, gb["min_z"] + gb["dim_z"]*0.58, gb["dim_x"]*0.18, 0.16),
        ("FX_ReflectCard_Green_02", "green", gb["min_x"] + gb["dim_x"]*0.75, y-0.04, gb["min_z"] + gb["dim_z"]*0.72, gb["dim_x"]*0.10, 0.09),
    ]
    rows = []
    for name, key, x, yy, z, w, h in specs:
        obj = create_or_replace_card(name, w, h, mats[key])
        col.objects.link(obj)
        obj.location = Vector((x, yy, z))
        # plane local normal points along +/- Y; align roughly to storefront/glass plane
        obj.rotation_euler = (math.radians(90), 0, 0)
        configure_cycles_visibility(obj)
        rows.append({"name": name, "color": key, "loc": [round(x,6), round(yy,6), round(z,6)], "width": round(w,6), "height": round(h,6), "visible_camera": getattr(obj, "visible_camera", None)})
    log(f"[cards] created {len(rows)} Cycles reflection-only cards near storefront glass")
    return rows

def setup_traffic_lights(gb):
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    target = Vector(((gb["min_x"]+gb["max_x"])*0.5, gb["min_y"], gb["min_z"] + gb["dim_z"]*0.58))
    front_y = gb["min_y"] - 4.2
    specs = [
        ("FX_TrafficLight_Red", (gb["min_x"] + gb["dim_x"]*0.22, front_y, gb["min_z"] + gb["dim_z"]*0.62), (1.0, 0.02, 0.01), 450.0, 0.30),
        ("FX_TrafficLight_Yellow", (gb["min_x"] + gb["dim_x"]*0.50, front_y-0.25, gb["min_z"] + gb["dim_z"]*0.64), (1.0, 0.78, 0.04), 420.0, 0.31),
        ("FX_TrafficLight_Green", (gb["min_x"] + gb["dim_x"]*0.78, front_y, gb["min_z"] + gb["dim_z"]*0.62), (0.03, 1.0, 0.12), 360.0, 0.32),
    ]
    rows = []
    for name, loc, color, energy, spot in specs:
        obj = bpy.data.objects.get(name)
        if not obj:
            data = bpy.data.lights.new(name+"_Data", "SPOT")
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
                    "Roughness": 0.004,
                    "Metallic": 0.0,
                    "Specular IOR Level": 1.0,
                    "Coat Weight": 1.0,
                    "Coat Roughness": 0.006,
                }
                for k, v in vals.items():
                    if k in bsdf.inputs:
                        bsdf.inputs[k].default_value = v
            changed.append({"object": obj.name, "material": mat.name})
    log(f"[glass] tuned {len(changed)} glass/window material slots for Cycles reflections")
    return changed

def setup_cycles_scene():
    scene = bpy.context.scene
    old = {"engine": scene.render.engine}
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.samples = 96
        scene.cycles.preview_samples = 48
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
    log("[render] scene render engine set to Cycles for reflection proof")
    return old

def scan_fx():
    rows = []
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        if o.name.startswith("FX_ReflectCard_") or o.name.startswith("FX_GlassStreak_") or o.name.startswith("FX_TrafficLight"):
            b = bounds(o)
            row = {"name": o.name, "type": o.type, "visible": visible(o), "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                   "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)], "collections": [c.name for c in o.users_collection],
                   "intent": o.get("intent", "")}
            if o.type == "LIGHT":
                row["energy"] = getattr(o.data, "energy", None)
                row["color"] = [round(v,6) for v in getattr(o.data, "color", [])]
            else:
                row["visible_camera"] = getattr(o, "visible_camera", None)
                row["visible_glossy"] = getattr(o, "visible_glossy", None)
            rows.append(row)
    return rows

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type,
                     "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {"name": name, "status": "missing"}
    b = bounds(o); c = counts(o)
    return {"name": name, "status": "present", "visible": visible(o),
            "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "faces": c["faces"]}

def write_reports(removed, gbdata, under, cards, lights, glass, fxscan, lightscan):
    fit = {"key_objects": [object_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    payload = {
        "removed_visible_overlays": removed,
        "glass_objects": gbdata["objects"],
        "glass_bounds": gbdata["bounds"],
        "underglow_lock": under,
        "cycles_reflection_cards": cards,
        "traffic_lights": lights,
        "glass_materials_updated": glass,
        "fx_scan": fxscan,
        "lights_scan": lightscan,
        "fit_scan": fit,
        "note": "This pass does not use visible streak overlays. It uses Cycles-compatible reflection-only emissive cards hidden from direct camera and visible to glossy rays."
    }
    (REP/"cycles_reflection_cards_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        "# Cycles Reflection Cards v1",
        "",
        "## What changed",
        "- Removed any visible FX_GlassStreak / FX_WindowGlow leftovers.",
        f"- Cycles reflection-only cards created: **{len(cards)}**",
        f"- Red/yellow/green traffic spotlights preserved/tuned: **{len(lights)}**",
        f"- Glass material slots tuned: **{len(glass)}**",
        "- Scene render engine was set to Cycles for reflection proof renders.",
        "",
        "## Important",
        "- No visible line/streak overlays were created.",
        "- `FX_ReflectCard_*` objects are hidden from direct camera rays where Cycles visibility is supported.",
        "- They remain visible to glossy/reflection rays so storefront glass can catch the traffic colors.",
        "- This is the cleaner method compared with the rejected floating streak draft.",
        "",
        "## Locked",
        f"- Underglow locked to: **{under.get('after')}**",
        "- Car, asphalt, parking paint strips, approved amber lights, sky/HDRI, character, and clothing were preserved.",
        "- Character deformation was not applied.",
    ]
    (REP/"Cycles_Reflection_Cards_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"CyclesReflectionCards_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c:c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render),
                                    "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x:x.name):
        b = bounds(o)
        e = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection], "visible": visible(o),
             "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
             "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
        if o.type == "MESH": e.update(counts(o))
        if o.type == "LIGHT":
            e["energy"] = getattr(o.data, "energy", None)
            e["color"] = [round(v,6) for v in getattr(o.data, "color", [])] if hasattr(o.data, "color") else None
        data["objects"].append(e)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Cycles Reflection Cards v1.\n\n- Removed visible reflection-streak overlays.\n- Rebuilt red/yellow/green reflection cards as Cycles camera-invisible/glossy-visible sources near storefront glass.\n- Preserved car, asphalt, parking strips, approved lights, sky/HDRI, character, and clothing.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"cycles_reflection_cards_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

def temp_cam(name, loc, aim, lens):
    data = bpy.data.cameras.new(name+"_Data")
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    cam.data.lens = lens
    look_at(cam, aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def render_review(gb):
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    target = Vector(((gb["min_x"]+gb["max_x"])*0.5, (gb["min_y"]+gb["max_y"])*0.5, gb["min_z"] + gb["dim_z"]*0.6))
    hero = bpy.data.objects.get("F2")
    hb = bounds(hero) if hero else {"min_x":-1,"max_x":1,"min_y":-1,"max_y":1,"min_z":0,"max_z":3}
    hc = center(hb)
    cams = [
        temp_cam("TMP_CyclesReflection_Close", Vector((target.x + gb["dim_x"]*0.55, gb["min_y"] - 5.2, target.z + 0.7)), target, 58),
        temp_cam("TMP_CyclesReflection_Oblique", Vector((target.x - gb["dim_x"]*0.55, gb["min_y"] - 6.4, target.z + 0.9)), target, 50),
        temp_cam("TMP_CyclesReflection_FXCheck", Vector((target.x, gb["min_y"] - 8.8, target.z + 1.15)), target, 45),
        temp_cam("TMP_CyclesReflection_Character", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old = scene.camera
    for cam, fn in [(cams[0],"01_CyclesGlassReflectionClose.png"), (cams[1],"02_CyclesGlassReflectionOblique.png"), (cams[2],"03_ReflectionCardsNotCameraVisible.png"), (cams[3],"04_CharacterReadyUnchanged.png")]:
        scene.camera = cam
        scene.render.filepath = str(OUT/fn)
        bpy.ops.render.render(write_still=True)
        log("[render] " + fn)
    scene.camera = old
    for cam in cams:
        bpy.data.objects.remove(cam, do_unlink=True)
    CUR.mkdir(parents=True, exist_ok=True)
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR/p.name).write_bytes(p.read_bytes())

def main():
    reset()
    log("[pass] Cycles reflection cards v1")
    removed = remove_bad_overlays()
    gbdata = glass_bounds()
    gb = gbdata["bounds"]
    under = restore_underglow()
    cards = setup_cycles_cards(gb)
    traffic = setup_traffic_lights(gb)
    glass = tune_glass_materials()
    setup_cycles_scene()
    fxscan = scan_fx()
    lightscan = scan_lights()
    write_reports(removed, gbdata, under, cards, traffic, glass, fxscan, lightscan)
    manifest()
    render_review(gb)
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"CyclesReflectionCards_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
