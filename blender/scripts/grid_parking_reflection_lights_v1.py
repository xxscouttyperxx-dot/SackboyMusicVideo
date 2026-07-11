import json, math, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "grid_parking_reflection_lights_v1"
REP = ROOT / "reports" / "grid_parking_reflection_lights_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

GRID_Z = 0.0
PAINT_Z = 0.003
HATCH_Z = 0.004
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "GridParkingReflectionLights_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "GridParkingReflectionLights_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {
        "min_x":min(xs), "max_x":max(xs),
        "min_y":min(ys), "max_y":max(ys),
        "min_z":min(zs), "max_z":max(zs),
        "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)
    }

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

def link(o, col):
    try:
        if o.name not in col.objects:
            col.objects.link(o)
    except Exception:
        pass

def backup_mesh(o, label):
    if not o or o.type != "MESH":
        return None
    col = ensure_col("GRID_PARKING_REPAIR_BACKUPS_HIDDEN", True)
    safe = o.name.replace(" ","_").replace("(","").replace(")","").replace(".","_")
    name = f"GRID_REPAIR_BACKUP_{label}_{safe}"
    if bpy.data.objects.get(name):
        return bpy.data.objects[name]
    mesh = o.data.copy()
    mesh.name = name + "_Mesh"
    dup = bpy.data.objects.new(name, mesh)
    dup.matrix_world = o.matrix_world.copy()
    dup.hide_viewport = True
    dup.hide_render = True
    dup["backup_for"] = o.name
    dup["backup_reason"] = label
    link(dup, col)
    return dup

def flatten_world_z(o, z):
    if not o or o.type != "MESH":
        return
    inv = o.matrix_world.inverted()
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        w.z = z
        v.co = inv @ w
    o.data.update()

def find_imported_asphalt():
    obj = bpy.data.objects.get("Asphalt ground")
    if obj and obj.type == "MESH":
        return obj
    for o in bpy.data.objects:
        if o.type == "MESH" and "asphalt" in o.name.lower() and o.name != "ENV_Asphalt":
            return o
    return None

def repair_asphalt_to_grid():
    asphalt = find_imported_asphalt()
    if not asphalt:
        raise RuntimeError("Could not find imported Asphalt ground mesh.")
    backup_mesh(asphalt, "before_grid_lower")
    oldb = bounds(asphalt)
    asphalt.hide_viewport = False
    asphalt.hide_render = False
    for c in asphalt.users_collection:
        c.hide_viewport = False
        c.hide_render = False
    flatten_world_z(asphalt, GRID_Z)
    asphalt["grid_parking_active_asphalt"] = True
    asphalt["grid_parking_plane_z"] = GRID_Z
    env = bpy.data.objects.get("ENV_Asphalt")
    if env and env != asphalt:
        env.hide_viewport = True
        env.hide_render = True
    nb = bounds(asphalt)
    log(f"[asphalt] imported Asphalt ground lowered/flattened to grid z={GRID_Z:.6f}")
    return {"name": asphalt.name, "old_bounds": oldb, "new_bounds": nb, "grid_z": GRID_Z, "env_asphalt_hidden": bool(env and env != asphalt)}

def remove_decal_objects():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith("PARKING_DECAL_"):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    log(f"[paint] removed {len(removed)} generated decal object(s)")
    return removed

