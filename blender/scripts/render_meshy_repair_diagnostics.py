import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

TARGET_COLLECTION = "CHAR_Meshy_LeftCandidate_Repaired"

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
    scene.world.color = (0.92, 0.92, 0.94)

    for name in (
        "ENV_ParkingLot",
        "LGT_Night",
        "CAM_Rigs",
        "CHAR_SackDoll",
        "BASE_Meshy_Source",
        "CHAR_Meshy_Working",
        "CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source",
        "CHAR_Meshy_LeftCandidate_Working",
        "MESHY_CandidateGallery",
        "MESHY_Components",
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

    studio = ensure_collection("DIAG_Meshy_Repair_Studio")

    for name in ("REPAIR_DIAG_Floor","REPAIR_DIAG_Key","REPAIR_DIAG_Fill","REPAIR_DIAG_Rim","REPAIR_DIAG_Camera"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor = bpy.context.object
    floor.name = "REPAIR_DIAG_Floor"
    floor.scale = (7,7,7)
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    studio.objects.link(floor)

    mat = bpy.data.materials.get("MAT_RepairDiagFloor") or bpy.data.materials.new("MAT_RepairDiagFloor")
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

    area("REPAIR_DIAG_Key",(4,-4,5),1900,3.5)
    area("REPAIR_DIAG_Fill",(-4,-2,3),900,4.0)
    area("REPAIR_DIAG_Rim",(0,4,4),1000,3.5)

    cam_data = bpy.data.cameras.get("REPAIR_DIAG_Camera_Data") or bpy.data.cameras.new("REPAIR_DIAG_Camera_Data")
    cam = bpy.data.objects.new("REPAIR_DIAG_Camera", cam_data)
    cam.data.lens = 55
    studio.objects.link(cam)
    return target, cam

def render_view(cam, label, loc, target):
    scene = bpy.context.scene
    cam.location = loc
    look_at(cam, target)
    scene.camera = cam
    out_dir = project_root() / "renders" / "meshy_repair_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{label}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-D] Rendered {path}")

def main():
    col, cam = setup_studio()
    xmin,xmax,ymin,ymax,zmin,zmax = collection_bounds(col)
    center = Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    height = zmax-zmin
    distance = max(5.0, height*2.0)

    render_view(cam,"Repaired_Front",(0,-distance,center.z),center)
    render_view(cam,"Repaired_Side",(distance,0,center.z),center)
    render_view(cam,"Repaired_Back",(0,distance,center.z),center)
    render_view(cam,"Repaired_ThreeQuarterFront",(distance*.78,-distance*.78,center.z+.15),center)
    render_view(cam,"Repaired_ThreeQuarterRear",(-distance*.78,distance*.78,center.z+.15),center)

    print("[Step01M-D] Repaired candidate diagnostics complete.")

if __name__ == "__main__":
    main()
