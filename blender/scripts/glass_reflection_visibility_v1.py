import json, traceback, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "glass_reflection_visibility_v1"
REP = ROOT / "reports" / "glass_reflection_visibility_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "GlassReflectionVisibility_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "GlassReflectionVisibility_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in coords]; ys = [c.y for c in coords]; zs = [c.z for c in coords]
    return {"min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys), "min_z": min(zs), "max_z": max(zs),
            "dim_x": max(xs)-min(xs), "dim_y": max(ys)-min(ys), "dim_z": max(zs)-min(zs)}

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
        return {"objects": [], "bounds": {"min_x": -7, "max_x": 7, "min_y": 7.0, "max_y": 7.6, "min_z": 0.8, "max_z": 3.0, "dim_x": 14, "dim_y": 0.6, "dim_z": 2.2}}
    b = {"min_x": min(x["min_x"] for x in bs), "max_x": max(x["max_x"] for x in bs),
         "min_y": min(x["min_y"] for x in bs), "max_y": max(x["max_y"] for x in bs),
         "min_z": min(x["min_z"] for x in bs), "max_z": max(x["max_z"] for x in bs)}
    b["dim_x"] = b["max_x"] - b["min_x"]; b["dim_y"] = b["max_y"] - b["min_y"]; b["dim_z"] = b["max_z"] - b["min_z"]
    return {"objects": [o.name for o in objs], "bounds": b}

