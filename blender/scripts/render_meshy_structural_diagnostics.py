import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

TARGET_COLLECTION = "CHAR_Meshy_LeftCandidate_Structural"

def collection_bounds(col):
    xs, ys, zs = [], [], []
    for obj in col.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            co = obj.matrix_world @ Vector(corner)
            xs.append(co.x); ys.append(co.y); zs.append(co.z)
    if not xs:
        raise RuntimeError(f"No mesh bounds in {col.name}")
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()

def setup_studio():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.world.color = (0.92,0.92,0.94)

    for name in (
        "ENV_ParkingLot","LGT_Night","CAM_Rigs","CHAR_SackDoll",
        "BASE_Meshy_Source","CHAR_Meshy_Working","CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source","CHAR_Meshy_LeftCandidate_Working",
        "CHAR_Meshy_LeftCandidate_Repaired","CHAR_Meshy_LeftCandidate_Refined",
        "MESHY_CandidateGallery","MESHY_Components"
    ):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = True
            col.hide_render = True

    target = bpy.data.collections.get(TARGET_COLLECTION)
    if not target:
        raise RuntimeError(f"Missing collection: {TARGET_COLLECTION}")
    target.hide_viewport = False
    target.hide_render = False

    studio = ensure_collection("DIAG_Meshy_Structural_Studio")

    for name in ("STRUCT_Floor","STRUCT_Key","STRUCT_Fill","STRUCT_Rim","STRUCT_Camera"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor = bpy.context.object
    floor.name = "STRUCT_Floor"
    floor.scale = (7,7,7)
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    studio.objects.link(floor)

    mat = bpy.data.materials.get("MAT_StructFloor") or bpy.data.materials.new("MAT_StructFloor")
    mat.diffuse_color = (0.95,0.95,0.96,1)
    floor.data.materials.append(mat)

    def area(name, loc, energy, size):
        data = bpy.data.lights.new(name=name, type='AREA')
        data.energy = energy
        data.shape = 'DISK'
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        studio.objects.link(obj)

    area("STRUCT_Key",(4,-4,5),1900,3.5)
    area("STRUCT_Fill",(-4,-2,3),900,4.0)
    area("STRUCT_Rim",(0,4,4),1000,3.5)

    cam_data = bpy.data.cameras.get("STRUCT_Camera_Data") or bpy.data.cameras.new("STRUCT_Camera_Data")
    cam = bpy.data.objects.new("STRUCT_Camera", cam_data)
    cam.data.lens = 55
    studio.objects.link(cam)
    return target, cam

def render_view(cam, label, loc, target):
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    cam.location = loc
    look_at(cam, target)
    scene.camera = cam
    out_dir = project_root() / "renders" / "meshy_structural_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{label}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-F] Rendered {path}")

def main():
    col, cam = setup_studio()
    xmin,xmax,ymin,ymax,zmin,zmax = collection_bounds(col)
    center = Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h = zmax-zmin
    d = max(5.0,h*2.0)

    render_view(cam,"Structural_Front",(0,-d,center.z),center)
    render_view(cam,"Structural_Side",(d,0,center.z),center)
    render_view(cam,"Structural_Back",(0,d,center.z),center)
    render_view(cam,"Structural_ThreeQuarterFront",(d*.78,-d*.78,center.z+.15),center)
    render_view(cam,"Structural_ThreeQuarterRear",(-d*.78,d*.78,center.z+.15),center)

    face_target = Vector((center.x, ymin + (ymax-ymin)*0.10, zmin + h*0.83))
    render_view(cam,"Structural_FaceCloseup",(0,-d*0.56,zmin+h*0.84),face_target)

    neck_target = Vector((center.x, ymin + (ymax-ymin)*0.22, zmin + h*0.69))
    render_view(cam,"Structural_NeckCloseup",(0,-d*0.58,zmin+h*0.70),neck_target)

    belly_target = Vector((center.x, ymin + (ymax-ymin)*0.18, zmin+h*0.43))
    render_view(cam,"Structural_StomachCloseup",(0,-d*0.70,zmin+h*0.43),belly_target)

    hand_target = Vector((xmin + (xmax-xmin)*0.10, ymin + (ymax-ymin)*0.28, zmin+h*0.54))
    render_view(cam,"Structural_LeftHandCloseup",(xmin - (xmax-xmin)*0.05, -d*0.52, zmin+h*0.56),hand_target)

    print("[Step01M-F] Structural diagnostics complete.")

if __name__ == "__main__":
    main()
