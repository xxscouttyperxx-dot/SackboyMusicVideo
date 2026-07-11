import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "scene_cleanup_flat_asphalt_v1B"
REP = ROOT / "reports" / "scene_cleanup_flat_asphalt_v1B"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "SceneCleanupFlatAsphalt_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "SceneCleanupFlatAsphalt_report.txt").write_text("", encoding="utf-8")

def vis(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bnd(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    return {"min_x":min(xs),"max_x":max(xs),"min_y":min(ys),"max_y":max(ys),"min_z":min(zs),"max_z":max(zs),
            "dim_x":max(xs)-min(xs),"dim_y":max(ys)-min(ys),"dim_z":max(zs)-min(zs)}

def cen(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5,(b["min_y"]+b["max_y"])*0.5,(b["min_z"]+b["max_z"])*0.5))

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

def link(obj, col):
    try:
        if obj.name not in col.objects:
            col.objects.link(obj)
    except Exception:
        pass

def backup(obj, label):
    if not obj or obj.type != "MESH":
        return None
    col = ensure_col("SCENE_CLEANUP_BACKUPS_HIDDEN", True)
    safe = obj.name.replace(" ","_").replace("(","").replace(")","").replace(".","_")
    name = "SCENE_BACKUP_%s_%s" % (label, safe)
    old = bpy.data.objects.get(name)
    if old:
        return old
    mesh = obj.data.copy()
    mesh.name = name + "_Mesh"
    dup = bpy.data.objects.new(name, mesh)
    dup.matrix_world = obj.matrix_world.copy()
    dup.hide_viewport = True
    dup.hide_render = True
    dup["backup_for"] = obj.name
    dup["backup_reason"] = label
    link(dup, col)
    return dup

def safe_transfer_materials(src, dst):
    if not src or not dst or src.type != "MESH" or dst.type != "MESH":
        return False
    mats = [slot.material for slot in src.material_slots if slot.material]
    if not mats:
        return False
    # Do not clear material slots. Just ensure the flat asphalt has at least the source materials.
    existing = {slot.material.name for slot in dst.material_slots if slot.material}
    for mat in mats:
        if mat.name not in existing:
            dst.data.materials.append(mat)
            existing.add(mat.name)
    return True

def flatten_world_z(obj, z):
    if not obj or obj.type != "MESH":
        return
    inv = obj.matrix_world.inverted()
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        w.z = z
        v.co = inv @ w
    obj.data.update()

def find_asphalt():
    env = bpy.data.objects.get("ENV_Asphalt")
    imp = bpy.data.objects.get("Asphalt ground")
    if not env:
        mesh = bpy.data.meshes.new("ENV_Asphalt_Mesh")
        size = 36.0
        mesh.from_pydata([(-size/2,-size/2,0),(size/2,-size/2,0),(size/2,size/2,0),(-size/2,size/2,0)], [], [(0,1,2,3)])
        mesh.update()
        env = bpy.data.objects.new("ENV_Asphalt", mesh)
        bpy.context.scene.collection.objects.link(env)
        log("[asphalt] created ENV_Asphalt")
    return env, imp

def paint_objs():
    out=[]; seen=set()
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        text = (obj.name + " " + " ".join(c.name for c in obj.users_collection)).lower()
        if any(bad in text for bad in ["asphalt","ground","lamp","sign","sidewalk","curb","storefront","camera"]):
            continue
        if any(k in text for k in ["hparking","stripe","strip","paint","line","divider","spine","parking"]):
            if obj.name not in seen:
                seen.add(obj.name)
                out.append(obj)
    return out

def prep_asphalt():
    env, imp = find_asphalt()
    changes = {}
    backup(env, "before_flatten")

    if imp and imp != env:
        backup(imp, "hidden_imported_asphalt")
        changes["material_transferred_from_imported_asphalt"] = safe_transfer_materials(imp, env)
        imp.hide_viewport = True
        imp.hide_render = True
        changes["imported_asphalt_hidden"] = imp.name
        log("[asphalt] hid bumpy imported Asphalt ground")

    eb = bnd(env)
    z = eb["max_z"] if eb else 0.0
    flatten_world_z(env, z)
    env["scene_cleanup_flattened"] = True
    env["scene_cleanup_flatten_plane_z"] = float(z)

    # Remove old snap modifier from ENV_Asphalt if it accidentally got one.
    if env.modifiers.get("PARKING_TO_ASPHALT_PREVIEW"):
        env.modifiers.remove(env.modifiers["PARKING_TO_ASPHALT_PREVIEW"])

    if not env.modifiers.get("FLAT_ASPHALT_VISUAL_THICKNESS"):
        try:
            mod = env.modifiers.new("FLAT_ASPHALT_VISUAL_THICKNESS", "SOLIDIFY")
            mod.thickness = 0.04
            mod.offset = -1.0
            mod.show_viewport = True
            mod.show_render = True
        except Exception:
            pass

    adjusted = []
    offset = 0.004
    for obj in paint_objs():
        for m in list(obj.modifiers):
            if m.name == "PARKING_TO_ASPHALT_PREVIEW":
                obj.modifiers.remove(m)
        ob = bnd(obj)
        if not ob:
            continue
        oldz = obj.location.z
        obj.location.z += (z + offset - ob["min_z"])
        nb = bnd(obj)
        obj["scene_cleanup_paint_snapped_to"] = env.name
        obj["scene_cleanup_paint_offset"] = offset
        adjusted.append({"name": obj.name, "old_location_z": round(oldz,6), "new_location_z": round(obj.location.z,6), "new_min_z": None if not nb else round(nb["min_z"],6)})

    changes["flat_asphalt_target"] = env.name
    changes["flat_plane_z"] = z
    changes["paint_objects_adjusted"] = len(adjusted)
    changes["paint_objects"] = adjusted
    log("[paint] flattened %s at z=%.6f and adjusted %d paint objects" % (env.name, z, len(adjusted)))
    return changes

def cleanup_cams():
    removed = []
    for cname in ["HERO_REVIEW_CAMERAS_MESH_AUDIT","HERO_REVIEW_CAMERAS"]:
        col = bpy.data.collections.get(cname)
        if not col:
            continue
        for obj in list(col.objects):
            if obj.type == "CAMERA":
                removed.append(obj.name)
                bpy.data.objects.remove(obj, do_unlink=True)
        if len(col.objects) == 0 and len(col.children) == 0:
            try:
                bpy.data.collections.remove(col)
            except Exception:
                pass
    log("[cleanup] removed %d temp review cameras" % len(removed))
    return removed

def scan_lights():
    rows=[]
    for o in sorted([x for x in bpy.data.objects if x.type=="LIGHT"], key=lambda x:x.name):
        d=o.data
        rows.append({"name":o.name,"type":d.type,"location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
                     "rotation":[round(v,6) for v in o.rotation_euler],
                     "energy":getattr(d,"energy",None),
                     "color":[round(v,6) for v in getattr(d,"color",[])] if hasattr(d,"color") else None,
                     "size":getattr(d,"size",None),
                     "spot_size":getattr(d,"spot_size",None) if d.type=="SPOT" else None,
                     "spot_blend":getattr(d,"spot_blend",None) if d.type=="SPOT" else None})
    return rows

def scan_decimate():
    rows=[]
    for name in ["Apricot Pullover Hoodie","Utility Box (Photoscanned)","Lid.001"]:
        o=bpy.data.objects.get(name)
        if not o:
            rows.append({"name":name,"status":"missing"})
            continue
        c=counts(o)
        m=o.modifiers.get("OPT_PREVIEW_DECIMATE")
        rows.append({"name":name,"vertices":c["vertices"],"faces":c["faces"],"decimate_modifier_present":bool(m),"ratio":None if not m else m.ratio})
    return rows

def reports(asph, cams, lights, dec):
    payload={"asphalt_and_paint":asph,"removed_temp_review_cameras":cams,"lights_scanned_preserved":lights,"decimate_targets_verified":dec,
             "locked":{"lights":"scanned only, not modified","car":"not modified","storefront":"not modified","sky_world_hdri":"not modified","reflection_lights":"not added"}}
    (REP/"scene_cleanup_flat_asphalt_v1B.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    lines=["# Scene Cleanup / Flat Asphalt v1B","","## Asphalt / Paint",
           f"- Flat asphalt target: **{asph.get('flat_asphalt_target')}**",
           f"- Flat plane z: **{asph.get('flat_plane_z')}**",
           f"- Paint objects adjusted: **{asph.get('paint_objects_adjusted')}**"]
    if asph.get("imported_asphalt_hidden"):
        lines.append(f"- Hidden bumpy imported asphalt: **{asph.get('imported_asphalt_hidden')}**")
    lines += ["","## Decimate Preview Verification"]
    for r in dec:
        lines.append(f"- **{r.get('name')}** | modifier={r.get('decimate_modifier_present')} | ratio={r.get('ratio')} | faces={r.get('faces')}")
    lines += ["","## Current Light Scan"]
    for l in lights:
        lines.append(f"- **{l['name']}** | type={l['type']} | loc={l['location']} | energy={l['energy']} | color={l['color']} | spot_size={l.get('spot_size')} | spot_blend={l.get('spot_blend')}")
    lines += ["","## Reflection Lighting Plan",
              "- Colored off-scene spotlights for glass reflections are a good idea, but this pass does not add them.",
              "- That should be a separate package so your newly tuned amber lighting remains preserved.",
              "",
              "## Locked Items",
              "- Existing lights were scanned only and not changed.",
              "- Car, storefront, sky/world/HDRI, and character hands were not changed."]
    (REP/"Scene_Cleanup_Flat_Asphalt_v1B.md").write_text("\n".join(lines),encoding="utf-8")
    (OUT/"SceneCleanupFlatAsphalt_status.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")

def manifest():
    data={"blend_file":bpy.data.filepath,"objects":[],"collections":[]}
    for col in sorted(bpy.data.collections,key=lambda c:c.name):
        data["collections"].append({"name":col.name,"hide_viewport":bool(col.hide_viewport),"hide_render":bool(col.hide_render),"object_count":len(col.objects),"child_count":len(col.children)})
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        bb=bnd(o)
        e={"name":o.name,"type":o.type,"collections":[c.name for c in o.users_collection],"visible":vis(o),
           "location":[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],
           "rotation":[round(v,6) for v in o.rotation_euler],
           "scale":[round(o.scale.x,6),round(o.scale.y,6),round(o.scale.z,6)],
           "dimensions":None if not bb else [round(bb["dim_x"],6),round(bb["dim_y"],6),round(bb["dim_z"],6)],
           "modifiers":[{"name":m.name,"type":m.type} for m in o.modifiers]}
        if o.type=="MESH":
            e.update(counts(o))
        if o.type=="LIGHT":
            e["energy"]=getattr(o.data,"energy",None)
            e["color"]=[round(v,6) for v in getattr(o.data,"color",[])] if hasattr(o.data,"color") else None
        data["objects"].append(e)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Scene Cleanup / Flat Asphalt v1B.\n\n- Existing manually tuned lights were scanned and preserved.\n- Active parking asphalt was flattened for paint placement.\n- Bumpy duplicate imported asphalt was hidden after material transfer where available.\n- Temporary review cameras were cleaned.\n- Decimate preview modifiers were verified.\n",encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"scene_cleanup_flat_asphalt_v1B","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)},indent=2),encoding="utf-8")

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
    env=bpy.data.objects.get("ENV_Asphalt")
    eb=bnd(env) if env else {"min_x":-18,"max_x":18,"min_y":-18,"max_y":18,"min_z":0,"max_z":0,"dim_x":36,"dim_y":36,"dim_z":0.1}
    c=cen(eb)
    hero=bpy.data.objects.get("F2")
    hb=bnd(hero) if hero else eb
    hc=cen(hb)
    cams=[
        temp_cam("TMP_FlatPaintCheck_v1B", Vector((c.x+eb["dim_x"]*0.18,c.y-eb["dim_y"]*0.32,eb["max_z"]+9.0)), Vector((c.x,c.y,eb["max_z"]+0.02)), 42),
        temp_cam("TMP_DecimatePreviewCheck_v1B", Vector((hc.x+2.5,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.4)), 55)
    ]
    old=scene.camera
    for cam,fn in [(cams[0],"01_FlatAsphaltPaintCheck.png"),(cams[1],"02_DecimatePreviewCheck.png")]:
        scene.camera=cam
        scene.render.filepath=str(OUT/fn)
        bpy.ops.render.render(write_still=True)
        log("[render] "+fn)
    if old:
        scene.camera=old
        scene.render.filepath=str(OUT/"03_CurrentSceneCamera.png")
        bpy.ops.render.render(write_still=True)
        log("[render] 03_CurrentSceneCamera.png")
    scene.camera=old
    for cam in cams:
        bpy.data.objects.remove(cam, do_unlink=True)
    CUR.mkdir(parents=True,exist_ok=True)
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR/p.name).write_bytes(p.read_bytes())

def main():
    reset()
    log("[lock] scanning current light changes; not modifying lights")
    removed = cleanup_cams()
    asph = prep_asphalt()
    lights = scan_lights()
    dec = scan_decimate()
    reports(asph, removed, lights, dec)
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
        with (OUT / "SceneCleanupFlatAsphalt_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
