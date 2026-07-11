import sys
from pathlib import Path

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import bpy
from mathutils import Vector
from common import project_root, ensure_collection

def ensure_studio_setup():
    # Hide environment and lighting collections for clean diagnostics.
    for name in ("ENV_ParkingLot", "LGT_Night", "CAM_Rigs"):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_render = True
            col.hide_viewport = True

    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    scene.world.color = (0.92, 0.92, 0.94)

    studio = ensure_collection("DIAG_Studio")

    # Remove old diagnostic objects if rerun.
    for name in ("DIAG_Floor", "DIAG_Key", "DIAG_Fill", "DIAG_Rim", "DIAG_Camera"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Neutral floor
    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor = bpy.context.object
    floor.name = "DIAG_Floor"
    floor.scale = (6,6,6)
    mat = bpy.data.materials.get("MAT_DiagFloor") or bpy.data.materials.new("MAT_DiagFloor")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.95,0.95,0.96,1)
    bsdf.inputs["Roughness"].default_value = 0.82
    floor.data.materials.clear()
    floor.data.materials.append(mat)
    studio.objects.link(floor)
    try:
        bpy.context.scene.collection.objects.unlink(floor)
    except:
        pass

    def add_area(name, location, energy, size, color=(1,1,1)):
        data = bpy.data.lights.new(name=name, type='AREA')
        data.energy = energy
        data.shape = 'RECTANGLE'
        data.size = size
        data.size_y = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        studio.objects.link(obj)
        return obj

    key = add_area("DIAG_Key", (3.0, -3.2, 4.5), 2200, 3.2)
    fill = add_area("DIAG_Fill", (-3.0, -2.2, 2.5), 1100, 3.0)
    rim = add_area("DIAG_Rim", (0.0, 3.0, 3.0), 900, 3.5)

    cam_data = bpy.data.cameras.get("DIAG_Camera_Data") or bpy.data.cameras.new("DIAG_Camera_Data")
    cam = bpy.data.objects.get("DIAG_Camera")
    if cam is None:
        cam = bpy.data.objects.new("DIAG_Camera", cam_data)
        studio.objects.link(cam)

    cam.data.lens = 50
    return cam

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def render_view(cam, name, location, target=(0,0,1.35)):
    scene = bpy.context.scene
    cam.location = location
    look_at(cam, target)
    scene.camera = cam
    out_dir = project_root() / "renders" / "character_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01A] Rendered {path}")

def run():
    cam = ensure_studio_setup()
    render_view(cam, "Character_Front", (0.0, -5.6, 1.55))
    render_view(cam, "Character_Side", (5.3, 0.0, 1.55))
    render_view(cam, "Character_Back", (0.0, 5.6, 1.55))
    render_view(cam, "Character_ThreeQuarterFront", (4.7, -4.7, 1.75))
    render_view(cam, "Character_ThreeQuarterRear", (-4.7, 4.7, 1.75))
    print("[Step01A] Character diagnostics complete.")

if __name__ == "__main__":
    run()
