from pathlib import Path
import json
import bpy
from mathutils import Vector
try:
    from common import project_root
except Exception:
    def project_root():
        return Path(__file__).resolve().parents[2]

def world_bounds(obj):
    if obj.type not in {"MESH","CURVE","FONT","META","SURFACE"} or not hasattr(obj,"bound_box"):
        return None
    try:
        coords=[obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return {"xmin":min(xs),"xmax":max(xs),"ymin":min(ys),"ymax":max(ys),"zmin":min(zs),"zmax":max(zs)}
    except Exception:
        return None

def dims_from_bounds(b):
    return None if not b else {"x":b["xmax"]-b["xmin"],"y":b["ymax"]-b["ymin"],"z":b["zmax"]-b["zmin"]}

def material_names(obj):
    return [] if not hasattr(obj.data,"materials") else [m.name if m else None for m in obj.data.materials]

def modifier_info(obj):
    return [{"name":m.name,"type":m.type} for m in obj.modifiers]

def collection_info():
    return [{"name":c.name,"hide_viewport":c.hide_viewport,"hide_render":c.hide_render,"objects":[o.name for o in c.objects],"children":[ch.name for ch in c.children]} for c in bpy.data.collections]

def object_info():
    out=[]
    for obj in bpy.data.objects:
        b=world_bounds(obj)
        row={"name":obj.name,"type":obj.type,"collections":[c.name for c in obj.users_collection],"hide_viewport":obj.hide_viewport,"hide_render":obj.hide_render,"parent":obj.parent.name if obj.parent else None,"location":list(obj.location),"rotation_euler":list(obj.rotation_euler),"scale":list(obj.scale),"dimensions":list(obj.dimensions),"world_bounds":b,"world_dimensions":dims_from_bounds(b),"modifiers":modifier_info(obj),"materials":material_names(obj)}
        try: row["visible_get"]=obj.visible_get()
        except Exception: row["visible_get"]=None
        if obj.type=="LIGHT":
            row["light"]={"type":obj.data.type,"energy":getattr(obj.data,"energy",None),"color":list(getattr(obj.data,"color",[])),"size":getattr(obj.data,"size",None),"shape":getattr(obj.data,"shape",None)}
        if obj.type=="CAMERA":
            row["camera"]={"lens":obj.data.lens,"sensor_width":obj.data.sensor_width,"clip_start":obj.data.clip_start,"clip_end":obj.data.clip_end}
        if obj.type=="ARMATURE":
            row["bones"]=[{"name":b.name,"parent":b.parent.name if b.parent else None,"head_local":list(b.head_local),"tail_local":list(b.tail_local)} for b in obj.data.bones]
        out.append(row)
    return out

def render_settings():
    s=bpy.context.scene
    return {"engine":s.render.engine,"resolution_x":s.render.resolution_x,"resolution_y":s.render.resolution_y,"resolution_percentage":s.render.resolution_percentage,"fps":s.render.fps,"frame_start":s.frame_start,"frame_end":s.frame_end,"frame_current":s.frame_current,"world":s.world.name if s.world else None}

def export_scene_manifest(out_path=None):
    out_path=Path(out_path) if out_path else project_root()/"scene_manifest.json"
    data={"manifest_version":1,"blend_file":bpy.data.filepath,"collections":collection_info(),"objects":object_info(),"render_settings":render_settings()}
    out_path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(f"[manifest] wrote {out_path}")
    return out_path
if __name__=='__main__':
    export_scene_manifest()
