import bpy
import math
from common import ensure_collection

def build():
    col = ensure_collection("CAM_Rigs")

    target = bpy.data.objects.get("CAM_Target")
    if target is None:
        target = bpy.data.objects.new("CAM_Target", None)
        col.objects.link(target)
    target.location = (0.0, 0.0, 1.45)

    cam_data = bpy.data.cameras.get("CAM_Orbit_Data")
    if cam_data is None:
        cam_data = bpy.data.cameras.new("CAM_Orbit_Data")

    cam = bpy.data.objects.get("CAM_Orbit")
    if cam is None:
        cam = bpy.data.objects.new("CAM_Orbit", cam_data)
        col.objects.link(cam)

    cam.data.lens = 42.0

    # Start clean so reruns remain deterministic.
    for constraint in list(cam.constraints):
        cam.constraints.remove(constraint)
    cam.animation_data_clear()

    track = cam.constraints.new(type='TRACK_TO')
    track.name = "Track Subject"
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    start_frame = 1
    end_frame = 180
    samples = 37
    start_angle = math.radians(-65.0)
    end_angle = math.radians(175.0)

    for i in range(samples):
        t = i / (samples - 1)
        frame = round(start_frame + (end_frame - start_frame) * t)
        angle = start_angle + (end_angle - start_angle) * t
        radius = 7.2 + (6.2 - 7.2) * t
        z = 4.2 + (0.75 - 4.2) * t

        cam.location = (
            radius * math.cos(angle),
            radius * math.sin(angle),
            z,
        )
        cam.keyframe_insert(data_path="location", frame=frame)

    # Blender 5.1 uses the layered Action system. We intentionally leave the
    # interpolation at Blender's defaults here; the explicit transform keys are
    # sufficient for the camera-motion proof and avoid legacy action.fcurves access.
    bpy.context.scene.camera = cam
    bpy.context.scene.frame_start = start_frame
    bpy.context.scene.frame_end = end_frame
    bpy.context.scene.frame_set(start_frame)

    print("[Step00 v2] Orbit camera rebuilt with explicit location keyframes.")

if __name__ == "__main__":
    build()
