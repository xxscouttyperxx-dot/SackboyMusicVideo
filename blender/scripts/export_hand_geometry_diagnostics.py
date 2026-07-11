import sys
import json
import csv
from pathlib import Path

import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_NAME = "HANDREFINE_J2_Working"
OUT_DIR_NAME = "hand_refine_j2a_geometry"
CAM_COLLECTION = "DIAG_HandJ2A_Cameras"
LIGHT_COLLECTION = "DIAG_HandJ2A_Lights"

def world_bounds(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def extract_region(obj):
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(obj)
    w=xmax-xmin
    cutoff = xmin + w*0.40

    mw = obj.matrix_world
    verts_world = [mw @ v.co for v in obj.data.vertices]

    selected_old = [i for i,co in enumerate(verts_world) if co.x <= cutoff]
    selected_set = set(selected_old)

    remap = {}
    region_verts = []
    for old_i in selected_old:
        remap[old_i] = len(region_verts)
        region_verts.append(verts_world[old_i])

    region_faces = []
    for poly in obj.data.polygons:
        ids = list(poly.vertices)
        if all(i in selected_set for i in ids):
            region_faces.append([remap[i] for i in ids])

    return {
        "bbox_full": (xmin,xmax,ymin,ymax,zmin,zmax),
        "cutoff_x": cutoff,
        "vertices": region_verts,
        "faces": region_faces,
    }

def write_obj(region, out_path):
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Step01M-J2A left arm/hand region export\n")
        for v in region["vertices"]:
            f.write(f"v {v.x:.9f} {v.y:.9f} {v.z:.9f}\n")
        for face in region["faces"]:
            f.write("f " + " ".join(str(i+1) for i in face) + "\n")
    print(f"[Step01M-J2A] Wrote OBJ: {out_path}")

def percentile(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    idx = (len(vals)-1)*p
    lo = int(idx)
    hi = min(lo+1, len(vals)-1)
    t = idx-lo
    return vals[lo]*(1-t) + vals[hi]*t

def write_metrics(region, out_dir):
    verts = region["vertices"]
    xs=[v.x for v in verts]; ys=[v.y for v in verts]; zs=[v.z for v in verts]

    metrics = {
        "region_vertex_count": len(verts),
        "region_face_count": len(region["faces"]),
        "cutoff_x": region["cutoff_x"],
        "bbox": {
            "xmin": min(xs), "xmax": max(xs),
            "ymin": min(ys), "ymax": max(ys),
            "zmin": min(zs), "zmax": max(zs),
        },
        "dimensions": {
            "x": max(xs)-min(xs),
            "y": max(ys)-min(ys),
            "z": max(zs)-min(zs),
        },
        "percentiles": {
            "x": {str(int(p*100)): percentile(xs,p) for p in (0,.1,.25,.5,.75,.9,1)},
            "y": {str(int(p*100)): percentile(ys,p) for p in (0,.1,.25,.5,.75,.9,1)},
            "z": {str(int(p*100)): percentile(zs,p) for p in (0,.1,.25,.5,.75,.9,1)},
        },
    }
    (out_dir/"LeftArmHand_geometry_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    # Cross-sectional bins along X.
    bins = 18
    xmin=min(xs); xmax=max(xs)
    width=(xmax-xmin)/bins if xmax>xmin else 1.0
    rows=[]
    for b in range(bins):
        x0=xmin+b*width
        x1=xmin+(b+1)*width if b<bins-1 else xmax+1e-9
        pts=[v for v in verts if x0 <= v.x < x1]
        if not pts:
            continue
        py=[v.y for v in pts]; pz=[v.z for v in pts]
        rows.append({
            "bin": b,
            "x0": x0,
            "x1": x1,
            "count": len(pts),
            "y_span": max(py)-min(py),
            "z_span": max(pz)-min(pz),
            "y_center": (max(py)+min(py))/2,
            "z_center": (max(pz)+min(pz))/2,
        })
    with (out_dir/"LeftArmHand_cross_sections.csv").open("w", newline="", encoding="utf-8") as f:
        writer=csv.DictWriter(f, fieldnames=rows[0].keys() if rows else ["bin"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[Step01M-J2A] Wrote geometry metrics and cross-sections.")

def setup_neutral_scene(target):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.image_settings.file_format='PNG'
    scene.render.resolution_percentage=100
    scene.world.color=(0.025,0.025,0.03)

    states={}
    for obj in bpy.context.scene.objects:
        states[obj.name]=obj.hide_render
        if obj.type=='MESH':
            obj.hide_render=(obj != target)
    target.hide_render=False

    light_col=replace_collection(LIGHT_COLLECTION)
    cam_col=replace_collection(CAM_COLLECTION)

    def area(name,loc,energy,size):
        data=bpy.data.lights.new(name+"_Data", type='AREA')
        data.energy=energy
        data.shape='DISK'
        data.size=size
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        light_col.objects.link(obj)
        return obj

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    key=area("J2A_Key",(-4,-5,4),800,3)
    fill=area("J2A_Fill",(3,-2,2),180,4)
    rim=area("J2A_Rim",(0,4,4),280,3)
    for l in (key,fill,rim):
        look_at(l,center)

    return cam_col, states

def restore_states(states):
    for name,state in states.items():
        obj=bpy.data.objects.get(name)
        if obj:
            obj.hide_render=state

def render_views(target, out_dir):
    cam_col,states=setup_neutral_scene(target)
    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    w=xmax-xmin; h=zmax-zmin
    d=max(5.0,h*2.0)

    hand_focus=Vector((xmin+w*.11, ymin+(ymax-ymin)*.30, zmin+h*.57))
    arm_focus=Vector((xmin+w*.23, ymin+(ymax-ymin)*.26, zmin+h*.60))

    views=[
        ("J2A_Hand_Frontish",(xmin-w*.14,ymin-d*.18,zmin+h*.58),hand_focus,78,"J2A_Hand_Frontish.png"),
        ("J2A_Hand_Sideish",(xmin-w*.02,(ymin+ymax)/2-d*.02,zmin+h*.58),hand_focus,72,"J2A_Hand_Sideish.png"),
        ("J2A_Arm_ThreeQuarter",(xmin+w*.18,ymin-d*.40,zmin+h*.72),arm_focus,68,"J2A_Arm_ThreeQuarter.png"),
    ]

    scene=bpy.context.scene
    for name,loc,aim,lens,fn in views:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.data.lens=lens
        cam.location=loc
        look_at(cam,aim)
        cam_col.objects.link(cam)
        scene.camera=cam
        scene.render.resolution_x=1280
        scene.render.resolution_y=1280
        scene.render.filepath=str(out_dir/fn)
        bpy.ops.render.render(write_still=True)
        print(f"[Step01M-J2A] Rendered {out_dir/fn}")

    restore_states(states)

def main():
    obj=bpy.data.objects.get(SOURCE_NAME)
    if not obj or obj.type!='MESH':
        raise RuntimeError("HANDREFINE_J2_Working not found. Run J2 first.")

    out_dir=project_root()/"renders"/OUT_DIR_NAME
    out_dir.mkdir(parents=True,exist_ok=True)

    region=extract_region(obj)
    write_obj(region,out_dir/"LeftArmHand_AnalysisRegion.obj")
    write_metrics(region,out_dir)
    render_views(obj,out_dir)

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J2A] Saved diagnostic cameras only: {out}")

if __name__=="__main__":
    main()