def candidate_original_paint_objects():
    out=[]; seen=set()
    # Prefer prior hidden originals collection if it exists.
    for cname in ["PARKING_PAINT_ORIGINALS_HIDDEN", "PARKING_PAINT_DECALS_FLAT"]:
        col = bpy.data.collections.get(cname)
        if col:
            for o in col.all_objects:
                if o.type == "MESH" and not o.name.startswith("PARKING_DECAL_"):
                    if o.name not in seen:
                        out.append(o); seen.add(o.name)
    # Add other paint-like objects still in scene.
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name in seen or o.name.startswith("PARKING_DECAL_"):
            continue
        text = (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()
        if any(bad in text for bad in ["plazashell","plaza shell","env_plaza","shell","asphalt","ground","lamp","sign","sidewalk","curb","storefront","camera","manhole","hatch","sewer","backup","hoodie","cargo","shoe","car","audi","window","glass"]):
            continue
        if any(k in text for k in ["hparking","stripe","strip","paint","line","divider","spine","parking"]):
            b = bounds(o)
            if not b:
                continue
            if b["dim_x"] > 18 or b["dim_y"] > 18:
                continue
            if b["dim_x"] < 0.01 or b["dim_y"] < 0.01:
                continue
            out.append(o); seen.add(o.name)
    return out

def restore_original_paint_flat():
    removed = remove_decal_objects()
    col = ensure_col("PARKING_PAINT_FLAT_ORIGINALS_ACTIVE", False)
    originals = candidate_original_paint_objects()
    rows=[]
    for o in originals:
        # Exclude any accidental plaza/shell/large object one more time.
        lower = o.name.lower()
        if "plazashell" in lower or "env_plaza" in lower or "shell" in lower:
            continue
        backup_mesh(o, "before_flat_grid_restore")
        for m in list(o.modifiers):
            if m.name == "PARKING_TO_ASPHALT_PREVIEW":
                o.modifiers.remove(m)
        flatten_world_z(o, PAINT_Z)
        o.location.z = o.location.z  # keep transforms stable after vertex flatten
        o.hide_viewport = False
        o.hide_render = False
        for c in o.users_collection:
            # do not unhide backup collections, only put it in active collection.
            pass
        link(o, col)
        try:
            o.visible_shadow = False
        except Exception:
            pass
        try:
            o.cycles_visibility.shadow = False
        except Exception:
            pass
        o["grid_parking_paint_restored_z"] = PAINT_Z
        b = bounds(o)
        rows.append({"name": o.name, "min_z": None if not b else round(b["min_z"],6), "max_z": None if not b else round(b["max_z"],6), "dims": None if not b else [round(b["dim_x"],4), round(b["dim_y"],4), round(b["dim_z"],4)]})
    log(f"[paint] restored {len(rows)} original paint strip object(s) as flat visible grid-level paint at z={PAINT_Z:.6f}")
    return {"generated_decals_removed": len(removed), "original_paint_restored": len(rows), "paint_z": PAINT_Z, "objects": rows}

def hatch_objects():
    col = bpy.data.collections.get("Cast iron sewer hatch")
    if col:
        objs=[o for o in col.all_objects if o.type=="MESH"]
        if objs:
            return objs
    out=[]
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        text=(o.name+" "+" ".join(c.name for c in o.users_collection)).lower()
        if any(k in text for k in ["sewer","hatch","manhole","cast iron"]):
            out.append(o)
    return out

def repair_hatch_to_grid():
    objs=hatch_objects()
    bs=[bounds(o) for o in objs if bounds(o)]
    rows=[]
    if bs:
        minz=min(b["min_z"] for b in bs)
        dz = HATCH_Z - minz
        for o in objs:
            o.location.z += dz
            o.hide_viewport = False
            o.hide_render = False
            for c in o.users_collection:
                c.hide_viewport = False
                c.hide_render = False
            nb=bounds(o)
            rows.append({"name":o.name,"min_z":None if not nb else round(nb["min_z"],6), "max_z":None if not nb else round(nb["max_z"],6)})
    log(f"[hatch] adjusted {len(rows)} hatch/manhole object(s) to grid surface")
    return rows

def restore_underglow():
    light = bpy.data.objects.get(UNDERGLOW_NAME)
    if not light:
        log(f"[underglow] WARNING missing {UNDERGLOW_NAME}")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before=[round(light.location.x,6), round(light.location.y,6), round(light.location.z,6)]
    light.location=Vector(UNDERGLOW_LOCK_LOC)
    after=[round(light.location.x,6), round(light.location.y,6), round(light.location.z,6)]
    log(f"[underglow] locked {UNDERGLOW_NAME}: {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after, "target": list(UNDERGLOW_LOCK_LOC)}

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()

def find_storefront_target():
    candidates=[]
    for o in bpy.data.objects:
        text=(o.name+" "+" ".join(c.name for c in o.users_collection)).lower()
        if any(k in text for k in ["storefront","window","glass","strip mall","door"]):
            b=bounds(o)
            if b:
                candidates.append((o,b))
    if candidates:
        minx=min(b["min_x"] for _,b in candidates); maxx=max(b["max_x"] for _,b in candidates)
        miny=min(b["min_y"] for _,b in candidates); maxy=max(b["max_y"] for _,b in candidates)
        minz=min(b["min_z"] for _,b in candidates); maxz=max(b["max_z"] for _,b in candidates)
        return Vector(((minx+maxx)/2, (miny+maxy)/2, min(maxz, 3.0)))
    return Vector((0.0, 7.5, 2.0))

def create_or_update_reflection_lights():
    col=ensure_col("WINDOW_REFLECTION_SPOTLIGHTS_FAR_END", False)
    target=find_storefront_target()
    specs=[
        ("TRAFFIC_REFLECT_Red_BrakeLight", (-8.0, -18.0, 2.4), (1.0, 0.05, 0.02), 70.0, 0.55),
        ("TRAFFIC_REFLECT_White_Headlight", (-2.5, -19.5, 2.2), (1.0, 0.92, 0.78), 95.0, 0.50),
        ("TRAFFIC_REFLECT_Amber_StreetTurn", (3.2, -18.5, 2.5), (1.0, 0.42, 0.06), 75.0, 0.58),
        ("TRAFFIC_REFLECT_Green_SignalBounce", (8.2, -20.0, 2.6), (0.08, 1.0, 0.20), 45.0, 0.60),
    ]
    rows=[]
    for name, loc, color, energy, spot_size in specs:
        obj=bpy.data.objects.get(name)
        if not obj:
            data=bpy.data.lights.new(name+"_Data", type="SPOT")
            obj=bpy.data.objects.new(name, data)
            col.objects.link(obj)
        else:
            # Make sure it is in the dedicated collection.
            link(obj, col)
        obj.location=Vector(loc)
        look_at(obj, target)
        obj.data.energy=energy
        obj.data.color=color
        obj.data.spot_size=spot_size
        obj.data.spot_blend=0.82
        obj.data.use_shadow=False
        obj["reflection_light_palette"] = "red_white_amber_green"
        rows.append({"name":name,"location":[round(v,6) for v in obj.location],"target":[round(target.x,6),round(target.y,6),round(target.z,6)],"energy":energy,"color":list(color),"spot_size":spot_size})
    log(f"[reflection] added/updated {len(rows)} far-end red/white/amber/green reflection spotlights; no blue")
    return rows

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
    names=["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022"]
    return {"key_objects":[object_report(n) for n in names]}

def write_reports(asphalt, paint, hatch, underglow, reflection, lights, fit):
    payload={
        "asphalt_grid_repair": asphalt,
        "paint_restore": paint,
        "hatch_repair": hatch,
        "underglow_lock": underglow,
        "reflection_lights_added": reflection,
        "lights_scan_after": lights,
        "character_fit_scan": fit,
        "next_character_deformation_plan": {
            "step_1": "Refine Sackboy body/head/torso proportions before dressing.",
            "step_2": "Use non-destructive body backups and controlled mesh deformation.",
            "step_3": "Deform hoodie, pants, and shoes around finalized proportions.",
            "step_4": "Rig after clothing/body fit is visually approved."
        }
    }
    (REP/"grid_parking_reflection_lights_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines=["# Grid Parking / Reflection Lights v1","",
           "## Parking Repair",
           f"- Imported asphalt lowered/flattened to grid z: **{asphalt.get('grid_z')}**",
           f"- Paint strips restored from original meshes: **{paint.get('original_paint_restored')}**",
           f"- Generated decal objects removed: **{paint.get('generated_decals_removed')}**",
           f"- Hatch/manhole objects adjusted: **{len(hatch)}**",
           f"- Underglow locked to: **{underglow.get('after')}**",
           "",
           "## Reflection Lights",
           "- Added far-end spotlights in **red / white / amber / green** only.",
           "- No blue reflection light was added.",
           "- Existing amber overhead/car lights were not modified.",
           ""]
    for r in reflection:
        lines.append(f"- **{r['name']}** | loc={r['location']} | energy={r['energy']} | color={r['color']}")
    lines += ["","## Character Fit Scan"]
    for r in fit["key_objects"]:
        lines.append(f"- **{r.get('name')}** | {r.get('status')} | dims={r.get('dimensions')} | faces={r.get('faces')}")
    lines += ["","## Next Character Deformation Plan",
              "- Refine Sackboy body/head/torso proportions first.",
              "- Then deform hoodie, pants, and shoes around the finalized body.",
              "- Rig only after the visual body/clothing fit is approved."]
    (REP/"Grid_Parking_Reflection_Lights_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"GridParkingReflectionLights_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

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
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Grid Parking / Reflection Lights v1.\n\n- Imported Asphalt ground is visible and flattened at grid level.\n- Original parking paint strip meshes are restored at grid level; generated decal objects are removed.\n- HERO_CyanUnderglow_Area is locked at its under-car location.\n- Far-end red/white/amber/green spotlights were added for window reflection tests.\n- Character deformation was not applied in this pass; fit scan and plan were recorded.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"grid_parking_reflection_lights_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

def render_review(asphalt):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    ab=bounds(asphalt) if asphalt else {"min_x":-18,"max_x":18,"min_y":-18,"max_y":18,"min_z":0,"max_z":0,"dim_x":36,"dim_y":36}
    c=center(ab)
    hero=bpy.data.objects.get("F2")
    hb=bounds(hero) if hero else ab
    hc=center(hb)
    car=bpy.data.objects.get("Audi e-tron GT quattro Black")
    cb=bounds(car) if car else ab
    cc=center(cb)
    cams=[
        temp_cam("TMP_GridParkingCheck", Vector((c.x+7.0,c.y-10.5,2.0)), Vector((c.x,c.y,0.02)), 50),
        temp_cam("TMP_ReflectionLightsCheck", Vector((c.x+8.5,c.y-13.0,3.2)), Vector((0,7.5,2.0)), 45),
        temp_cam("TMP_CharacterFitNextCheck", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old=scene.camera
    for cam, fn in [(cams[0],"01_GridAsphaltPaintRestored.png"),(cams[1],"02_ReflectionLightsFarEnd.png"),(cams[2],"03_CharacterFitNextCheck.png")]:
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

def temp_cam(name, loc, aim, lens):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    cam.location=loc
    cam.data.lens=lens
    look_at(cam, aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def main():
    reset()
    log("[pass] grid parking repair, underglow lock, reflection light setup")
    asphalt=repair_asphalt_to_grid()
    paint=restore_original_paint_flat()
    hatch=repair_hatch_to_grid()
    underglow=restore_underglow()
    reflection=create_or_update_reflection_lights()
    lights=scan_lights()
    fit=fit_scan()
    write_reports(asphalt, paint, hatch, underglow, reflection, lights, fit)
    manifest()
    render_review(bpy.data.objects.get(asphalt["name"]))
    out=ROOT/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] "+str(out))

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"GridParkingReflectionLights_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
