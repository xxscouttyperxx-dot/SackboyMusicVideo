import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "surface_repair_character_fit_scan_v1B"
REP = ROOT / "reports" / "surface_repair_character_fit_scan_v1B"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "SurfaceRepairCharacterFitScan_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "SurfaceRepairCharacterFitScan_report.txt").write_text("", encoding="utf-8")

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

def mesh_counts(o):
    if o and o.type == "MESH":
        return {"vertices": len(o.data.vertices), "faces": len(o.data.polygons)}
    return {"vertices":0, "faces":0}

def ensure_col(name, hide=False):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = hide
    col.hide_render = hide
    return col

def link_obj(o, col):
    try:
        if o.name not in col.objects:
            col.objects.link(o)
    except Exception:
        pass

def backup_mesh(o, label):
    if not o or o.type != "MESH":
        return None
    col = ensure_col("SURFACE_REPAIR_BACKUPS_HIDDEN", True)
    safe = o.name.replace(" ","_").replace("(","").replace(")","").replace(".","_")
    name = f"SURFACE_BACKUP_{label}_{safe}"
    old = bpy.data.objects.get(name)
    if old:
        return old
    mesh = o.data.copy()
    mesh.name = name + "_Mesh"
    dup = bpy.data.objects.new(name, mesh)
    dup.matrix_world = o.matrix_world.copy()
    dup.hide_viewport = True
    dup.hide_render = True
    dup["backup_for"] = o.name
    dup["backup_reason"] = label
    link_obj(dup, col)
    return dup

def ensure_asphalt_material(obj):
    mat = bpy.data.materials.get("ENV_MAT_Flat_Dark_Asphalt")
    if not mat:
        mat = bpy.data.materials.new("ENV_MAT_Flat_Dark_Asphalt")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.035, 0.033, 0.031, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.88
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
    if obj.type == "MESH":
        if len(obj.material_slots) == 0:
            obj.data.materials.append(mat)
        elif not any(slot.material for slot in obj.material_slots):
            obj.data.materials[0] = mat
    return mat.name

def flatten_mesh_world_z(obj, z):
    inv = obj.matrix_world.inverted()
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        w.z = z
        v.co = inv @ w
    obj.data.update()

