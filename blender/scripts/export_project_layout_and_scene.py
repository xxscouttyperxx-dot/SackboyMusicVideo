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
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return {"xmin":min(xs),"xmax":max(xs),"ymin":min(ys),"ymax":max(ys),"zmin":min(zs),"zmax":max(zs)}
    except Exception:
        return None

def dims_from_bounds(bounds):
    if not bounds:
        return None
    return {"x":bounds["xmax"]-bounds["xmin"],"y":bounds["ymax"]-bounds["ymin"],"z":bounds["zmax"]-bounds["zmin"]}

def scene_manifest():
    scene=bpy.context.scene
    objects=[]
    for obj in bpy.data.objects:
        b=world_bounds(obj)
        row={
            "name":obj.name,
            "type":obj.type,
            "collections":[c.name for c in obj.users_collection],
            "hide_viewport":obj.hide_viewport,
            "hide_render":obj.hide_render,
            "visible_get":obj.visible_get() if hasattr(obj,"visible_get") else None,
            "parent":obj.parent.name if obj.parent else None,
            "location":[round(v,6) for v in obj.location],
            "rotation_euler":[round(v,6) for v in obj.rotation_euler],
            "scale":[round(v,6) for v in obj.scale],
            "dimensions":[round(v,6) for v in obj.dimensions],
            "world_bounds":b,
            "world_dimensions":dims_from_bounds(b),
            "modifiers":[{"name":m.name,"type":m.type} for m in obj.modifiers],
            "materials":[m.name if m else None for m in getattr(obj.data,"materials",[])] if hasattr(obj,"data") else [],
        }
        if obj.type=="LIGHT":
            row["light"]={"type":obj.data.type,"energy":getattr(obj.data,"energy",None),"color":list(getattr(obj.data,"color",[])),"size":getattr(obj.data,"size",None)}
        if obj.type=="CAMERA":
            row["camera"]={"lens":obj.data.lens,"clip_start":obj.data.clip_start,"clip_end":obj.data.clip_end}
        if obj.type=="ARMATURE":
            row["bones"]=[{"name":b.name,"parent":b.parent.name if b.parent else None,"head_local":list(b.head_local),"tail_local":list(b.tail_local)} for b in obj.data.bones]
        objects.append(row)
    collections=[]
    for col in bpy.data.collections:
        collections.append({"name":col.name,"hide_viewport":col.hide_viewport,"hide_render":col.hide_render,"objects":[o.name for o in col.objects],"children":[c.name for c in col.children]})
    return {
        "blend_file":bpy.data.filepath,
        "collections":collections,
        "objects":objects,
        "render_settings":{"engine":scene.render.engine,"resolution_x":scene.render.resolution_x,"resolution_y":scene.render.resolution_y,"resolution_percentage":scene.render.resolution_percentage,"fps":scene.render.fps,"frame_start":scene.frame_start,"frame_end":scene.frame_end,"frame_current":scene.frame_current,"world":scene.world.name if scene.world else None},
    }

def markdown_summary(data):
    lines=["# Scene Layout Summary\n\n",f"Blend: `{data['blend_file']}`\n\n","## Collections\n\n"]
    for col in sorted(data["collections"], key=lambda c:c["name"].lower()):
        lines.append(f"- **{col['name']}** | hidden viewport={col['hide_viewport']} render={col['hide_render']} | objects={len(col['objects'])} | children={len(col['children'])}\n")
    lines.append("\n## Key Objects\n\n")
    important_terms=["F2","HANDREFINE","car","audi","sky","hdri","light","camera","store","mall","lamp","parking","underglow"]
    for obj in sorted(data["objects"], key=lambda o:o["name"].lower()):
        name_low=obj["name"].lower()
        if any(term.lower() in name_low for term in important_terms) or obj["type"] in {"LIGHT","CAMERA","ARMATURE"}:
            lines.append(f"- **{obj['name']}** ({obj['type']}) collections={obj['collections']} visible={obj['visible_get']} dims={obj.get('world_dimensions')} loc={obj['location']}\n")
    return "".join(lines)

def file_tree(root):
    ignore_dirs={"Backups","Archive","__pycache__",".git",".venv"}
    include_roots=["blender","NightSkyHDRI003_1K","renders/current_review","reports"]
    rows=[]
    for rel_root in include_roots:
        base=root/rel_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if any(part in ignore_dirs for part in path.parts):
                continue
            if path.is_file():
                rows.append({"path":str(path.relative_to(root)),"size_bytes":path.stat().st_size})
    return rows

def main():
    root=project_root()
    out_dir=root/"reports"/"project_workflow_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    data=scene_manifest()
    (root/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (out_dir/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (out_dir/"scene_layout_summary.md").write_text(markdown_summary(data),encoding="utf-8")
    files=file_tree(root)
    (out_dir/"project_file_layout.json").write_text(json.dumps(files,indent=2),encoding="utf-8")
    print(f"[audit] wrote {root/'scene_manifest.json'}")
    print(f"[audit] wrote {out_dir/'scene_layout_summary.md'}")
    print(f"[audit] wrote {out_dir/'project_file_layout.json'}")

if __name__ == "__main__":
    main()
