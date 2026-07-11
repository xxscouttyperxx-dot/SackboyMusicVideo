import sys, json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root

OUT_DIR = project_root() / "renders" / "baseline_capture_scan_v1"
REPORT_DIR = project_root() / "reports" / "baseline_capture_scan_v1"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "BaselineCaptureScan_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "BaselineCaptureScan_report.txt").write_text("", encoding="utf-8")

def world_bounds(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return {"dim_x": max(xs)-min(xs), "dim_y": max(ys)-min(ys), "dim_z": max(zs)-min(zs),
                "min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys), "min_z": min(zs), "max_z": max(zs)}
    except Exception:
        return None

def visible(obj):
    return (not obj.hide_viewport) and (not obj.hide_render)

def collect_scene_summary():
    collections = []
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        collections.append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render), "object_count": len(col.objects), "child_count": len(col.children)})

    clothing = []
    lights = []
    suspect = []
    key = []
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        colnames=[c.name for c in obj.users_collection]
        row={"name": obj.name, "type": obj.type, "collections": colnames, "visible": visible(obj),
             "location": [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)], "bounds": world_bounds(obj)}
        n=obj.name
        if n.startswith("HERO_") or n.startswith("F2") or n.startswith("HANDREFINE") or n.startswith("Audi e-tron GT quattro Black") or n.startswith("V2B_OverheadAmber"):
            key.append(row)
        if any("CLOTHING" in c.upper() or "WARDROBE" in c.upper() or "IMPORTED" in c.upper() for c in colnames) or any(tok in n for tok in ["Clothing","Hoodie","Jeans","Shoe","Sneaker","Jacket","Pants"]):
            clothing.append(row)
        if obj.type == "LIGHT":
            data=obj.data
            row["light_type"]=data.type
            row["energy"]=getattr(data,"energy",None)
            row["color"]=list(getattr(data,"color",[])) if hasattr(data,"color") else None
            row["spot_size"]=getattr(data,"spot_size",None) if data.type=="SPOT" else None
            row["spot_blend"]=getattr(data,"spot_blend",None) if data.type=="SPOT" else None
            row["size"]=getattr(data,"size",None)
            lights.append(row)
        if any(tok in n for tok in ["Traffic","ReflectionCard","MaterialSwatch","FlameAccent","YellowSweep","OrangeSweep"]):
            suspect.append(row)
    return {"blend_file": bpy.data.filepath, "collections": collections, "key_objects": key, "clothing_related_objects": clothing, "lights": lights, "suspect_leftover_objects": suspect}

def write_markdown(summary):
    lines=[]
    lines.append("# Baseline Capture / Scan v1")
    lines.append("")
    lines.append("Read-only capture of the current manual baseline. This script does not modify lights, clothing, car, storefront, sky, materials, or geometry.")
    lines.append("")
    lines.append("## Collections")
    for col in summary["collections"]:
        lines.append(f"- **{col['name']}** | hidden viewport={col['hide_viewport']} render={col['hide_render']} | objects={col['object_count']} | children={col['child_count']}")
    lines.append("")
    lines.append("## Lights Locked Baseline")
    for light in summary["lights"]:
        lines.append(f"- **{light['name']}** | type={light.get('light_type')} | loc={light['location']} | energy={light.get('energy')} | color={light.get('color')} | spot_size={light.get('spot_size')} | spot_blend={light.get('spot_blend')} | collections={light['collections']}")
    lines.append("")
    lines.append("## Clothing / Imported Candidate Objects")
    for item in summary["clothing_related_objects"]:
        b=item.get("bounds")
        d=None if not b else {"x":round(b["dim_x"],4),"y":round(b["dim_y"],4),"z":round(b["dim_z"],4)}
        lines.append(f"- **{item['name']}** ({item['type']}) | visible={item['visible']} | collections={item['collections']} | loc={item['location']} | dims={d}")
    lines.append("")
    lines.append("## Suspect Leftover Objects")
    if summary["suspect_leftover_objects"]:
        for obj in summary["suspect_leftover_objects"]:
            lines.append(f"- **{obj['name']}** ({obj['type']}) | visible={obj['visible']} | collections={obj['collections']}")
    else:
        lines.append("- None found by name scan.")
    lines.append("")
    lines.append("## Red Specks Notes")
    lines.append("- Red specks around sharp edges in Rendered mode are commonly caused by z-fighting/overlapping surfaces, transparent guide meshes intersecting character/clothing, emissive/glossy highlights clipping at edges, or material/normal artifacts.")
    lines.append("- In this scene, the likely causes are overlapping guide/asset geometry, glossy/emissive edge highlights, or imported model normals/materials. This package only records the baseline; it does not change the scene.")
    (REPORT_DIR / "Baseline_Capture_Scan_v1.md").write_text("\n".join(lines), encoding="utf-8")

def export_manifest():
    script=project_root()/"blender"/"scripts"/"export_project_layout_and_scene.py"
    if script.exists():
        ns={"__file__":str(script),"__name__":"__main__"}
        exec(script.read_text(encoding="utf-8"), ns)

def render_existing_cameras():
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    cams=sorted([o for o in bpy.data.objects if o.type=="CAMERA" and o.name.startswith("HERO_CAM_")], key=lambda o:o.name)[:3]
    if not cams:
        cams=sorted([o for o in bpy.data.objects if o.type=="CAMERA"], key=lambda o:o.name)[:3]
    for idx,cam in enumerate(cams, start=1):
        scene.camera=cam
        safe="".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in cam.name)
        fn=f"{idx:02d}_{safe}.png"
        scene.render.filepath=str(OUT_DIR/fn)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {fn}")
    current=project_root()/"renders"/"current_review"
    current.mkdir(parents=True,exist_ok=True)
    for p in current.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (current/p.name).write_bytes(p.read_bytes())

def main():
    reset_log()
    log("[baseline] read-only scan started; no scene objects will be modified")
    summary=collect_scene_summary()
    (REPORT_DIR/"baseline_capture_scan_v1.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    write_markdown(summary)
    render_existing_cameras()
    export_manifest()
    log("[baseline] scan complete; blend intentionally not saved")

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with (OUT_DIR/"BaselineCaptureScan_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
