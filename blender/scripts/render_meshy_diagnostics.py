import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

TARGET_COLLECTION = "CHAR_Meshy_Working"

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def collection_bounds(col):
    xs, ys, zs = [], [], []
    for obj in col.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            co = obj.matrix_world @ Vector(corner)
            xs.append(co.x); ys.append(co.y); zs.append(co.z)
    if not xs:
        raise RuntimeError(f"No mesh bounds in collection {col.name}")
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def setup_studio():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.world.color = (0.92, 0.92, 0.94)

    # Hide non-diagnostic scene collections.
    for name in ("ENV_ParkingLot", "LGT_Night", "CAM_Rigs", "CHAR_SackDoll", "BASE_Meshy_Source"):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_render = True
            col.hide_viewport = True

    target = bpy.data.collections.get(TARGET_COLLECTION)
    if not target:
        raise RuntimeError(f"Missing {TARGET_COLLECTION}")
    target.hide_render = False
    target.hide_viewport = False

    studio = ensure_collection("DIAG_Meshy_Studio")

    for name in ("MESHY_DIAG_Floor","MESHY_DIAG_Key","MESHY_DIAG_Fill","MESHY_DIAG_Rim","MESHY_DIAG_Camera"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor = bpy.context.object
    floor.name = "MESHY_DIAG_Floor"
    floor.scale = (7,7,7)
    mat = bpy.data.materials.get("MAT_MeshyDiagFloor") or bpy.data.materials.new("MAT_MeshyDiagFloor")
    mat.diffuse_color = (0.95,0.95,0.96,1)
    floor.data.materials.append(mat)
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    studio.objects.link(floor)

    def area(name, loc, energy, size):
        data = bpy.data.lights.new(name=name, type='AREA')
        data.energy = energy
        data.shape = 'DISK'
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        studio.objects.link(obj)
        return obj

    area("MESHY_DIAG_Key", (4,-4,5), 1900, 3.5)
    area("MESHY_DIAG_Fill", (-4,-2,3), 900, 4.0)
    area("MESHY_DIAG_Rim", (0,4,4), 1000, 3.5)

    cam_data = bpy.data.cameras.get("MESHY_DIAG_Camera_Data") or bpy.data.cameras.new("MESHY_DIAG_Camera_Data")
    cam = bpy.data.objects.new("MESHY_DIAG_Camera", cam_data)
    studio.objects.link(cam)
    cam.data.lens = 55

    return target, cam

def render_view(cam, name, loc, target):
    scene = bpy.context.scene
    cam.location = loc
    look_at(cam, target)
    scene.camera = cam

    out_dir = project_root() / "renders" / "meshy_baseline_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M] Rendered {path}")

def run():
    col, cam = setup_studio()
    xmin,xmax,ymin,ymax,zmin,zmax = collection_bounds(col)
    center = Vector(((xmin+xmax)/2, (ymin+ymax)/2, (zmin+zmax)/2))
    height = zmax-zmin
    distance = max(5.4, height * 2.1)

    render_view(cam, "Meshy_Front", (0,-distance,center.z), center)
    render_view(cam, "Meshy_Side", (distance,0,center.z), center)
    render_view(cam, "Meshy_Back", (0,distance,center.z), center)
    render_view(cam, "Meshy_ThreeQuarterFront", (distance*0.78,-distance*0.78,center.z+0.15), center)
    render_view(cam, "Meshy_ThreeQuarterRear", (-distance*0.78,distance*0.78,center.z+0.15), center)

    print("[Step01M] Meshy baseline diagnostics complete.")

if __name__ == "__main__":
    run()
