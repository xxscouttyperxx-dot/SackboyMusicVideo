import sys
from pathlib import Path

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import bpy
from common import project_root

def configure():
    scene = bpy.context.scene

    # Blender 5.1 accepts BLENDER_EEVEE, BLENDER_WORKBENCH, or CYCLES.
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 50
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 180
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

def validate_camera_motion():
    scene = bpy.context.scene
    cam = bpy.data.objects.get("CAM_Orbit")
    if cam is None:
        raise RuntimeError("CAM_Orbit missing")

    positions = []
    for frame in (1, 90, 180):
        scene.frame_set(frame)
        positions.append(tuple(round(v, 4) for v in cam.matrix_world.translation))

    if len(set(positions)) != 3:
        raise RuntimeError(f"CAM_Orbit is not moving: {positions}")

    print(f"[Step00 v2] Camera positions: {positions}")

def render_preview(camera_name, frame):
    scene = bpy.context.scene
    cam = bpy.data.objects.get(camera_name)
    if cam is None:
        raise RuntimeError(f"Missing camera: {camera_name}")

    scene.camera = cam
    scene.frame_set(frame)

    out_dir = project_root() / "renders" / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{camera_name}_frame_{frame:04d}.png"

    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)

    if not output.exists():
        raise RuntimeError(f"Expected render was not created: {output}")

    print(f"[Step00 v2] Rendered {output}")

if __name__ == "__main__":
    configure()
    validate_camera_motion()

    for frame in (1, 90, 180):
        render_preview("CAM_Orbit", frame)
    render_preview("CAM_Low", 1)

    print("[Step00 v2] Diagnostic render run complete.")