def look_at(o, target):
    direction = target - o.location
    o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def emission_mat(name, color, strength, alpha=1.0, transparent=False):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    try:
        mat.show_transparent_back = True
    except Exception:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    if transparent and alpha < 1.0:
        transp = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = 1.0 - alpha
        nt.links.new(transp.outputs["BSDF"], mix.inputs[1])
        nt.links.new(emit.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    else:
        nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

def glass_reflect_mat(name, color, strength, alpha):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 1.0 - alpha
    nt.links.new(transp.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat

def make_plane(name, width, height):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    verts = [(-0.5*width, 0, -0.5*height), (0.5*width, 0, -0.5*height), (0.5*width, 0, 0.5*height), (-0.5*width, 0, 0.5*height)]
    mesh.from_pydata(verts, [], [(0,1,2,3)])
    mesh.update()
    return bpy.data.objects.new(name, mesh)

def replace_obj(name, obj):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    obj.name = name
    obj.data.name = name + "_Mesh"
    return obj

def remove_old_reflection_fx():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith("FX_ReflectCard_") or o.name.startswith("FX_GlassStreak_") or o.name.startswith("FX_WindowGlow_"):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
        if "White_Headlight" in o.name:
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    log(f"[fx] removed old/extra reflection FX objects: {removed}")
    return removed

def setup_traffic_lights(gb):
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    target = Vector(((gb["min_x"]+gb["max_x"])*0.5, (gb["min_y"]+gb["max_y"])*0.5, gb["min_z"] + gb["dim_z"]*0.58))
    # Position lights in front of storefront aiming into glass. They influence scene less broadly via tighter cones.
    front_y = gb["min_y"] - 4.2
    x_left = gb["min_x"] + gb["dim_x"]*0.22
    x_mid = gb["min_x"] + gb["dim_x"]*0.50
    x_right = gb["min_x"] + gb["dim_x"]*0.78
    specs = [
        ("FX_TrafficLight_Red", (x_left, front_y, gb["min_z"] + gb["dim_z"]*0.62), (1.0, 0.02, 0.01), 520.0, 0.30),
        ("FX_TrafficLight_Yellow", (x_mid, front_y-0.25, gb["min_z"] + gb["dim_z"]*0.64), (1.0, 0.78, 0.04), 480.0, 0.31),
        ("FX_TrafficLight_Green", (x_right, front_y, gb["min_z"] + gb["dim_z"]*0.62), (0.03, 1.0, 0.12), 380.0, 0.32),
    ]
    rows = []
    for name, loc, color, energy, spot_size in specs:
        o = bpy.data.objects.get(name)
        if not o:
            data = bpy.data.lights.new(name+"_Data", "SPOT")
            o = bpy.data.objects.new(name, data)
            col.objects.link(o)
        link_to(o, col)
        o.location = Vector(loc)
        look_at(o, target)
        o.data.energy = energy
        o.data.color = color
        o.data.spot_size = spot_size
        o.data.spot_blend = 0.94
        o.data.use_shadow = False
        o["traffic_cycle_ready"] = True
        rows.append({"name": name, "loc": [round(v,6) for v in o.location], "target": [round(target.x,6),round(target.y,6),round(target.z,6)], "energy": energy, "color": list(color)})
    log("[lights] positioned red/yellow/green spotlights close to storefront reflection zone")
    return rows

def setup_reflection_cards_and_streaks(gb):
    col = ensure_col("FX_REFLECTION_TRAFFIC", False)
    mats_cards = {
        "red": emission_mat("FX_MAT_ReflectCard_Red", (1,0.015,0.005,1), 14),
        "yellow": emission_mat("FX_MAT_ReflectCard_Yellow", (1,0.74,0.035,1), 12),
        "green": emission_mat("FX_MAT_ReflectCard_Green", (0.02,1,0.12,1), 10),
    }
    mats_streak = {
        "red": glass_reflect_mat("FX_MAT_GlassStreak_Red", (1,0.025,0.01,1), 3.2, 0.34),
        "yellow": glass_reflect_mat("FX_MAT_GlassStreak_Yellow", (1,0.72,0.035,1), 2.8, 0.30),
        "green": glass_reflect_mat("FX_MAT_GlassStreak_Green", (0.025,1,0.12,1), 2.5, 0.28),
    }
    # Determine plane orientation: storefront glass usually spans X/Z with Y depth. Put overlay just in front.
    front_y = gb["min_y"] - 0.018
    reflection_y = gb["min_y"] - 0.35
    x0 = gb["min_x"] + gb["dim_x"]*0.16
    x1 = gb["min_x"] + gb["dim_x"]*0.50
    x2 = gb["min_x"] + gb["dim_x"]*0.82
    z_low = gb["min_z"] + gb["dim_z"]*0.43
    z_mid = gb["min_z"] + gb["dim_z"]*0.58
    z_high = gb["min_z"] + gb["dim_z"]*0.70
    target = Vector(((gb["min_x"]+gb["max_x"])*0.5, gb["max_y"], z_mid))
    # Camera-invisible reflection cards close to the glass.
    card_specs = [
        ("FX_ReflectCard_Red_01", x0, reflection_y, z_mid, gb["dim_x"]*0.19, 0.16, mats_cards["red"]),
        ("FX_ReflectCard_Red_02", x0+gb["dim_x"]*0.06, reflection_y-0.04, z_high, gb["dim_x"]*0.10, 0.09, mats_cards["red"]),
        ("FX_ReflectCard_Yellow_01", x1, reflection_y, z_mid, gb["dim_x"]*0.18, 0.14, mats_cards["yellow"]),
        ("FX_ReflectCard_Yellow_02", x1-gb["dim_x"]*0.06, reflection_y-0.04, z_low, gb["dim_x"]*0.10, 0.08, mats_cards["yellow"]),
        ("FX_ReflectCard_Green_01", x2, reflection_y, z_mid, gb["dim_x"]*0.18, 0.14, mats_cards["green"]),
        ("FX_ReflectCard_Green_02", x2-gb["dim_x"]*0.05, reflection_y-0.04, z_high, gb["dim_x"]*0.10, 0.08, mats_cards["green"]),
    ]
    card_rows = []
    for name, x, y, z, w, h, mat in card_specs:
        obj = make_plane(name, w, h)
        replace_obj(name, obj)
        col.objects.link(obj)
        obj.location = Vector((x,y,z))
        # Keep card roughly parallel to storefront; if ray visibility works, it will reflect but not show in camera.
        obj.rotation_euler = (math.radians(90), 0, 0)
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
        obj["intent"] = "camera-invisible reflection source for storefront glass"
        obj["traffic_cycle_ready"] = True
        card_rows.append({"name": name, "loc": [round(x,6),round(y,6),round(z,6)], "width": round(w,6), "height": h, "visible_camera": getattr(obj, "visible_camera", None)})
    # Guaranteed readable glass-surface streak overlays, subtle and on the glass plane rather than loose props.
    streak_specs = [
        ("FX_GlassStreak_Red_01", x0, front_y, z_mid, gb["dim_x"]*0.20, 0.055, mats_streak["red"]),
        ("FX_GlassStreak_Red_02", x0+gb["dim_x"]*0.065, front_y, z_high, gb["dim_x"]*0.10, 0.035, mats_streak["red"]),
        ("FX_GlassStreak_Yellow_01", x1, front_y, z_mid, gb["dim_x"]*0.18, 0.052, mats_streak["yellow"]),
        ("FX_GlassStreak_Yellow_02", x1-gb["dim_x"]*0.06, front_y, z_low, gb["dim_x"]*0.10, 0.032, mats_streak["yellow"]),
        ("FX_GlassStreak_Green_01", x2, front_y, z_mid, gb["dim_x"]*0.18, 0.050, mats_streak["green"]),
        ("FX_GlassStreak_Green_02", x2-gb["dim_x"]*0.05, front_y, z_high, gb["dim_x"]*0.10, 0.030, mats_streak["green"]),
    ]
    streak_rows = []
    for name, x, y, z, w, h, mat in streak_specs:
        obj = make_plane(name, w, h)
        replace_obj(name, obj)
        col.objects.link(obj)
        obj.location = Vector((x,y,z))
        obj.rotation_euler = (math.radians(90), 0, 0)
        obj.data.materials.append(mat)
        obj.hide_viewport = False
        obj.hide_render = False
        try:
            obj.visible_shadow = False
        except Exception:
            pass
        obj["intent"] = "subtle on-glass reflection streak overlay to guarantee visible traffic-light reflection in Eevee"
        obj["traffic_cycle_ready"] = True
        streak_rows.append({"name": name, "loc": [round(x,6),round(y,6),round(z,6)], "width": round(w,6), "height": h})
    log(f"[fx] created {len(card_rows)} reflection cards and {len(streak_rows)} on-glass streak overlays")
    return {"reflection_cards": card_rows, "glass_streak_overlays": streak_rows}

def tune_glass_materials():
    changed = []
    for o in find_glass_objects():
        if len(o.material_slots) == 0:
            o.data.materials.append(bpy.data.materials.new("WINDOW_MAT_TrafficReflectiveGlass"))
        for slot in o.material_slots:
            mat = slot.material
            if not mat:
                continue
            mat.use_nodes = True
            try: mat.blend_method = "BLEND"
            except Exception: pass
            try: mat.use_screen_refraction = True
            except Exception: pass
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                vals = {"Base Color": (0.01,0.014,0.018,0.58), "Alpha": 0.58, "Roughness": 0.008,
                        "Metallic": 0.0, "Specular IOR Level": 1.0, "Coat Weight": 0.9, "Coat Roughness": 0.012}
                for k, v in vals.items():
                    if k in bsdf.inputs:
                        bsdf.inputs[k].default_value = v
            changed.append({"object": o.name, "material": mat.name})
    ee = getattr(bpy.context.scene, "eevee", None)
    if ee:
        for attr, val in [("use_ssr", True), ("use_ssr_refraction", True), ("ssr_quality", 1.0), ("ssr_max_roughness", 0.16), ("taa_render_samples", 96), ("taa_samples", 64)]:
            try:
                if hasattr(ee, attr):
                    setattr(ee, attr, val)
            except Exception:
                pass
    log(f"[glass] tuned {len(changed)} glass/window material slots")
    return changed

def scan_fx():
    rows = []
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        if o.name.startswith("FX_ReflectCard_") or o.name.startswith("FX_GlassStreak_") or o.name.startswith("FX_TrafficLight"):
            b = bounds(o)
            row = {"name": o.name, "type": o.type, "visible": visible(o), "loc": [round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
                   "dims": None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)], "collections": [c.name for c in o.users_collection],
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
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x: x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type, "loc": [round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
                     "energy": getattr(d, "energy", None), "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def object_report(name):
    o = bpy.data.objects.get(name)
    if not o: return {"name": name, "status": "missing"}
    b = bounds(o); c = counts(o)
    return {"name": name, "status": "present", "visible": visible(o),
            "loc": [round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)],
            "faces": c["faces"]}

def write_reports(removed, gbdata, under, traffic, fx, glass, fx_scan, lights):
    fit = {"key_objects": [object_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    payload = {"old_reflection_fx_removed": removed, "glass_objects": gbdata["objects"], "glass_bounds": gbdata["bounds"], "underglow_lock": under,
               "traffic_lights": traffic, "reflection_fx": fx, "glass_materials_updated": glass, "fx_scan": fx_scan, "lights_scan": lights, "fit_scan": fit,
               "note": "This pass uses two layers: camera-invisible reflection cards for ray/path reflection, plus subtle on-glass streak overlays so the red/yellow/green traffic reflections are actually visible in Eevee/view renders."}
    (REP/"glass_reflection_visibility_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Glass Reflection Visibility v1", "",
             "## What changed",
             "- Rebuilt the reflection system around the storefront glass rather than around the far-end lights.",
             f"- Camera-invisible reflection cards: **{len(fx.get('reflection_cards', []))}**",
             f"- Subtle on-glass streak overlays: **{len(fx.get('glass_streak_overlays', []))}**",
             f"- Red/yellow/green traffic spotlights: **{len(traffic)}**",
             f"- Glass material slots tuned: **{len(glass)}**",
             "",
             "## Why there are both cards and streaks",
             "- The `FX_ReflectCard_*` objects are intended for ray/path reflections and are hidden from direct camera view where Blender supports that visibility.",
             "- The `FX_GlassStreak_*` objects are subtle on-glass reflection overlays. They guarantee the traffic reflection reads in Eevee/rendered view instead of depending only on screen-space reflection behavior.",
             "",
             "## Animation prep",
             "- Red, yellow, and green light/card systems are named consistently for later keyframing.",
             "- Later animation should keyframe energy/emission strength so one color is dominant at a time with slight fade overlap.",
             "",
             "## Locked",
             f"- Underglow locked to: **{under.get('after')}**",
             "- Car, asphalt, parking paint strips, approved amber lights, sky/HDRI, character, and clothing were preserved.",
             "- Character deformation was not applied."]
    (REP/"Glass_Reflection_Visibility_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"GlassReflectionVisibility_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c:c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render), "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x:x.name):
        b = bounds(o)
        e = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection], "visible": visible(o),
             "location": [round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
             "dimensions": None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)]}
        if o.type == "MESH": e.update(counts(o))
        if o.type == "LIGHT":
            e["energy"] = getattr(o.data, "energy", None)
            e["color"] = [round(v,6) for v in getattr(o.data, "color", [])] if hasattr(o.data, "color") else None
        data["objects"].append(e)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Glass Reflection Visibility v1.\n\n- Rebuilt red/yellow/green storefront glass reflection system.\n- Added reflection cards plus subtle on-glass streak overlays for reliable visible reflections.\n- Preserved car, asphalt, parking strips, approved amber lights, sky/HDRI, character, and clothing.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"glass_reflection_visibility_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

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
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    target = Vector(((gb["min_x"]+gb["max_x"])*0.5, (gb["min_y"]+gb["max_y"])*0.5, gb["min_z"]+gb["dim_z"]*0.6))
    hero = bpy.data.objects.get("F2")
    hb = bounds(hero) if hero else {"min_x":-1,"max_x":1,"min_y":-1,"max_y":1,"min_z":0,"max_z":3}
    hc = center(hb)
    cams = [
        temp_cam("TMP_GlassReflection_Close", Vector((target.x + gb["dim_x"]*0.45, gb["min_y"] - 5.0, target.z + 0.65)), target, 58),
        temp_cam("TMP_GlassReflection_Oblique", Vector((target.x - gb["dim_x"]*0.45, gb["min_y"] - 6.2, target.z + 0.80)), target, 48),
        temp_cam("TMP_GlassReflection_FXSetup", Vector((target.x, gb["min_y"] - 8.0, target.z + 1.1)), target, 42),
        temp_cam("TMP_GlassReflection_CharacterReady", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old = scene.camera
    for cam, fn in [(cams[0],"01_GlassReflectionClose.png"), (cams[1],"02_GlassReflectionOblique.png"), (cams[2],"03_ReflectionFXSetup.png"), (cams[3],"04_CharacterReadyUnchanged.png")]:
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
    log("[pass] glass reflection visibility v1")
    removed = remove_old_reflection_fx()
    gbdata = glass_bounds()
    gb = gbdata["bounds"]
    under = restore_underglow()
    traffic = setup_traffic_lights(gb)
    fx = setup_reflection_cards_and_streaks(gb)
    glass = tune_glass_materials()
    fx_scan = scan_fx()
    lights = scan_lights()
    write_reports(removed, gbdata, under, traffic, fx, glass, fx_scan, lights)
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
        with (OUT/"GlassReflectionVisibility_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