def find_env_asphalt():
    obj = bpy.data.objects.get("ENV_Asphalt")
    if obj and obj.type == "MESH":
        return obj
    mesh = bpy.data.meshes.new("ENV_Asphalt_Mesh")
    size = 36.0
    mesh.from_pydata([(-size/2,-size/2,0),(size/2,-size/2,0),(size/2,size/2,0),(-size/2,size/2,0)], [], [(0,1,2,3)])
    mesh.update()
    obj = bpy.data.objects.new("ENV_Asphalt", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj

def show_object_and_collections(obj):
    obj.hide_viewport = False
    obj.hide_render = False
    for col in obj.users_collection:
        col.hide_viewport = False
        col.hide_render = False

def paint_objects():
    out=[]; seen=set()
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        text = (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()
        if any(bad in text for bad in ["asphalt","ground","lamp","sign","sidewalk","curb","storefront","camera","manhole","hatch","sewer"]):
            continue
        if any(k in text for k in ["hparking","stripe","strip","paint","line","divider","spine","parking"]):
            if o.name not in seen:
                seen.add(o.name)
                out.append(o)
    return out

def set_mesh_world_z_plane(obj, z):
    if obj.type != "MESH":
        return
    backup_mesh(obj, "before_paint_flatten")
    inv = obj.matrix_world.inverted()
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        w.z = z
        v.co = inv @ w
    obj.data.update()

def collection_objects_named(name):
    col = bpy.data.collections.get(name)
    if not col:
        return []
    return [o for o in col.all_objects if o.type == "MESH"]

def hatch_objects():
    objs = collection_objects_named("Cast iron sewer hatch")
    if objs:
        return objs
    out=[]
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        text = (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()
        if any(k in text for k in ["sewer", "hatch", "manhole", "cast iron"]):
            out.append(o)
    return out

def union_bounds(objs):
    bs=[bounds(o) for o in objs if bounds(o)]
    if not bs:
        return None
    return {"min_x":min(b["min_x"] for b in bs),"max_x":max(b["max_x"] for b in bs),
            "min_y":min(b["min_y"] for b in bs),"max_y":max(b["max_y"] for b in bs),
            "min_z":min(b["min_z"] for b in bs),"max_z":max(b["max_z"] for b in bs),
            "dim_x":max(b["max_x"] for b in bs)-min(b["min_x"] for b in bs),
            "dim_y":max(b["max_y"] for b in bs)-min(b["min_y"] for b in bs),
            "dim_z":max(b["max_z"] for b in bs)-min(b["min_z"] for b in bs)}

def repair_surface():
    env = find_env_asphalt()
    backup_mesh(env, "before_surface_repair")
    show_object_and_collections(env)

    eb = bounds(env)
    plane_z = eb["max_z"] if eb else 0.0
    flatten_mesh_world_z(env, plane_z)
    show_object_and_collections(env)
    mat_name = ensure_asphalt_material(env)

    imported = bpy.data.objects.get("Asphalt ground")
    imported_hidden = None
    if imported and imported != env:
        imported.hide_viewport = True
        imported.hide_render = True
        imported_hidden = imported.name

    if env.modifiers.get("FLAT_ASPHALT_VISUAL_THICKNESS"):
        env.modifiers.remove(env.modifiers["FLAT_ASPHALT_VISUAL_THICKNESS"])

    paint_z = plane_z + 0.0012
    paints = paint_objects()
    paint_rows=[]
    for p in paints:
        oldb = bounds(p)
        oldz = None if not oldb else oldb["min_z"]
        for m in list(p.modifiers):
            if m.name == "PARKING_TO_ASPHALT_PREVIEW":
                p.modifiers.remove(m)
        set_mesh_world_z_plane(p, paint_z)
        p["surface_repair_paint_plane_z"] = paint_z
        nb = bounds(p)
        paint_rows.append({"name":p.name, "old_min_z": None if oldz is None else round(oldz,6), "new_min_z": None if not nb else round(nb["min_z"],6)})

    hatches = hatch_objects()
    hatch_rows=[]
    hb = union_bounds(hatches)
    if hb:
        dz = (plane_z + 0.0015) - hb["min_z"]
        for h in hatches:
            h.location.z += dz
            h.hide_viewport = False
            h.hide_render = False
            for col in h.users_collection:
                col.hide_viewport = False
                col.hide_render = False
            nb = bounds(h)
            hatch_rows.append({"name":h.name, "new_min_z": None if not nb else round(nb["min_z"],6), "new_max_z": None if not nb else round(nb["max_z"],6)})

    log(f"[surface] ENV_Asphalt visible, flattened at z={plane_z:.6f}; paint planes={len(paint_rows)}; hatch objects={len(hatch_rows)}")
    return {"env_asphalt": env.name, "flat_plane_z": plane_z, "asphalt_material": mat_name, "imported_bumpy_asphalt_hidden": imported_hidden,
            "paint_z": paint_z, "paint_objects_adjusted": len(paint_rows), "paint_objects": paint_rows,
            "hatch_objects_adjusted": len(hatch_rows), "hatch_objects": hatch_rows}

def scan_lights():
    rows=[]
    for o in sorted([x for x in bpy.data.objects if x.type=="LIGHT"], key=lambda x:x.name):
        d=o.data
        rows.append({"name":o.name, "type":d.type, "location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
                     "rotation":[round(v,6) for v in o.rotation_euler], "energy":getattr(d,"energy",None),
                     "color":[round(v,6) for v in getattr(d,"color",[])] if hasattr(d,"color") else None,
                     "size":getattr(d,"size",None), "spot_size":getattr(d,"spot_size",None) if d.type=="SPOT" else None,
                     "spot_blend":getattr(d,"spot_blend",None) if d.type=="SPOT" else None})
    return rows

def object_report(name):
    o=bpy.data.objects.get(name)
    if not o:
        return {"name":name,"status":"missing"}
    bb=bounds(o); cc=mesh_counts(o)
    return {"name":name,"status":"present","type":o.type,"collections":[c.name for c in o.users_collection],"visible":visible(o),
            "location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
            "dimensions":None if not bb else [round(bb["dim_x"],6),round(bb["dim_y"],6),round(bb["dim_z"],6)],
            "minmax_z":None if not bb else [round(bb["min_z"],6),round(bb["max_z"],6)],
            "vertices":cc["vertices"],"faces":cc["faces"],
            "modifiers":[{"name":m.name,"type":m.type,"ratio":getattr(m,"ratio",None)} for m in o.modifiers]}

def character_fit_scan():
    names = ["F2", "Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022", "Utility Box (Photoscanned)", "Lid.001"]
    rows=[object_report(n) for n in names]
    shoe_objs=[]
    col=bpy.data.collections.get("Shoes")
    if col:
        for o in col.all_objects:
            if o.type=="MESH":
                shoe_objs.append(object_report(o.name))
    return {"key_objects":rows, "shoe_collection_meshes":shoe_objs}

def reports(surface, lights, fit):
    payload={"surface_repair":surface, "lights_scanned_preserved":lights, "character_fit_scan":fit,
             "reflection_light_plan":{"approved_palette":["red","white","amber","green"],"rejected_palette":["blue"],
             "note":"Future package can add off-scene spotlights aimed at glossy storefront glass only. This package does not add lights."},
             "locked":{"existing_lights":"scanned only, not modified","car":"not modified","storefront":"not modified","sky_world_hdri":"not modified","character_body":"not modified","clothing_fit":"scan only"}}
    (REP/"surface_repair_character_fit_scan_v1B.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    lines=["# Surface Repair / Character Fit Scan v1B",""]
    lines += ["## Surface Repair", f"- Active asphalt shown/flattened: **{surface.get('env_asphalt')}** at z **{surface.get('flat_plane_z')}**",
              f"- Bumpy imported asphalt hidden: **{surface.get('imported_bumpy_asphalt_hidden')}**",
              f"- Paint strips flattened to plane z: **{surface.get('paint_z')}**", f"- Paint objects adjusted: **{surface.get('paint_objects_adjusted')}**",
              f"- Manhole/hatch objects adjusted: **{surface.get('hatch_objects_adjusted')}**", ""]
    lines.append("## Character / Clothing Fit Scan")
    for r in fit["key_objects"]:
        lines.append(f"- **{r.get('name')}** | {r.get('status')} | dims={r.get('dimensions')} | faces={r.get('faces')} | modifiers={r.get('modifiers')}")
    lines += ["","## Current Light Scan"]
    for l in lights:
        lines.append(f"- **{l['name']}** | type={l['type']} | loc={l['location']} | energy={l['energy']} | color={l['color']} | spot_size={l.get('spot_size')} | spot_blend={l.get('spot_blend')}")
    lines += ["","## Window Reflection Lighting Plan","- Later reflection-light package should use **red / white / amber / green**, not blue.",
              "- Existing amber lights should remain untouched; new reflection lights should be separately named and placed away from the character/car path.",
              "","## Next Fit Direction","- Do not force clothing onto the current body yet.",
              "- First use this scan to refine body/head/torso proportions and then deform clothing to the final character."]
    (REP/"Surface_Repair_Character_Fit_Scan_v1B.md").write_text("\n".join(lines),encoding="utf-8")
    (OUT/"SurfaceRepairCharacterFitScan_status.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")

def manifest():
    data={"blend_file":bpy.data.filepath,"objects":[],"collections":[]}
    for col in sorted(bpy.data.collections,key=lambda c:c.name):
        data["collections"].append({"name":col.name,"hide_viewport":bool(col.hide_viewport),"hide_render":bool(col.hide_render),"object_count":len(col.objects),"child_count":len(col.children)})
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        bb=bounds(o)
        e={"name":o.name,"type":o.type,"collections":[c.name for c in o.users_collection],"visible":visible(o),
           "location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
           "rotation":[round(v,6) for v in o.rotation_euler], "scale":[round(o.scale.x,6),round(o.scale.y,6),round(o.scale.z,6)],
           "dimensions":None if not bb else [round(bb["dim_x"],6),round(bb["dim_y"],6),round(bb["dim_z"],6)],
           "modifiers":[{"name":m.name,"type":m.type} for m in o.modifiers]}
        if o.type=="MESH":
            e.update(mesh_counts(o))
        if o.type=="LIGHT":
            e["energy"]=getattr(o.data,"energy",None)
            e["color"]=[round(v,6) for v in getattr(o.data,"color",[])] if hasattr(o.data,"color") else None
        data["objects"].append(e)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Surface Repair / Character Fit Scan v1B.\n\n- ENV_Asphalt is visible and flat.\n- Parking paint strips are zero-height planes just above asphalt.\n- Manhole/hatch objects were raised back onto asphalt.\n- Current lights were scanned and preserved.\n- Character/clothing fit measurements were recorded; no body or clothing deformation was applied.\n",encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"surface_repair_character_fit_scan_v1B","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)},indent=2),encoding="utf-8")

