import json, traceback, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "parking_texture_decal_fit_prep_v1"
REP = ROOT / "reports" / "parking_texture_decal_fit_prep_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "ParkingTextureDecalFitPrep_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "ParkingTextureDecalFitPrep_report.txt").write_text("", encoding="utf-8")

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

def unlink_from_non_target(o, target):
    for col in list(o.users_collection):
        if col != target:
            try:
                col.objects.unlink(o)
            except Exception:
                pass
    link(o, target)

def backup_mesh(o, label):
    if not o or o.type != "MESH":
        return None
    col = ensure_col("PARKING_DECAL_BACKUPS_HIDDEN", True)
    safe = o.name.replace(" ","_").replace("(","").replace(")","").replace(".","_")
    name = f"PARKING_BACKUP_{label}_{safe}"
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
    # fallback any imported-looking asphalt mesh
    for o in bpy.data.objects:
        if o.type == "MESH" and "asphalt" in o.name.lower() and o.name != "ENV_Asphalt":
            return o
    return None

def find_env_asphalt():
    obj = bpy.data.objects.get("ENV_Asphalt")
    if obj and obj.type == "MESH":
        return obj
    return None

def ensure_default_asphalt_mat(o):
    if not o or o.type != "MESH":
        return None
    has_mat = any(slot.material for slot in o.material_slots)
    if has_mat:
        return None
    mat = bpy.data.materials.get("ENV_MAT_OldParkingLot_DarkDirty")
    if not mat:
        mat = bpy.data.materials.new("ENV_MAT_OldParkingLot_DarkDirty")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.045, 0.043, 0.039, 1)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.92
    o.data.materials.append(mat)
    return mat.name

def select_active_asphalt():
    imported = find_imported_asphalt()
    env = find_env_asphalt()
    active = imported or env
    if not active:
        mesh = bpy.data.meshes.new("Asphalt ground_Mesh")
        size = 36.0
        mesh.from_pydata([(-size/2,-size/2,0),(size/2,-size/2,0),(size/2,size/2,0),(-size/2,size/2,0)], [], [(0,1,2,3)])
        mesh.update()
        active = bpy.data.objects.new("Asphalt ground", mesh)
        bpy.context.scene.collection.objects.link(active)
        imported = active
    return active, imported, env

def show_active_asphalt_flatten_hide_env():
    active, imported, env = select_active_asphalt()
    backup_mesh(active, "before_flatten_visible_imported_asphalt")
    active.hide_viewport = False
    active.hide_render = False
    for col in active.users_collection:
        col.hide_viewport = False
        col.hide_render = False

    ab = bounds(active)
    z = ab["max_z"] if ab else 0.0
    flatten_world_z(active, z)
    ensure_default_asphalt_mat(active)
    active["parking_active_visible_flat_asphalt"] = True
    active["parking_flat_plane_z"] = float(z)

    # Hide ENV_Asphalt to prevent z-fighting and confusion. Imported asphalt is now the visible ground.
    if env and env != active:
        env.hide_viewport = True
        env.hide_render = True

    log(f"[asphalt] visible active asphalt: {active.name}; flattened at z={z:.6f}; ENV_Asphalt hidden={bool(env and env != active)}")
    return active, z, {"active_asphalt": active.name, "plane_z": z, "env_asphalt_hidden": bool(env and env != active)}

def old_paint_objects():
    out=[]; seen=set()
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        n=o.name
        if n.startswith("PARKING_DECAL_"):
            continue
        text = (n + " " + " ".join(c.name for c in o.users_collection)).lower()
        if any(bad in text for bad in ["asphalt","ground","lamp","sign","sidewalk","curb","storefront","camera","manhole","hatch","sewer","backup"]):
            continue
        if any(k in text for k in ["hparking","stripe","strip","paint","line","divider","spine","parking"]):
            if n not in seen:
                out.append(o); seen.add(n)
    return out

def choose_paint_material(old):
    if old and old.type=="MESH":
        for slot in old.material_slots:
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

