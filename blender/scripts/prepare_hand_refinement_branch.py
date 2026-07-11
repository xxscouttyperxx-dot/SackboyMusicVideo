import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_NAME = "F2"
WORK_COLLECTION = "CHAR_HandRefine_Working"
DIAG_COLLECTION = "DIAG_HandRefine_Lights"
CAM_COLLECTION = "DIAG_HandRefine_Cameras"

def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def world_bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def look_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def duplicate_working(source):
    col = replace_collection(WORK_COLLECTION)
    dup = source.copy()
    dup.data = source.data.copy()
    col.objects.link(dup)
    dup.name = "HANDREFINE_Working"
    dup.hide_viewport = False
    dup.hide_render = False

    source.hide_render = True
    source.hide_viewport = True
    print(f"[Step01M-J0] Created working duplicate: {dup.name}")
    return dup

def setup_scene(target):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world.color=(0.045,0.045,0.055)

    # Hide all other meshes for diagnostic render.
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj != target:
            obj.hide_render = True
    target.hide_render=False

    light_col=replace_collection(DIAG_COLLECTION)
    cam_col=replace_collection(CAM_COLLECTION)

    def area(name,loc,energy,size):
        data=bpy.data.lights.new(name=name+"_Data", type='AREA')
        data.energy=energy
        data.shape='RECTANGLE'
        data.size=size
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        light_col.objects.link(obj)
        return obj

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h=zmax-zmin
    w=xmax-xmin

    # Raking light rig: deliberately lower intensity and side-biased.
    key=area("HANDDIAG_RakeKey",(-3.5,-4.5,3.6),700,2.2)
    look_at(key, center)
    fill=area("HANDDIAG_SoftFill",(3.0,-2.0,2.3),180,3.5)
    look_at(fill, center)
    rim=area("HANDDIAG_Rim",(0,4.0,3.2),350,2.0)
    look_at(rim, center)

    # Neutral gray floor
    bpy.ops.mesh.primitive_plane_add(location=(0,0,zmin))
    floor=bpy.context.object
    floor.name="HANDDIAG_Floor"
    floor.scale=(7,7,7)
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    light_col.objects.link(floor)

    mat=bpy.data.materials.get("MAT_HandDiagFloor") or bpy.data.materials.new("MAT_HandDiagFloor")
    mat.diffuse_color=(0.18,0.18,0.20,1)
    floor.data.materials.clear()
    floor.data.materials.append(mat)

    return cam_col, center, h, w, (xmin,xmax,ymin,ymax,zmin,zmax)

def create_camera(col,name,loc,target,lens=60):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    cam.data.lens=lens
    cam.location=loc
    look_at(cam,target)
    col.objects.link(cam)
    return cam

def render(cam,filename):
    scene=bpy.context.scene
    scene.render.resolution_x=1280
    scene.render.resolution_y=1280
    scene.camera=cam
    out_dir=project_root()/"renders"/"hand_refine_prep"
    out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/filename
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-J0] Rendered {path}")

def main():
    source=bpy.data.objects.get(SOURCE_NAME)
    if not source or source.type!='MESH':
        raise RuntimeError("Expected source object F2 was not found.")

    target=duplicate_working(source)
    cam_col,center,h,w,b=setup_scene(target)
    xmin,xmax,ymin,ymax,zmin,zmax=b
    d=max(5.0,h*2.0)

    render(create_camera(cam_col,"HANDDIAG_Front",(0,-d,center.z),center,60),"HandPrep_Front_Raking.png")
    render(create_camera(cam_col,"HANDDIAG_ThreeQuarter",(d*.76,-d*.76,center.z+.1),center,60),"HandPrep_ThreeQuarter_Raking.png")

    left_target=Vector((xmin+w*.085,ymin+(ymax-ymin)*.28,zmin+h*.57))
    render(create_camera(cam_col,"HANDDIAG_LeftClose",(xmin-w*.05,-d*.48,zmin+h*.58),left_target,72),"HandPrep_LeftHand_Raking.png")

    right_target=Vector((xmin+w*.915,ymin+(ymax-ymin)*.28,zmin+h*.57))
    render(create_camera(cam_col,"HANDDIAG_RightClose",(xmax+w*.05,-d*.48,zmin+h*.58),right_target,72),"HandPrep_RightHand_Raking.png")

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J0] Saved hand-refinement working branch and diagnostic rig: {out}")

if __name__=="__main__":
    main()
