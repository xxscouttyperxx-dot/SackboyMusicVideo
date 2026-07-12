import json, math, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "scene_scrub_glass_reflection_boost_v1"
REP = ROOT / "reports" / "scene_scrub_glass_reflection_boost_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

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

def object_text(o):
    return (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()

def material_text(o):
    names = []
    if o and o.type == "MESH":
        for s in o.material_slots:
            if s.material:
                names.append(s.material.name)
    return " ".join(names).lower()

def remove_edge_frame_objects():
    removed=[]
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            continue
        name = o.name
        lower = name.lower()
        text = object_text(o) + " " + material_text(o)
        if not (lower.startswith("env_framel") or lower.startswith("env_framer") or lower.startswith("env_frame_l") or lower.startswith("env_frame_r")):
            continue
        # Do not delete storefront/window/door frames. User means edge objects near parking/sidewalk.
        if any(k in text for k in ["storefront", "window", "door", "glass", "mall"]):
            continue
        b = bounds(o)
        # Thin/ground-ish frame objects only; avoid accidental large building structures.
        if b and (b["dim_z"] > 0.45 or b["dim_x"] > 28 or b["dim_y"] > 28):
            continue
        removed.append(name)
        bpy.data.objects.remove(o, do_unlink=True)
    log(f"[scrub] removed {len(removed)} black/glossy edge frame object(s): {removed}")
    return removed

def cleanup_hidden_backups_and_duplicate_collections():
    removed_objects=[]
    removed_collections=[]
    backup_keywords = ["BACKUPS_HIDDEN", "BACKUP_LINKED_ORIGINALS", "PARKING_DECAL_BACKUPS", "SURFACE_REPAIR_BACKUPS", "SCENE_CLEANUP_BACKUPS", "GRID_PARKING_REPAIR_BACKUPS", "PARKING_HEIGHT_REPAIR_BACKUPS"]
    for col in list(bpy.data.collections):
        cname = col.name
        if not any(k.lower() in cname.lower() for k in backup_keywords):
            continue
        # Only delete objects in hidden backup collections; these are redundant because package-level .blend backups exist.
        for o in list(col.objects):
            removed_objects.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
        try:
            bpy.data.collections.remove(col)
            removed_collections.append(cname)
        except Exception:
            pass
    # Remove old generated parking decal leftovers if any survived.
    for o in list(bpy.data.objects):
        if o.name.startswith("PARKING_DECAL_") or "ENV_PlazaShell" in o.name:
            removed_objects.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    # Remove empty helper collections that only add clutter.
    for col in list(bpy.data.collections):
        if len(col.objects) == 0 and len(col.children) == 0:
            if any(k in col.name.lower() for k in ["backup", "decal", "old", "guide", "swatch"]):
                try:
                    removed_collections.append(col.name)
                    bpy.data.collections.remove(col)
                except Exception:
                    pass
    log(f"[scrub] removed {len(removed_objects)} hidden/generated duplicate object(s) and {len(removed_collections)} clutter collection(s)")
    return {"removed_objects": removed_objects, "removed_collections": removed_collections}

def restore_underglow():
    light = bpy.data.objects.get(UNDERGLOW_NAME)
    if not light:
        log(f"[underglow] WARNING missing {UNDERGLOW_NAME}")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before=[round(light.location.x,6), round(light.location.y,6), round(light.location.z,6)]
    light.location=Vector(UNDERGLOW_LOCK_LOC)
    after=[round(light.location.x,6), round(light.location.y,6), round(light.location.z,6)]
    log(f"[underglow] locked {UNDERGLOW_NAME}: {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after}

def find_storefront_target():
    candidates=[]
    for o in bpy.data.objects:
        text = object_text(o)
        if any(k in text for k in ["storefront", "window", "glass", "strip mall", "door"]):
            b=bounds(o)
            if b:
                candidates.append(b)
    if candidates:
        minx=min(b["min_x"] for b in candidates); maxx=max(b["max_x"] for b in candidates)
        miny=min(b["min_y"] for b in candidates); maxy=max(b["max_y"] for b in candidates)
        minz=min(b["min_z"] for b in candidates); maxz=max(b["max_z"] for b in candidates)
        return Vector(((minx+maxx)/2, (miny+maxy)/2, min(3.0, maxz)))
    return Vector((0.0, 7.5, 2.0))

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def boost_reflection_lights():
    col = bpy.data.collections.get("WINDOW_REFLECTION_SPOTLIGHTS_FAR_END")
    if not col:
        col = bpy.data.collections.new("WINDOW_REFLECTION_SPOTLIGHTS_FAR_END")
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = False
    col.hide_render = False
    target = find_storefront_target()
    # Higher energy and tighter cones aimed at glass. Still shadowless to reduce scene-wide cast shadows.
    specs=[
        ("TRAFFIC_REFLECT_Red_BrakeLight", (-8.0, -18.0, 2.4), (1.0, 0.03, 0.015), 480.0, 0.38),
        ("TRAFFIC_REFLECT_White_Headlight", (-2.5, -19.5, 2.2), (1.0, 0.92, 0.76), 620.0, 0.34),
        ("TRAFFIC_REFLECT_Amber_StreetTurn", (3.2, -18.5, 2.5), (1.0, 0.38, 0.04), 500.0, 0.38),
        ("TRAFFIC_REFLECT_Green_SignalBounce", (8.2, -20.0, 2.6), (0.05, 1.0, 0.18), 330.0, 0.40),
    ]
    rows=[]
    for name, loc, color, energy, spot_size in specs:
        obj=bpy.data.objects.get(name)
        if not obj:
            data=bpy.data.lights.new(name+"_Data", type="SPOT")
            obj=bpy.data.objects.new(name, data)
            col.objects.link(obj)
        else:
            try:
                col.objects.link(obj)
            except Exception:
                pass
        obj.location = Vector(loc)
        look_at(obj, target)
        obj.data.energy = energy
        obj.data.color = color
        obj.data.spot_size = spot_size
        obj.data.spot_blend = 0.9
        obj.data.use_shadow = False
        obj["reflection_light_palette"] = "red_white_amber_green"
        obj["purpose"] = "far-end storefront glass reflection test"
        rows.append({"name":name, "location":[round(v,6) for v in obj.location], "energy":energy, "color":list(color), "spot_size":spot_size, "target":[round(target.x,6),round(target.y,6),round(target.z,6)]})
    log(f"[reflection] boosted {len(rows)} red/white/amber/green far-end spotlights and aimed at storefront glass")
    return rows

def is_window_or_glass_obj(o):
    text = object_text(o) + " " + material_text(o)
    return any(k in text for k in ["glass", "window", "storefrontwindow", "storefront_window", "pane"])

def make_glossy_glass_materials():
    changed=[]
    for o in bpy.data.objects:
        if o.type != "MESH" or not is_window_or_glass_obj(o):
            continue
        if len(o.material_slots) == 0:
            mat = bpy.data.materials.new("WINDOW_MAT_TrafficReflectiveGlass")
            o.data.materials.append(mat)
        for slot in o.material_slots:
            mat = slot.material
            if not mat:
                continue
            mat.use_nodes = True
            mat.blend_method = "BLEND"
            mat.use_screen_refraction = True if hasattr(mat, "use_screen_refraction") else getattr(mat, "use_screen_refraction", False)
            mat.show_transparent_back = True if hasattr(mat, "show_transparent_back") else getattr(mat, "show_transparent_back", False)
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            if bsdf:
                for input_name, value in [
                    ("Base Color", (0.015, 0.018, 0.022, 0.62)),
                    ("Alpha", 0.58),
                    ("Roughness", 0.018),
                    ("Metallic", 0.0),
                    ("Specular IOR Level", 1.0),
                    ("Coat Weight", 0.75),
                    ("Coat Roughness", 0.025),
                ]:
                    if input_name in bsdf.inputs:
                        bsdf.inputs[input_name].default_value = value
            changed.append({"object": o.name, "material": mat.name})
    # Try enabling Eevee reflection-related settings where available.
    scene=bpy.context.scene
    ee = getattr(scene, "eevee", None)
    if ee:
        for attr, val in [
            ("use_gtao", True),
            ("gtao_distance", 3),
            ("gtao_factor", 1.2),
            ("taa_render_samples", 64),
            ("taa_samples", 64),
            ("use_ssr", True),
            ("use_ssr_refraction", True),
            ("ssr_quality", 1.0),
            ("ssr_max_roughness", 0.22),
        ]:
            try:
                if hasattr(ee, attr):
                    setattr(ee, attr, val)
            except Exception:
                pass
    log(f"[glass] updated {len(changed)} glass/window material slot(s) for sharper spotlight reflections")
    return changed

def scan_lights():
    rows=[]
    for o in sorted([x for x in bpy.data.objects if x.type=="LIGHT"], key=lambda x:x.name):
        d=o.data
        rows.append({"name":o.name,"type":d.type,"location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
                     "rotation":[round(v,6) for v in o.rotation_euler],"energy":getattr(d,"energy",None),
                     "color":[round(v,6) for v in getattr(d,"color",[])] if hasattr(d,"color") else None,
                     "size":getattr(d,"size",None),"spot_size":getattr(d,"spot_size",None) if d.type=="SPOT" else None,
                     "spot_blend":getattr(d,"spot_blend",None) if d.type=="SPOT" else None})
    return rows

def object_report(name):
    o=bpy.data.objects.get(name)
    if not o:
        return {"name":name,"status":"missing"}
    b=bounds(o); c=counts(o)
    return {"name":name,"status":"present","visible":visible(o),"location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
            "dimensions":None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)],
            "minmax_z":None if not b else [round(b["min_z"],6),round(b["max_z"],6)],
            "vertices":c["vertices"],"faces":c["faces"],
            "modifiers":[{"name":m.name,"type":m.type,"ratio":getattr(m,"ratio",None)} for m in o.modifiers]}