def create_decal_from_bounds(old, z, col, idx):
    b = bounds(old)
    if not b:
        return None
    # Ignore anything too large to be a parking stripe.
    if b["dim_x"] > 28 or b["dim_y"] > 28:
        return None
    # Keep tiny but visible margin. This makes a true zero-thickness decal plane.
    minx, maxx, miny, maxy = b["min_x"], b["max_x"], b["min_y"], b["max_y"]
    if abs(maxx-minx) < 0.01 or abs(maxy-miny) < 0.01:
        return None
    mesh = bpy.data.meshes.new(f"PARKING_DECAL_Mesh_{idx:03d}")
    verts = [(minx,miny,z), (maxx,miny,z), (maxx,maxy,z), (minx,maxy,z)]
    faces = [(0,1,2,3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"PARKING_DECAL_{idx:03d}_{old.name}", mesh)
    col.objects.link(obj)
    mat = choose_paint_material(old)
    if mat:
        obj.data.materials.append(mat)
    obj["source_paint_object"] = old.name
    obj["decal_plane_z"] = float(z)
    try:
        obj.visible_shadow = False
    except Exception:
        pass
    try:
        obj.cycles_visibility.shadow = False
    except Exception:
        pass
    return obj

def rebuild_paint_decals(surface_z):
    col = ensure_col("PARKING_PAINT_DECALS_FLAT", False)
    # Clear previous decal objects only.
    for o in list(col.objects):
        if o.name.startswith("PARKING_DECAL_"):
            bpy.data.objects.remove(o, do_unlink=True)

    old = old_paint_objects()
    old_col = ensure_col("PARKING_PAINT_ORIGINALS_HIDDEN", True)
    rows=[]; made=0
    decal_z = surface_z + 0.002
    for idx, o in enumerate(old, start=1):
        backup_mesh(o, "old_paint_before_decal_rebuild")
        dec = create_decal_from_bounds(o, decal_z, col, idx)
        if dec:
            made += 1
        # Hide old physical strip objects so they cannot touch tires or cast shadows.
        o.hide_viewport = True
        o.hide_render = True
        link(o, old_col)
        rows.append({"old": o.name, "decal": None if not dec else dec.name, "old_dims": None if not bounds(o) else [round(bounds(o)["dim_x"],4), round(bounds(o)["dim_y"],4), round(bounds(o)["dim_z"],4)]})
    log(f"[paint] hid {len(old)} old paint-strip meshes and built {made} flat decal planes at z={decal_z:.6f}")
    return {"old_paint_hidden": len(old), "flat_decals_created": made, "decal_z": decal_z, "objects": rows}

def hatch_objects():
    col = bpy.data.collections.get("Cast iron sewer hatch")
    if col:
        objs=[o for o in col.all_objects if o.type=="MESH"]
        if objs:
            return objs
    out=[]
    for o in bpy.data.objects:
        if o.type!="MESH":
            continue
        text=(o.name+" "+" ".join(c.name for c in o.users_collection)).lower()
        if any(k in text for k in ["sewer","hatch","manhole","cast iron"]):
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

def repair_hatch(surface_z):
    objs = hatch_objects()
    ub = union_bounds(objs)
    rows=[]
    if ub:
        dz = (surface_z + 0.0025) - ub["min_z"]
        for o in objs:
            o.location.z += dz
            o.hide_viewport = False
            o.hide_render = False
            for c in o.users_collection:
                c.hide_viewport = False
                c.hide_render = False
            nb=bounds(o)
            rows.append({"name": o.name, "min_z": None if not nb else round(nb["min_z"],6), "max_z": None if not nb else round(nb["max_z"],6)})
    log(f"[hatch] adjusted {len(rows)} hatch/manhole mesh object(s)")
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
    return {"name":name,"status":"present","type":o.type,"visible":visible(o),"collections":[c.name for c in o.users_collection],
            "location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
            "dimensions":None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)],
            "minmax_z":None if not b else [round(b["min_z"],6),round(b["max_z"],6)],
            "vertices":c["vertices"],"faces":c["faces"],
            "modifiers":[{"name":m.name,"type":m.type,"ratio":getattr(m,"ratio",None)} for m in o.modifiers]}

def character_fit_scan():
    names=["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022"]
    return {"key_objects":[object_report(n) for n in names]}

