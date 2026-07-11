import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "parking_height_underglow_repair_v1"
REP = ROOT / "reports" / "parking_height_underglow_repair_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

TARGET_SURFACE_Z = 0.3007543087005615
PAINT_OFFSET = 0.0020
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)
BAD_DECAL_NAME_PARTS = ["ENV_PlazaShell", "PlazaShell"]

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "ParkingHeightUnderglowRepair_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "ParkingHeightUnderglowRepair_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs),"max_x":max(xs),"min_y":min(ys),"max_y":max(ys),"min_z":min(zs),"max_z":max(zs),
            "dim_x":max(xs)-min(xs),"dim_y":max(ys)-min(ys),"dim_z":max(zs)-min(zs)}

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
    col = ensure_col("PARKING_HEIGHT_REPAIR_BACKUPS_HIDDEN", True)
    safe = o.name.replace(" ","_").replace("(","").replace(")","").replace(".","_")
    name = f"PARKING_HEIGHT_BACKUP_{label}_{safe}"
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

def repair_asphalt_height():
    asphalt = find_imported_asphalt()
    if not asphalt:
        raise RuntimeError("Could not find imported Asphalt ground mesh.")
    backup_mesh(asphalt, "before_height_repair")
    asphalt.hide_viewport = False
    asphalt.hide_render = False
    for col in asphalt.users_collection:
        col.hide_viewport = False
        col.hide_render = False
    oldb = bounds(asphalt)
    flatten_world_z(asphalt, TARGET_SURFACE_Z)
    asphalt["active_visible_flat_imported_asphalt"] = True
    asphalt["parking_height_repair_plane_z"] = TARGET_SURFACE_Z
    env = bpy.data.objects.get("ENV_Asphalt")
    if env and env != asphalt:
        env.hide_viewport = True
        env.hide_render = True
    nb = bounds(asphalt)
    log(f"[asphalt] lowered/flattened imported Asphalt ground from old z {None if not oldb else oldb['max_z']:.6f} to z={TARGET_SURFACE_Z:.6f}; ENV_Asphalt hidden")
    return {"name": asphalt.name, "old_bounds": oldb, "new_bounds": nb, "target_z": TARGET_SURFACE_Z, "env_asphalt_hidden": bool(env and env != asphalt)}

def delete_bad_and_existing_decals():
    removed=[]
    for o in list(bpy.data.objects):
        if o.name.startswith("PARKING_DECAL_"):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    log(f"[paint] removed {len(removed)} prior parking decal objects")
    return removed

def choose_paint_material(src=None):
    if src and src.type == "MESH":
        for slot in src.material_slots:
            if slot.material:
                return slot.material
    mat = bpy.data.materials.get("PARKING_DECAL_OffWhitePaint")
    if not mat:
        mat = bpy.data.materials.new("PARKING_DECAL_OffWhitePaint")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.78, 0.72, 0.58, 1)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.78
    return mat

def candidate_old_paint_objects():
    out=[]; seen=set()
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        n = o.name
        if n.startswith("PARKING_DECAL_"):
            continue
        text = (n + " " + " ".join(c.name for c in o.users_collection)).lower()
        # Exclude shell/environment/non-paint geometry. This specifically prevents PARKING_DECAL_*ENV_PlazaShell.
        if any(part.lower() in text for part in ["plazashell", "plaza shell", "env_plaza", "shell"]):
            continue
        if any(bad in text for bad in ["asphalt","ground","lamp","sign","sidewalk","curb","storefront","camera","manhole","hatch","sewer","backup","hoodie","cargo","shoe","car","audi","window","glass"]):
            continue
        if any(k in text for k in ["hparking","stripe","strip","paint","line","divider","spine","parking"]):
            b = bounds(o)
            if not b:
                continue
            # Keep only stripe-like pieces, not giant shells or accidental slabs.
            if b["dim_x"] > 16 or b["dim_y"] > 16:
                continue
            if b["dim_x"] < 0.015 or b["dim_y"] < 0.015:
                continue
            if n not in seen:
                out.append(o); seen.add(n)
    return out

