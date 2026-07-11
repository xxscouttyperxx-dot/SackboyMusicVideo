import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir=Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0,str(scripts_dir))

from common import project_root,ensure_collection

TARGET_COLLECTION="CHAR_Meshy_LeftCandidate_HandCompact"
WIRE_COLLECTION="DIAG_HandCompact_WireOverlay"

def remove_collection_and_objects(name):
    col=bpy.data.collections.get(name)
    if not col:
        return
    for obj in list(col.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(col)

def bounds(col):
    xs=[];ys=[];zs=[]
    for obj in col.objects:
        if obj.type!='MESH': continue
        for corner in obj.bound_box:
            co=obj.matrix_world@Vector(corner)
            xs.append(co.x);ys.append(co.y);zs.append(co.z)
    if not xs: raise RuntimeError("No target mesh bounds.")
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def look_at(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def make_wire_overlay(target_col):
    remove_collection_and_objects(WIRE_COLLECTION)
    wire_col=ensure_collection(WIRE_COLLECTION)

    mat=bpy.data.materials.get("MAT_TopologyWire")
    if mat is None:
        mat=bpy.data.materials.new("MAT_TopologyWire")
        mat.diffuse_color=(0.015,0.015,0.018,1)

    for obj in target_col.objects:
        if obj.type!='MESH': continue
        dup=obj.copy()
        dup.data=obj.data.copy()
        wire_col.objects.link(dup)
        dup.name=obj.name+"_WIRE"

        dup.data.materials.clear()
        dup.data.materials.append(mat)

        mod=dup.modifiers.new(name="TopologyWire",type='WIREFRAME')
        mod.thickness=0.0015
        mod.use_replace=True
        mod.use_even_offset=True

    wire_col.hide_render=True
    wire_col.hide_viewport=True
    return wire_col

def setup():
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world.color=(0.92,0.92,0.94)

    for name in (
        "ENV_ParkingLot","LGT_Night","CAM_Rigs","CHAR_SackDoll",
        "BASE_Meshy_Source","CHAR_Meshy_Working","CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source","CHAR_Meshy_LeftCandidate_Working",
        "CHAR_Meshy_LeftCandidate_Repaired","CHAR_Meshy_LeftCandidate_Refined",
        "CHAR_Meshy_LeftCandidate_Structural","MESHY_CandidateGallery",
        "MESHY_Components"
    ):
        col=bpy.data.collections.get(name)
        if col:
            col.hide_viewport=True
            col.hide_render=True

    target=bpy.data.collections.get(TARGET_COLLECTION)
    if not target: raise RuntimeError(f"Missing {TARGET_COLLECTION}")
    target.hide_viewport=False
    target.hide_render=False

    studio=ensure_collection("DIAG_HandCompact_Studio")
    for name in ("HG_Floor","HG_Key","HG_Fill","HG_Rim","HG_Camera"):
        obj=bpy.data.objects.get(name)
        if obj: bpy.data.objects.remove(obj,do_unlink=True)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor=bpy.context.object
    floor.name="HG_Floor"
    floor.scale=(7,7,7)
    for c in list(floor.users_collection): c.objects.unlink(floor)
    studio.objects.link(floor)

    mat=bpy.data.materials.get("MAT_HGFloor") or bpy.data.materials.new("MAT_HGFloor")
    mat.diffuse_color=(0.95,0.95,0.96,1)
    floor.data.materials.append(mat)

    def area(name,loc,energy,size):
        data=bpy.data.lights.new(name=name,type='AREA')
        data.energy=energy;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);obj.location=loc;studio.objects.link(obj)

    area("HG_Key",(4,-4,5),1900,3.5)
    area("HG_Fill",(-4,-2,3),900,4.0)
    area("HG_Rim",(0,4,4),1000,3.5)

    cam_data=bpy.data.cameras.get("HG_Camera_Data") or bpy.data.cameras.new("HG_Camera_Data")
    cam=bpy.data.objects.new("HG_Camera",cam_data)
    cam.data.lens=55
    studio.objects.link(cam)

    wire=make_wire_overlay(target)
    return target,wire,cam

def render(cam,label,loc,target,res=(1280,1280)):
    scene=bpy.context.scene
    scene.render.resolution_x=res[0]
    scene.render.resolution_y=res[1]
    cam.location=loc
    look_at(cam,target)
    scene.camera=cam
    out_dir=project_root()/"renders"/"meshy_handcompact_diagnostics"
    out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/f"{label}.png"
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-G] Rendered {path}")

def main():
    target_col,wire_col,cam=setup()
    xmin,xmax,ymin,ymax,zmin,zmax=bounds(target_col)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h=zmax-zmin
    d=max(5.0,h*2.0)

    # Solid diagnostics
    render(cam,"HandCompact_Front",(0,-d,center.z),center)
    render(cam,"HandCompact_ThreeQuarterFront",(d*.78,-d*.78,center.z+.15),center)

    left_target=Vector((xmin+(xmax-xmin)*0.085,ymin+(ymax-ymin)*0.30,zmin+h*0.57))
    render(cam,"HandCompact_LeftHandCloseup",(xmin-(xmax-xmin)*0.05,-d*.50,zmin+h*0.58),left_target)

    right_target=Vector((xmin+(xmax-xmin)*0.915,ymin+(ymax-ymin)*0.30,zmin+h*0.57))
    render(cam,"HandCompact_RightHandCloseup",(xmax+(xmax-xmin)*0.05,-d*.50,zmin+h*0.58),right_target)

    # Wireframe topology overlays only
    target_col.hide_render=True
    wire_col.hide_render=False

    render(cam,"Topology_Front",(0,-d,center.z),center)
    render(cam,"Topology_LeftHandCloseup",(xmin-(xmax-xmin)*0.05,-d*.50,zmin+h*0.58),left_target)
    render(cam,"Topology_RightHandCloseup",(xmax+(xmax-xmin)*0.05,-d*.50,zmin+h*0.58),right_target)
    face_target=Vector((center.x,ymin+(ymax-ymin)*0.12,zmin+h*0.82))
    render(cam,"Topology_FaceCloseup",(0,-d*.57,zmin+h*.83),face_target)
    stomach_target=Vector((center.x,ymin+(ymax-ymin)*0.18,zmin+h*.43))
    render(cam,"Topology_StomachCloseup",(0,-d*.70,zmin+h*.43),stomach_target)

    # restore solid as visible state
    target_col.hide_render=False
    wire_col.hide_render=True

    print("[Step01M-G] Solid and topology diagnostics complete.")

if __name__=="__main__":
    main()