def fit_scan():
    return {"key_objects":[object_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022"]]}

def write_reports(edge_removed, scrub, underglow, reflection, glass, lights, fit):
    payload={
        "edge_frame_objects_removed": edge_removed,
        "hidden_duplicate_scrub": scrub,
        "underglow_lock": underglow,
        "reflection_lights_boosted": reflection,
        "glass_materials_updated": glass,
        "lights_scan_after": lights,
        "character_fit_scan": fit,
        "notes": {
            "white_parking_strips": "Preserved. Only black/glossy ENV_Frame* edge objects were targeted.",
            "large_blend_pushes": "Future publish scripts should avoid staging blender/sackboy_scene.blend1 when possible, but scene-changing commits still need sackboy_scene.blend in Git LFS.",
            "character_deformation": "Not performed in this scrub/lighting pass. Next package can start body/head/torso proportion refinement."
        }
    }
    (REP/"scene_scrub_glass_reflection_boost_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines=["# Scene Scrub / Glass Reflection Boost v1","",
           "## Cleanup",
           f"- Black/glossy ENV_Frame* edge objects removed: **{len(edge_removed)}**",
           f"- Hidden/generated duplicate objects removed: **{len(scrub.get('removed_objects', []))}**",
           f"- Clutter collections removed: **{len(scrub.get('removed_collections', []))}**",
           "- White parking paint strips were preserved.",
           "",
           "## Lighting / Glass",
           f"- Underglow lock location: **{underglow.get('after')}**",
           f"- Far-end reflection lights boosted: **{len(reflection)}**",
           f"- Glass/window material slots updated: **{len(glass)}**",
           "- Reflection palette remains **red / white / amber / green** only. No blue.",
           "",
           "## Character Fit Scan"]
    for r in fit["key_objects"]:
        lines.append(f"- **{r.get('name')}** | {r.get('status')} | dims={r.get('dimensions')} | faces={r.get('faces')}")
    lines += ["","## Next",
              "- Inspect glass in Rendered view. In Material Preview, enable Scene Lights/Scene World to see actual scene lighting.",
              "- Next package can start Sackboy body/head/torso deformation before clothing deformation."]
    (REP/"Scene_Scrub_Glass_Reflection_Boost_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"SceneScrubGlassReflectionBoost_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def manifest():
    data={"blend_file":bpy.data.filepath,"objects":[],"collections":[]}
    for col in sorted(bpy.data.collections, key=lambda c:c.name):
        data["collections"].append({"name":col.name,"hide_viewport":bool(col.hide_viewport),"hide_render":bool(col.hide_render),"object_count":len(col.objects),"child_count":len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x:x.name):
        b=bounds(o)
        e={"name":o.name,"type":o.type,"collections":[c.name for c in o.users_collection],"visible":visible(o),
           "location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
           "rotation":[round(v,6) for v in o.rotation_euler],"scale":[round(o.scale.x,6),round(o.scale.y,6),round(o.scale.z,6)],
           "dimensions":None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)],
           "modifiers":[{"name":m.name,"type":m.type} for m in o.modifiers]}
        if o.type=="MESH":
            e.update(counts(o))
        if o.type=="LIGHT":
            e["energy"]=getattr(o.data,"energy",None)
            e["color"]=[round(v,6) for v in getattr(o.data,"color",[])] if hasattr(o.data,"color") else None
        data["objects"].append(e)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Scene Scrub / Glass Reflection Boost v1.\n\n- Targeted black/glossy ENV_Frame* parking-edge objects were removed.\n- Hidden/generated backup duplicate objects were scrubbed.\n- White parking paint strips were preserved.\n- Far-end red/white/amber/green reflection spotlights were boosted.\n- Glass/window materials were tuned for sharper reflections.\n- Character deformation was not applied in this pass.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"scene_scrub_glass_reflection_boost_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

def look_at(cam, target):
    direction=target-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()

def temp_cam(name, loc, aim, lens):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    cam.location=loc
    cam.data.lens=lens
    look_at(cam, aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def render_review():
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    hero=bpy.data.objects.get("F2")
    hb=bounds(hero) if hero else {"min_x":-1,"max_x":1,"min_y":-1,"max_y":1,"min_z":0,"max_z":3,"dim_x":2,"dim_y":2}
    hc=center(hb)
    storefront = find_storefront_target()
    cams=[
        temp_cam("TMP_ScrubParkingCheck", Vector((0,-10,2.3)), Vector((0,0,0.05)), 50),
        temp_cam("TMP_GlassReflectionBoostCheck", Vector((6,-12,3.3)), storefront, 48),
        temp_cam("TMP_CharacterFitReadyCheck", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old=scene.camera
    for cam, fn in [(cams[0],"01_ParkingEdgeScrubCheck.png"),(cams[1],"02_GlassReflectionBoostCheck.png"),(cams[2],"03_CharacterFitReadyCheck.png")]:
        scene.camera=cam
        scene.render.filepath=str(OUT/fn)
        bpy.ops.render.render(write_still=True)
        log("[render] "+fn)
    scene.camera=old
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
    log("[pass] scrub edge clutter, boost glass reflections, preserve white paint and locked lights")
    edge_removed = remove_edge_frame_objects()
    scrub = cleanup_hidden_backups_and_duplicate_collections()
    underglow = restore_underglow()
    reflection = boost_reflection_lights()
    glass = make_glossy_glass_materials()
    lights = scan_lights()
    fit = fit_scan()
    write_reports(edge_removed, scrub, underglow, reflection, glass, lights, fit)
    manifest()
    render_review()
    out=ROOT/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] "+str(out))

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"SceneScrubGlassReflectionBoost_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