def create_decal(src, idx, z, col):
    b = bounds(src)
    if not b:
        return None
    minx,maxx,miny,maxy = b["min_x"], b["max_x"], b["min_y"], b["max_y"]
    mesh = bpy.data.meshes.new(f"PARKING_DECAL_Mesh_{idx:03d}")
    mesh.from_pydata([(minx,miny,z),(maxx,miny,z),(maxx,maxy,z),(minx,maxy,z)], [], [(0,1,2,3)])
    mesh.update()
    obj = bpy.data.objects.new(f"PARKING_DECAL_{idx:03d}_{src.name}", mesh)
    col.objects.link(obj)
    mat = choose_paint_material(src)
    if mat:
        obj.data.materials.append(mat)
    obj["source_paint_object"] = src.name
    obj["decal_plane_z"] = z
    try:
        obj.visible_shadow = False
    except Exception:
        pass
    try:
        obj.cycles_visibility.shadow = False
    except Exception:
        pass
    return obj

def rebuild_paint_decals():
    removed = delete_bad_and_existing_decals()
    col = ensure_col("PARKING_PAINT_DECALS_FLAT", False)
    old_col = ensure_col("PARKING_PAINT_ORIGINALS_HIDDEN", True)
    z = TARGET_SURFACE_Z + PAINT_OFFSET
    candidates = candidate_old_paint_objects()
    rows=[]
    for idx, src in enumerate(candidates, start=1):
        backup_mesh(src, "old_paint_before_low_decal_rebuild")
        dec = create_decal(src, idx, z, col)
        src.hide_viewport = True
        src.hide_render = True
        link(src, old_col)
        rows.append({"source": src.name, "decal": None if not dec else dec.name, "source_dims": None if not bounds(src) else [round(bounds(src)["dim_x"],4), round(bounds(src)["dim_y"],4), round(bounds(src)["dim_z"],4)]})
    # Safety remove the named bad object if a variant survived.
    bad_removed=[]
    for o in list(bpy.data.objects):
        if o.name.startswith("PARKING_DECAL_") and any(part in o.name for part in BAD_DECAL_NAME_PARTS):
            bad_removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    log(f"[paint] rebuilt {len(rows)} flat decals at z={z:.6f}; bad plaza decals removed after rebuild={len(bad_removed)}")
    return {"prior_decals_removed": len(removed), "flat_decals_created": len(rows), "decal_z": z, "bad_plaza_decals_removed": bad_removed, "objects": rows}

def repair_hatch():
    objs=[]
    col = bpy.data.collections.get("Cast iron sewer hatch")
    if col:
        objs = [o for o in col.all_objects if o.type == "MESH"]
    if not objs:
        for o in bpy.data.objects:
            if o.type != "MESH":
                continue
            text=(o.name+" "+" ".join(c.name for c in o.users_collection)).lower()
            if any(k in text for k in ["sewer","hatch","manhole","cast iron"]):
                objs.append(o)
    bs=[bounds(o) for o in objs if bounds(o)]
    rows=[]
    if bs:
        minz=min(b["min_z"] for b in bs)
        dz=(TARGET_SURFACE_Z + 0.0025) - minz
        for o in objs:
            o.location.z += dz
            o.hide_viewport = False
            o.hide_render = False
            for c in o.users_collection:
                c.hide_viewport = False
                c.hide_render = False
            nb=bounds(o)
            rows.append({"name": o.name, "min_z": None if not nb else round(nb["min_z"],6), "max_z": None if not nb else round(nb["max_z"],6)})
    log(f"[hatch] adjusted {len(rows)} hatch/manhole object(s)")
    return rows

def restore_underglow():
    light = bpy.data.objects.get(UNDERGLOW_NAME)
    if not light:
        log(f"[underglow] WARNING: {UNDERGLOW_NAME} not found")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(light.location.x,6), round(light.location.y,6), round(light.location.z,6)]
    light.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(light.location.x,6), round(light.location.y,6), round(light.location.z,6)]
    log(f"[underglow] restored {UNDERGLOW_NAME} from {before} to {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after, "target": list(UNDERGLOW_LOCK_LOC)}

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
            "collections":[c.name for c in o.users_collection],
            "modifiers":[{"name":m.name,"type":m.type,"ratio":getattr(m,"ratio",None)} for m in o.modifiers]}

