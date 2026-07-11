import sys
from pathlib import Path
import math
import bpy
import bmesh
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_NAME = "HANDREFINE_J2_Working"
OUT_NAME = "HANDREFINE_J2B_Working"
OUT_COLLECTION = "CHAR_HandRefine_J2B"
CAM_COLLECTION = "DIAG_HandRefine_J2B_Cameras"

# Measurements taken from J2A exported cross sections.
X_TIP_END = -1.47
X_FINGER_END = -1.30
X_PALM_END = -1.06
X_WRIST_END = -0.88
Y_CENTER = 0.085
Z_CENTER = 1.445

def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def world_bounds(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def smoothstep(a,b,x):
    if a == b:
        return 0.0
    t=max(0.0,min(1.0,(x-a)/(b-a)))
    return t*t*(3-2*t)

def pick_source():
    obj=bpy.data.objects.get(SOURCE_NAME)
    if not obj or obj.type!='MESH':
        raise RuntimeError("HANDREFINE_J2_Working not found. Run J2 first.")
    return obj

def duplicate_source(source):
    col=replace_collection(OUT_COLLECTION)
    dup=source.copy()
    dup.data=source.data.copy()
    dup.name=OUT_NAME
    col.objects.link(dup)
    source.hide_viewport=True
    source.hide_render=True
    dup.hide_viewport=False
    dup.hide_render=False
    return dup

def gaussian(x, mu, sigma):
    return math.exp(-((x-mu)**2)/(2*sigma*sigma))

def target_half_y(x):
    # Data-driven target width profile from hand tip -> palm -> wrist.
    if x <= X_FINGER_END:
        t=smoothstep(X_TIP_END,X_FINGER_END,x)
        return 0.18 + 0.05*t
    if x <= X_PALM_END:
        t=smoothstep(X_FINGER_END,X_PALM_END,x)
        return 0.23 + 0.03*math.sin(math.pi*t)
    t=smoothstep(X_PALM_END,X_WRIST_END,x)
    return 0.23 - 0.02*t

def target_half_z(x):
    if x <= X_FINGER_END:
        t=smoothstep(X_TIP_END,X_FINGER_END,x)
        return 0.12 + 0.05*t
    if x <= X_PALM_END:
        t=smoothstep(X_FINGER_END,X_PALM_END,x)
        return 0.17 + 0.025*math.sin(math.pi*t)
    t=smoothstep(X_PALM_END,X_WRIST_END,x)
    return 0.18 - 0.015*t

def reshape(obj):
    mesh=obj.data
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    mw=obj.matrix_world
    imw=mw.inverted()

    moved=0
    finger_moved=0
    thumb_reduced=0

    lobe_centers=[1.525,1.455,1.385]
    valley_centers=[1.490,1.420]

    for v in bm.verts:
        world=mw @ v.co
        x,y,z=world.x,world.y,world.z

        if not (X_TIP_END-0.05 <= x <= X_WRIST_END):
            continue
        if not (-0.55 <= y <= 0.65 and 1.10 <= z <= 1.80):
            continue

        region_weight=1.0-smoothstep(X_PALM_END,X_WRIST_END,x)
        if x <= X_PALM_END:
            region_weight=1.0

        # Exact cross-section driven compression.
        hy=target_half_y(x)
        hz=target_half_z(x)
        dy=y-Y_CENTER
        dz=z-Z_CENTER

        # Soft clamp rather than hard scale so local features survive.
        if abs(dy) > hy:
            excess=abs(dy)-hy
            y -= math.copysign(excess*0.72*region_weight,dy)

        if abs(dz) > hz:
            excess=abs(dz)-hz
            z -= math.copysign(excess*0.65*region_weight,dz)

        # Shorten broad forward reach a little more.
        if x < X_FINGER_END:
            t=1.0-smoothstep(X_TIP_END,X_FINGER_END,x)
            x += 0.045*t

        # Sculpt three rounded finger lobes in the tip silhouette.
        if x < X_FINGER_END + 0.035:
            lobes=sum(gaussian(z,c,0.026) for c in lobe_centers)
            valleys=sum(gaussian(z,c,0.020) for c in valley_centers)
            x += (-0.026*lobes + 0.018*valleys)
            finger_moved += 1

        # Reduce the oversized underside/thumb-side droop.
        if X_FINGER_END <= x <= X_PALM_END+0.02 and z < 1.36:
            lift=(1.36-z)*0.38
            z += lift
            thumb_reduced += 1

        world=Vector((x,y,z))
        v.co=imw @ world
        moved += 1

    # One tiny smoothing pass on hand only, no arm smoothing.
    selected=[]
    for v in bm.verts:
        world=mw @ v.co
        if X_TIP_END-0.05 <= world.x <= X_PALM_END+0.01 and 1.10 <= world.z <= 1.80:
            selected.append(v)
    if selected:
        bmesh.ops.smooth_vert(
            bm,
            verts=selected,
            factor=0.08,
            use_axis_x=False,
            use_axis_y=True,
            use_axis_z=True,
        )

    bm.normal_update()
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()

    return {
        "vertices_moved": moved,
        "finger_zone_vertices": finger_moved,
        "underside_vertices_lifted": thumb_reduced,
    }

def look_at(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def render_views(target):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.image_settings.file_format='PNG'
    scene.render.resolution_percentage=100
    scene.world.color=(0.03,0.03,0.035)

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    w=xmax-xmin
    h=zmax-zmin
    d=max(5.0,h*2.0)

    states={}
    for obj in bpy.context.scene.objects:
        states[obj.name]=obj.hide_render
        if obj.type=='MESH':
            obj.hide_render=(obj != target)
    target.hide_render=False

    cam_col=replace_collection(CAM_COLLECTION)

    # Add simple low-key lights.
    light_col=ensure_collection("DIAG_HandRefine_J2B_Lights")
    for obj in list(light_col.objects):
        bpy.data.objects.remove(obj,do_unlink=True)

    def area(name,loc,energy,size,aim):
        data=bpy.data.lights.new(name+"_Data",type='AREA')
        data.energy=energy
        data.shape='DISK'
        data.size=size
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        look_at(obj,aim)
        light_col.objects.link(obj)

    hand_focus=Vector((-1.22,Y_CENTER,Z_CENTER))
    area("J2B_Key",(-2.2,-3.0,2.3),650,2.0,hand_focus)
    area("J2B_Fill",(-0.4,-1.2,1.8),150,3.0,hand_focus)
    area("J2B_Rim",(-1.2,2.8,2.0),260,2.0,hand_focus)

    out_dir=project_root()/"renders"/"hand_refine_j2b"
    out_dir.mkdir(parents=True,exist_ok=True)

    views=[
        ("J2B_Hand_Frontish",(-1.55,-2.2,1.47),hand_focus,78,"J2B_Hand_Frontish.png"),
        ("J2B_Hand_Backish",(-1.55,2.2,1.47),hand_focus,78,"J2B_Hand_Backish.png"),
        ("J2B_Arm_ThreeQuarter",(-0.95,-3.4,1.75),Vector((-0.95,0.08,1.48)),68,"J2B_Arm_ThreeQuarter.png"),
    ]

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
        print(f"[Step01M-J2B] Rendered {out_dir/fn}")

    for name,state in states.items():
        obj=bpy.data.objects.get(name)
        if obj:
            obj.hide_render=state

def write_report(stats):
    out_dir=project_root()/"renders"/"hand_refine_j2b"
    out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/"J2B_DataDriven_Report.txt"
    path.write_text(
        "Step01M-J2B Data-Driven Hand Reshape\n"
        "====================================\n\n"
        f"Vertices moved: {stats['vertices_moved']}\n"
        f"Finger-zone vertices shaped: {stats['finger_zone_vertices']}\n"
        f"Underside/thumb-zone vertices lifted: {stats['underside_vertices_lifted']}\n\n"
        "Measured source basis:\n"
        "tip/palm X span approximately -1.47 to -1.06\n"
        "wrist transition approximately -1.06 to -0.88\n"
        "arm center approximately Y=0.085, Z=1.445\n\n"
        "Operations:\n"
        "- exact cross-section-driven Y/Z compaction\n"
        "- modest forward shortening\n"
        "- three-lobe tip silhouette shaping\n"
        "- underside/thumb droop reduction\n"
        "- minimal hand-only smoothing\n",
        encoding="utf-8"
    )

def main():
    source=pick_source()
    target=duplicate_source(source)
    stats=reshape(target)
    render_views(target)
    write_report(stats)

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J2B] Saved: {out}")

if __name__=="__main__":
    main()