def write_reports(asphalt, paint, hatch, lights, fit):
    payload={
        "asphalt": asphalt, "paint_decals": paint, "hatch": hatch,
        "lights_scanned_preserved": lights,
        "character_fit_scan": fit,
        "feedback_notes":{
            "imported_asphalt":"Imported Asphalt ground is now the active visible surface and was flattened instead of hidden.",
            "paint_strips":"Old raised strip meshes are hidden; flat zero-thickness decal planes replace them.",
            "reflection_lighting":"Future reflection package should use red, white, amber, and green spotlights only, not blue.",
            "fit_plan":"Next body/clothing work should refine Sackboy proportions first, then deform clothing, then rig."
        },
        "locked":{"existing_lights":"scanned only, not modified","car":"not modified","storefront":"not modified","sky_world_hdri":"not modified","character":"scan only"}
    }
    (REP/"parking_texture_decal_fit_prep_v1.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    lines=["# Parking Texture Decal / Fit Prep v1","",
           "## Parking Surface",
           f"- Active visible asphalt: **{asphalt.get('active_asphalt')}**",
           f"- Asphalt flattened at z: **{asphalt.get('plane_z')}**",
           f"- ENV_Asphalt hidden to avoid z-fighting: **{asphalt.get('env_asphalt_hidden')}**",
           "",
           "## Paint Decals",
           f"- Old physical paint-strip meshes hidden: **{paint.get('old_paint_hidden')}**",
           f"- Flat decal planes created: **{paint.get('flat_decals_created')}**",
           f"- Decal z: **{paint.get('decal_z')}**",
           "",
           "## Hatch / Manhole",
           f"- Hatch/manhole objects adjusted: **{len(hatch)}**",
           "",
           "## Character / Clothing Fit Scan"]
    for r in fit["key_objects"]:
        lines.append(f"- **{r.get('name')}** | {r.get('status')} | dims={r.get('dimensions')} | faces={r.get('faces')} | modifiers={r.get('modifiers')}")
    lines += ["","## Current Light Scan"]
    for l in lights:
        lines.append(f"- **{l['name']}** | type={l['type']} | loc={l['location']} | energy={l['energy']} | color={l['color']} | spot_size={l.get('spot_size')} | spot_blend={l.get('spot_blend')}")
    lines += ["","## Direction Locked In",
              "- For window reflections, use **red / white / amber / green** off-scene spotlights only. No blue.",
              "- Do not force clothing onto Sackboy yet. Refine body/head/torso proportions first, then deform hoodie/pants/shoes to fit, then rig.",
              "- Existing amber lights, car, storefront, and sky/HDRI were not changed."]
    (REP/"Parking_Texture_Decal_Fit_Prep_v1.md").write_text("\n".join(lines),encoding="utf-8")
    (OUT/"ParkingTextureDecalFitPrep_status.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")

def manifest():
    data={"blend_file":bpy.data.filepath,"objects":[],"collections":[]}
    for col in sorted(bpy.data.collections,key=lambda c:c.name):
        data["collections"].append({"name":col.name,"hide_viewport":bool(col.hide_viewport),"hide_render":bool(col.hide_render),"object_count":len(col.objects),"child_count":len(col.children)})
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
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
    (ROOT/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Parking Texture Decal / Fit Prep v1.\n\n- Imported Asphalt ground is visible and flattened.\n- ENV_Asphalt is hidden to avoid z-fighting.\n- Old raised paint-strip meshes are hidden and replaced with flat decal planes.\n- Hatch/manhole was placed back on the asphalt surface.\n- Current lighting was scanned and preserved.\n- Character/clothing fit measurements were recorded; no body or clothing deformation was applied.\n",encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"parking_texture_decal_fit_prep_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)},indent=2),encoding="utf-8")

def look_at(cam, target):
    direction=target-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()

def temp_cam(name, loc, aim, lens):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    cam.location=loc; cam.data.lens=lens
    look_at(cam,aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def render_review(active):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    ab=bounds(active) if active else {"min_x":-18,"max_x":18,"min_y":-18,"max_y":18,"min_z":0,"max_z":0,"dim_x":36,"dim_y":36}
    c=center(ab)
    hero=bpy.data.objects.get("F2")
    hb=bounds(hero) if hero else ab
    hc=center(hb)
    cams=[
        temp_cam("TMP_DecalPaintLowAngle", Vector((c.x+7.0,c.y-10.5,ab["max_z"]+2.2)), Vector((c.x,c.y,ab["max_z"]+0.02)), 50),
        temp_cam("TMP_DecalPaintTopCheck", Vector((c.x,c.y,ab["max_z"]+14.0)), Vector((c.x,c.y,ab["max_z"]+0.02)), 45),
        temp_cam("TMP_FitPrepScan", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.6)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old=scene.camera
    for cam,fn in [(cams[0],"01_PaintDecalLowAngle.png"),(cams[1],"02_PaintDecalTopCheck.png"),(cams[2],"03_CharacterFitPrepScan.png")]:
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
    active, surface_z, asphalt_info = show_active_asphalt_flatten_hide_env()
    paint_info = rebuild_paint_decals(surface_z)
    hatch_info = repair_hatch(surface_z)
    lights = scan_lights()
    fit = character_fit_scan()
    write_reports(asphalt_info, paint_info, hatch_info, lights, fit)
    manifest()
    render_review(active)
    out=ROOT/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] "+str(out))

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"ParkingTextureDecalFitPrep_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
