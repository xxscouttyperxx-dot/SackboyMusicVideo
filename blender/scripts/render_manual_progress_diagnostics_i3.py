import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

CAM_COLLECTION = "DIAG_ManualProgress_Cameras"
STUDIO_COLLECTION = "DIAG_ManualProgress_Studio"

def world_bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def choose_target():
    # Prefer the exact object detected by I2.
    obj=bpy.data.objects.get("F2")
    if obj and obj.type=='MESH':
        print("[Step01M-I3] Using target object: F2")
        return obj

    active=bpy.context.view_layer.objects.active
    if active and active.type=='MESH':
        print(f"[Step01M-I3] Using active mesh: {active.name}")
        return active

    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if not meshes:
        raise RuntimeError("No mesh objects found.")
    target=max(meshes,key=lambda o: o.dimensions.x*o.dimensions.y*o.dimensions.z)
    print(f"[Step01M-I3] Fallback target: {target.name}")
    return target

def save_visibility_state():
    obj_state={}
    col_state={}
    for obj in bpy.context.scene.objects:
        obj_state[obj.name]=(obj.hide_viewport,obj.hide_render)
    for col in bpy.data.collections:
        col_state[col.name]=(col.hide_viewport,col.hide_render)
    return obj_state,col_state

def restore_visibility(obj_state,col_state):
    for name,state in obj_state.items():
        obj=bpy.data.objects.get(name)
        if obj:
            obj.hide_viewport,obj.hide_render=state
    for name,state in col_state.items():
        col=bpy.data.collections.get(name)
        if col:
            col.hide_viewport,col.hide_render=state

def force_target_visible(target):
    target.hide_viewport=False
    target.hide_render=False

    # Unhide every collection that directly owns the target.
    for col in target.users_collection:
        col.hide_viewport=False
        col.hide_render=False
        print(f"[Step01M-I3] Unhid target collection for render: {col.name}")

    # Hide all other mesh objects from render only.
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj != target:
            obj.hide_render=True

def replace_collection(name):
    col=bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def look_at(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def setup_studio():
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world.color=(0.92,0.92,0.94)

    cam_col=replace_collection(CAM_COLLECTION)
    studio=replace_collection(STUDIO_COLLECTION)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor=bpy.context.object
    floor.name="MANUAL_DIAG_Floor"
    floor.scale=(8,8,8)
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    studio.objects.link(floor)

    mat=bpy.data.materials.get("MAT_ManualDiagFloor") or bpy.data.materials.new("MAT_ManualDiagFloor")
    mat.diffuse_color=(0.95,0.95,0.96,1)
    floor.data.materials.clear()
    floor.data.materials.append(mat)

    def area(name,loc,energy,size):
        data=bpy.data.lights.new(name=name+"_Data",type='AREA')
        data.energy=energy
        data.shape='DISK'
        data.size=size
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        studio.objects.link(obj)

    area("MANUAL_DIAG_Key",(4,-4,5),1900,3.5)
    area("MANUAL_DIAG_Fill",(-4,-2,3),900,4.0)
    area("MANUAL_DIAG_Rim",(0,4,4),1000,3.5)

    return cam_col

def create_camera(cam_col,name,loc,target,lens=55):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    data.lens=lens
    cam.location=loc
    look_at(cam,target)
    cam_col.objects.link(cam)
    return cam

def render(cam,filename):
    scene=bpy.context.scene
    scene.render.resolution_x=1280
    scene.render.resolution_y=1280
    scene.camera=cam
    out_dir=project_root()/"renders"/"manual_progress_diagnostics"
    out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/filename
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-I3] Rendered {path}")

def main():
    target=choose_target()
    obj_state,col_state=save_visibility_state()

    try:
        force_target_visible(target)
        cam_col=setup_studio()

        xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
        center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
        h=zmax-zmin; w=xmax-xmin; d=max(5.0,h*2.0)

        views=[
            ("DIAG_Manual_Front",(0,-d,center.z),"Manual_Front.png"),
            ("DIAG_Manual_Side",(d,0,center.z),"Manual_Side.png"),
            ("DIAG_Manual_Back",(0,d,center.z),"Manual_Back.png"),
            ("DIAG_Manual_ThreeQuarterFront",(d*.78,-d*.78,center.z+.15),"Manual_ThreeQuarterFront.png"),
            ("DIAG_Manual_ThreeQuarterRear",(-d*.78,d*.78,center.z+.15),"Manual_ThreeQuarterRear.png"),
        ]
        for name,loc,fn in views:
            render(create_camera(cam_col,name,loc,center),fn)

        face_target=Vector((center.x,ymin+(ymax-ymin)*0.12,zmin+h*.82))
        render(
            create_camera(cam_col,"DIAG_Manual_FaceCloseup",(0,-d*.58,zmin+h*.83),face_target,65),
            "Manual_FaceCloseup.png"
        )

        left_target=Vector((xmin+w*.085,ymin+(ymax-ymin)*.28,zmin+h*.57))
        render(
            create_camera(cam_col,"DIAG_Manual_LeftHandCloseup",(xmin-w*.05,-d*.50,zmin+h*.58),left_target,65),
            "Manual_LeftHandCloseup.png"
        )

        right_target=Vector((xmin+w*.915,ymin+(ymax-ymin)*.28,zmin+h*.57))
        render(
            create_camera(cam_col,"DIAG_Manual_RightHandCloseup",(xmax+w*.05,-d*.50,zmin+h*.58),right_target,65),
            "Manual_RightHandCloseup.png"
        )

    finally:
        restore_visibility(obj_state,col_state)

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-I3] Saved cameras while restoring original visibility state: {out}")

if __name__=="__main__":
    main()