def look_at(cam, target):
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()

def temp_cam(name, loc, aim, lens):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    cam.location=loc
    cam.data.lens=lens
    look_at(cam,aim)
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
    env=bpy.data.objects.get("ENV_Asphalt")
    eb=bounds(env) if env else {"min_x":-18,"max_x":18,"min_y":-18,"max_y":18,"min_z":0,"max_z":0,"dim_x":36,"dim_y":36,"dim_z":0.1}
    c=center(eb)
    hero=bpy.data.objects.get("F2")
    hb=bounds(hero) if hero else eb
    hc=center(hb)
    cams=[temp_cam("TMP_SurfacePaintLowAngle_v1B", Vector((c.x+8.0,c.y-11.0,eb["max_z"]+3.2)), Vector((c.x,c.y,eb["max_z"]+0.03)), 50),
          temp_cam("TMP_SurfacePaintTopCheck_v1B", Vector((c.x,c.y-0.1,eb["max_z"]+14.0)), Vector((c.x,c.y,eb["max_z"]+0.02)), 45),
          temp_cam("TMP_CharacterFitScan_v1B", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.6)), Vector((hc.x,hc.y,hc.z+0.45)), 55)]
    old=scene.camera
    for cam, fn in [(cams[0],"01_SurfacePaintLowAngle.png"),(cams[1],"02_SurfacePaintTopCheck.png"),(cams[2],"03_CharacterFitScan.png")]:
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
    log("[lock] preserving existing lights; no reflection lights added")
    surface=repair_surface()
    lights=scan_lights()
    fit=character_fit_scan()
    reports(surface, lights, fit)
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
        with (OUT/"SurfaceRepairCharacterFitScan_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
