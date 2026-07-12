import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "scene_scrub_glass_reflection_boost_v1B"
REP = ROOT / "reports" / "scene_scrub_glass_reflection_boost_v1B"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)
EDGE_PREFIXES = ("ENV_FrameL_", "ENV_FrameR_", "ENV_Frame_L_", "ENV_Frame_R_", "ENV_FrameL", "ENV_FrameR")

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "SceneScrubGlassReflectionBoost_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "SceneScrubGlassReflectionBoost_report.txt").write_text("", encoding="utf-8")

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in cs]; ys = [c.y for c in cs]; zs = [c.z for c in cs]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

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

def object_text(o):
    return (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()

def material_text(o):
    if not o or o.type != "MESH":
        return ""
    return " ".join([s.material.name for s in o.material_slots if s.material]).lower()

def is_parking_paint(o):
    text = object_text(o) + " " + material_text(o)
    if o.name.startswith("PARKING_DECAL_"):
        return True
    return any(k in text for k in ["hparking", "stripe", "strip", "paint", "divider", "spine", "parking"]) and not any(
        bad in text for bad in ["frame", "plaza", "shell", "storefront", "window", "door"]
    )

def remove_rejected_edge_frames():
    removed = []
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            continue
        if not any(o.name.startswith(prefix) for prefix in EDGE_PREFIXES):
            continue
        text = object_text(o) + " " + material_text(o)
        if any(k in text for k in ["storefront", "window", "door", "glass", "mall"]):
            continue
        if is_parking_paint(o):
            continue
        removed.append(o.name)
        bpy.data.objects.remove(o, do_unlink=True)
    log("[scrub] removed rejected ENV_Frame* edge objects: " + str(removed))
    return removed

def scrub_clutter():
    removed_objects = []
    removed_collections = []
    protected = ["F2", "Audi", "Asphalt", "HParking", "Parking", "V2B_OverheadAmber", "HERO_CarAmber", "HERO_CarWarm",
                 "HERO_CyanUnderglow", "FX_Traffic", "TRAFFIC_REFLECT", "Apricot Pullover Hoodie", "Cargo pants",
                 "Plane.001", "Plane.022", "Storefront", "Window", "Door", "Glass"]
    kill_parts = ["MaterialSwatch", "Swatch", "PARKING_DECAL_", "ENV_PlazaShell", "TMP_"]
    for o in list(bpy.data.objects):
        if any(p in o.name for p in protected):
            continue
        if any(k in o.name for k in kill_parts):
            if not visible(o) or o.name.startswith("PARKING_DECAL_") or "ENV_PlazaShell" in o.name:
                removed_objects.append(o.name)
                bpy.data.objects.remove(o, do_unlink=True)

    for col in list(bpy.data.collections):
        cname = col.name
        if any(good in cname for good in ["ENV_PARKING", "ENV_STOREFRONT", "ENV_LIGHTING_APPROVED", "FX_REFLECTION_TRAFFIC", "CHAR_F2", "WARDROBE_IMPORTED"]):
            continue
        if any(k in cname.lower() for k in ["backup", "swatch", "guide", "decal", "tmp"]):
            for o in list(col.objects):
                if visible(o) or any(p in o.name for p in protected):
                    continue
                removed_objects.append(o.name)
                bpy.data.objects.remove(o, do_unlink=True)
            if len(col.objects) == 0 and len(col.children) == 0:
                try:
                    removed_collections.append(cname)
                    bpy.data.collections.remove(col)
                except Exception:
                    pass
    log(f"[scrub] removed {len(removed_objects)} hidden/generated clutter objects and {len(removed_collections)} clutter collections")
    return {"removed_objects": removed_objects, "removed_collections": removed_collections}

def organize_collections():
    mapping = {
        "ENV_PARKING": ["Asphalt ground", "HParking", "parking", "Paint", "Stripe", "Strip", "Divider", "Spine", "sewer", "hatch", "manhole"],
        "ENV_LIGHTING_APPROVED": ["V2B_OverheadAmber", "HERO_CarAmber", "HERO_CarWarmSideGlint", "HERO_CyanUnderglow"],
        "CHAR_F2": ["F2"],
        "WARDROBE_IMPORTED": ["Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022"],
        "FX_REFLECTION_TRAFFIC": ["FX_Traffic", "TRAFFIC_REFLECT", "ReflectCard"],
    }
    cols = []
    for name, keys in mapping.items():
        col = ensure_col(name, False)
        cols.append(name)
        for o in bpy.data.objects:
            if any(k.lower() in o.name.lower() for k in keys):
                link_to(o, col)
    return cols

def restore_underglow():
    obj = bpy.data.objects.get(UNDERGLOW_NAME)
    if not obj:
        log("[underglow] missing")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)]
    obj.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)]
    log(f"[underglow] locked {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after}

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def find_storefront_target():
    bs = []
    for o in bpy.data.objects:
        text = object_text(o) + " " + material_text(o)
        if any(k in text for k in ["storefront", "window", "glass", "door"]):
            b = bounds(o)
            if b:
                bs.append(b)
    if bs:
        return Vector(((min(b["min_x"] for b in bs)+max(b["max_x"] for b in bs))*0.5,
                       (min(b["min_y"] for b in bs)+max(b["max_y"] for b in bs))*0.5,
                       min(3.0, max(b["max_z"] for b in bs))))
    return Vector((0, 7.5, 2.0))

def prep_traffic_lights():
    removed = []
    for o in list(bpy.data.objects):
        if "White_Headlight" in o.name:
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    target = find_storefront_target()
    specs = [
        ("FX_TrafficLight_Red", "TRAFFIC_REFLECT_Red_BrakeLight", (-7.5,-18.5,2.55), (1,0.025,0.01), 650, 0.32),
        ("FX_TrafficLight_Yellow", "TRAFFIC_REFLECT_Amber_StreetTurn", (0,-19,2.55), (1,0.82,0.05), 560, 0.34),
        ("FX_TrafficLight_Green", "TRAFFIC_REFLECT_Green_SignalBounce", (7.5,-18.5,2.55), (0.02,1,0.16), 420, 0.36),
    ]
    rows = []
    for name, old, loc, color, energy, spot in specs:
        obj = bpy.data.objects.get(name) or bpy.data.objects.get(old)
        if obj:
            obj.name = name
            obj.data.name = name + "_Data"
        else:
            data = bpy.data.lights.new(name+"_Data", "SPOT")
            obj = bpy.data.objects.new(name, data)
            col.objects.link(obj)
        link_to(obj, col)
        obj.location = Vector(loc)
        look_at(obj, target)
        obj.data.energy = energy
        obj.data.color = color
        obj.data.spot_size = spot
        obj.data.spot_blend = 0.92
        obj.data.use_shadow = False
        obj["traffic_cycle_ready"] = True
        rows.append({"name": name, "loc": list(loc), "energy": energy, "color": list(color)})
    log(f"[reflection] removed extras {removed}; prepared red/yellow/green lights")
    return {"removed_extra_lights": removed, "lights": rows}

def emission_mat(name, color, strength):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

def create_card(name, loc, scale, mat, target):
    obj = bpy.data.objects.get(name)
    if obj and obj.type != "MESH":
        bpy.data.objects.remove(obj, do_unlink=True)
        obj = None
    if not obj:
        mesh = bpy.data.meshes.new(name+"_Mesh")
        mesh.from_pydata([(-0.5,0,-0.5),(0.5,0,-0.5),(0.5,0,0.5),(-0.5,0,0.5)], [], [(0,1,2,3)])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
    obj.location = Vector(loc)
    obj.scale = Vector(scale)
    look_at(obj, target)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for attr, val in [("visible_camera", False), ("visible_shadow", False), ("visible_diffuse", False), ("visible_glossy", True)]:
        try: setattr(obj, attr, val)
        except Exception: pass
    try:
        obj.cycles_visibility.camera = False
        obj.cycles_visibility.shadow = False
        obj.cycles_visibility.diffuse = False
        obj.cycles_visibility.glossy = True
        obj.cycles_visibility.transmission = True
    except Exception:
        pass
    obj.hide_viewport = False
    obj.hide_render = False
    obj["reflection_only_card"] = True
    return obj

def create_reflection_cards():
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    target = find_storefront_target()
    mats = {
        "red": emission_mat("FX_MAT_TrafficReflect_Red", (1,0.02,0.01,1), 8),
        "yellow": emission_mat("FX_MAT_TrafficReflect_Yellow", (1,0.78,0.05,1), 7),
        "green": emission_mat("FX_MAT_TrafficReflect_Green", (0.03,1,0.15,1), 6),
    }
    specs = [
        ("FX_ReflectCard_Red_01", (-6.8,-16.5,2.2), (3.2,1,0.18), mats["red"]),
        ("FX_ReflectCard_Red_02", (-5.2,-16.2,2.55), (1.6,1,0.11), mats["red"]),
        ("FX_ReflectCard_Yellow_01", (0,-16.9,2.35), (3.0,1,0.16), mats["yellow"]),
        ("FX_ReflectCard_Yellow_02", (1.5,-16.4,2.7), (1.4,1,0.10), mats["yellow"]),
        ("FX_ReflectCard_Green_01", (6.5,-16.5,2.25), (3.0,1,0.16), mats["green"]),
        ("FX_ReflectCard_Green_02", (5.0,-16.1,2.62), (1.4,1,0.10), mats["green"]),
    ]
    rows = []
    for name, loc, scale, mat in specs:
        obj = create_card(name, loc, scale, mat, target)
        link_to(obj, col)
        rows.append({"name": name, "location": list(loc), "scale": list(scale), "material": mat.name})
    log(f"[reflection] created {len(rows)} reflection-only emissive cards")
    return rows

def tune_glass():
    changed = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        text = object_text(o) + " " + material_text(o)
        if not any(k in text for k in ["glass", "window"]):
            continue
        if len(o.material_slots) == 0:
            o.data.materials.append(bpy.data.materials.new("WINDOW_MAT_TrafficReflectiveGlass"))
        for slot in o.material_slots:
            mat = slot.material
            if not mat: continue
            mat.use_nodes = True
            try: mat.blend_method = "BLEND"
            except Exception: pass
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                vals = {"Base Color": (0.012,0.016,0.020,0.62), "Alpha": 0.58, "Roughness": 0.012,
                        "Metallic": 0.0, "Specular IOR Level": 1.0, "Coat Weight": 0.85, "Coat Roughness": 0.018}
                for k,v in vals.items():
                    if k in bsdf.inputs:
                        bsdf.inputs[k].default_value = v
            changed.append({"object": o.name, "material": mat.name})
    log(f"[glass] tuned {len(changed)} glass/window materials")
    return changed

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x: x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type, "loc": [round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
                     "energy": getattr(d, "energy", None), "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def obj_report(name):
    o = bpy.data.objects.get(name)
    if not o: return {"name": name, "status": "missing"}
    b = bounds(o); c = counts(o)
    return {"name": name, "status": "present", "visible": visible(o),
            "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "faces": c["faces"]}

def reports(edge, clutter, cols, under, traffic, cards, glass, lights):
    fit = {"key_objects": [obj_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    payload = {"edge_frame_objects_removed": edge, "clutter_removed": clutter, "organized_collections": cols, "underglow_lock": under,
               "traffic_lights": traffic, "reflection_cards": cards, "glass_materials_updated": glass, "lights_scan_after": lights,
               "fit_scan": fit, "traffic_animation_plan": {"colors": ["red","yellow","green"], "method": "keyframe energy/emission intensity later"}}
    (REP/"scene_scrub_glass_reflection_boost_v1B.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Scene Scrub / Glass Reflection Boost v1B", "", "## Cleanup",
             f"- Rejected ENV_Frame* edge objects removed: **{len(edge)}**",
             f"- Hidden/generated clutter objects removed: **{len(clutter.get('removed_objects', []))}**",
             f"- Clutter collections removed: **{len(clutter.get('removed_collections', []))}**",
             "- White parking paint strips were preserved.", "",
             "## Reflection Setup",
             f"- Extra/fourth reflection lights removed: **{len(traffic.get('removed_extra_lights', []))}**",
             f"- Red/yellow/green traffic spotlights prepared: **{len(traffic.get('lights', []))}**",
             f"- Camera-invisible emissive reflection cards created/updated: **{len(cards)}**",
             f"- Glass/window material slots tuned: **{len(glass)}**",
             "- Prepared for later traffic-light style keyframing.", "",
             "## Locked",
             f"- Underglow locked to: **{under.get('after')}**",
             "- Car, asphalt, white parking strips, sky/HDRI, and approved amber lights were preserved.",
             "- Character/clothing deformation was not applied in this pass."]
    (REP/"Scene_Scrub_Glass_Reflection_Boost_v1B.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"SceneScrubGlassReflectionBoost_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

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
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Scene Scrub / Glass Reflection Boost v1B.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"scene_scrub_glass_reflection_boost_v1B","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

def temp_cam(name, loc, aim, lens):
    data = bpy.data.cameras.new(name+"_Data")
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    cam.data.lens = lens
    look_at(cam, aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def render_review():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    hero = bpy.data.objects.get("F2")
    hb = bounds(hero) if hero else {"min_x":-1,"max_x":1,"min_y":-1,"max_y":1,"min_z":0,"max_z":3}
    hc = center(hb)
    target = find_storefront_target()
    cams = [
        temp_cam("TMP_SceneScrub_Overview_v1B", Vector((4.5,-10.5,3.0)), Vector((0,0,0.8)), 42),
        temp_cam("TMP_GlassReflectionBoost_v1B", Vector((7,-12.5,3.4)), target, 50),
        temp_cam("TMP_ReflectionTrafficSetup_v1B", Vector((0,-21.5,3.2)), target, 45),
        temp_cam("TMP_CharacterFitReady_v1B", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old = scene.camera
    for cam, fn in [(cams[0],"01_SceneScrub_Overview.png"),(cams[1],"02_GlassReflectionBoost.png"),(cams[2],"03_ReflectionTrafficSetup.png"),(cams[3],"04_CharacterFitReady.png")]:
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
    log("[pass] scene scrub + corrected red/yellow/green reflection setup v1B")
    edge = remove_rejected_edge_frames()
    clutter = scrub_clutter()
    cols = organize_collections()
    under = restore_underglow()
    traffic = prep_traffic_lights()
    cards = create_reflection_cards()
    glass = tune_glass()
    lights = scan_lights()
    reports(edge, clutter, cols, under, traffic, cards, glass, lights)
    manifest()
    render_review()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"SceneScrubGlassReflectionBoost_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