def write_reports(asphalt, paint, hatch, underglow, lights):
    fit = {"key_objects":[object_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022"]]}
    payload={
        "asphalt_height_repair": asphalt,
        "paint_decal_repair": paint,
        "hatch_repair": hatch,
        "underglow_restore": underglow,
        "lights_scanned_after_restore": lights,
        "character_fit_scan": fit,
        "reflection_lighting_plan":{
            "status":"not_added_in_this_repair_pass",
            "approved_colors":["red","white","amber","green"],
            "note":"The far-end reflection lights are approved conceptually but intentionally not added during this repair pass."
        },
        "locked":{"car":"not moved","existing_amber_lights":"not modified except underglow location restore","storefront":"not modified","sky_world_hdri":"not modified","character":"not modified"}
    }
    (REP/"parking_height_underglow_repair_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines=["# Parking Height / Underglow Repair v1","",
           "## Repair Summary",
           f"- Imported asphalt lowered/flattened to z: **{asphalt.get('target_z')}**",
           f"- Old/new asphalt object: **{asphalt.get('name')}**",
           f"- Prior decals removed: **{paint.get('prior_decals_removed')}**",
           f"- Flat parking decals rebuilt: **{paint.get('flat_decals_created')}**",
           f"- Bad plaza-shell decals removed: **{len(paint.get('bad_plaza_decals_removed', []))}**",
           f"- Hatch/manhole objects adjusted: **{len(hatch)}**",
           f"- Underglow restored to: **{underglow.get('after')}**",
           "",
           "## Reflection Lights",
           "- Red / white / amber / green far-end reflection spotlights were **not added in this repair pass**.",
           "- They are the next controlled lighting package after this surface repair is visually approved.",
           "",
           "## Fit Direction",
           "- Clothing/body fit is still scan-only here.",
           "- Next character pass should refine Sackboy torso/head/body proportions before deforming hoodie/pants/shoes.",
           "",
           "## Current Lights"]
    for l in lights:
        lines.append(f"- **{l['name']}** | type={l['type']} | loc={l['location']} | energy={l['energy']} | color={l['color']}")
    (REP/"Parking_Height_Underglow_Repair_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"ParkingHeightUnderglowRepair_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

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
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Parking Height / Underglow Repair v1.\n\n- Imported Asphalt ground is visible and flattened/lowered to the previous clean parking surface height.\n- Bad PARKING_DECAL_*ENV_PlazaShell decal was removed by rebuilding paint decals from filtered paint sources.\n- Old raised paint-strip meshes are hidden and replaced with flat decal planes.\n- HERO_CyanUnderglow_Area was restored to its locked location under the car.\n- No far-end reflection lights were added in this repair pass.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"parking_height_underglow_repair_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

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

def render_review(asphalt_obj):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    ab=bounds(asphalt_obj) if asphalt_obj else {"min_x":-18,"max_x":18,"min_y":-18,"max_y":18,"min_z":TARGET_SURFACE_Z,"max_z":TARGET_SURFACE_Z,"dim_x":36,"dim_y":36}
    c=center(ab)
    car=bpy.data.objects.get("Audi e-tron GT quattro Black")
    cb=bounds(car) if car else ab
    cc=center(cb)
    hero=bpy.data.objects.get("F2")
    hb=bounds(hero) if hero else ab
    hc=center(hb)
    cams=[
        temp_cam("TMP_HeightRepairPaintLow", Vector((c.x+7.0,c.y-10.5,TARGET_SURFACE_Z+2.0)), Vector((c.x,c.y,TARGET_SURFACE_Z+0.02)), 50),
        temp_cam("TMP_HeightRepairCarUnderglow", Vector((cc.x+5.0,cc.y-7.5,TARGET_SURFACE_Z+2.2)), Vector((cc.x,cc.y,TARGET_SURFACE_Z+0.45)), 55),
        temp_cam("TMP_HeightRepairCharacter", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old=scene.camera
    for cam, fn in [(cams[0],"01_LoweredAsphaltPaintDecals.png"),(cams[1],"02_UnderglowRestoredCheck.png"),(cams[2],"03_CharacterHeightCheck.png")]:
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
    log("[repair] lowering imported asphalt and restoring locked underglow")
    asphalt = repair_asphalt_height()
    paint = rebuild_paint_decals()
    hatch = repair_hatch()
    underglow = restore_underglow()
    lights = scan_lights()
    asphalt_obj = bpy.data.objects.get(asphalt["name"])
    write_reports(asphalt, paint, hatch, underglow, lights)
    manifest()
    render_review(asphalt_obj)
    out=ROOT/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] "+str(out))

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"ParkingHeightUnderglowRepair_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
