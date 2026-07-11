import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

TARGET_COLLECTION = "CHAR_Meshy_LeftCandidate_Refined"  # Step01M-E baseline, not F/G
CAMERA_NAME = "ORANGE_TOPO_Camera"

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

def set_visibility():
    for name in (
        "ENV_ParkingLot", "LGT_Night", "CAM_Rigs", "CHAR_SackDoll",
        "BASE_Meshy_Source", "CHAR_Meshy_Working", "CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source", "CHAR_Meshy_LeftCandidate_Working",
        "CHAR_Meshy_LeftCandidate_Repaired", "CHAR_Meshy_LeftCandidate_Structural",
        "CHAR_Meshy_LeftCandidate_HandCompact", "MESHY_CandidateGallery",
        "MESHY_Components", "MESHY_GalleryComponents"
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
    return target

def setup_workbench():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'SINGLE'
    shading.single_color = (1.0, 0.16, 0.0)
    shading.background_type = 'VIEWPORT'
    shading.background_color = (0.018, 0.018, 0.022)
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = 'WORLD'
    shading.curvature_ridge_factor = 2.0
    shading.curvature_valley_factor = 1.5
    shading.show_xray = True
    shading.xray_alpha = 0.22

    # Wireframe overlay on the actual mesh.
    for obj in bpy.data.collections[TARGET_COLLECTION].objects:
        if obj.type == 'MESH':
            obj.display_type = 'WIRE'
            obj.show_wire = True
            obj.show_all_edges = True
            obj.color = (1.0, 0.16, 0.0, 1.0)

    studio = ensure_collection("DIAG_OrangeTopology_Studio")

    old = bpy.data.objects.get(CAMERA_NAME)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    cam_data = bpy.data.cameras.get(CAMERA_NAME + "_Data") or bpy.data.cameras.new(CAMERA_NAME + "_Data")
    cam = bpy.data.objects.new(CAMERA_NAME, cam_data)
    cam.data.lens = 58
    studio.objects.link(cam)

    return cam

def render_view(cam, label, loc, target, res=(1400, 1400)):
    scene = bpy.context.scene
    scene.render.resolution_x = res[0]
    scene.render.resolution_y = res[1]
    cam.location = loc
    look_at(cam, target)
    scene.camera = cam

    out_dir = project_root() / "renders" / "orange_topology_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{label}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-H] Rendered {path}")

def main():
    target_col = set_visibility()
    cam = setup_workbench()

    xmin, xmax, ymin, ymax, zmin, zmax = collection_bounds(target_col)
    center = Vector(((xmin+xmax)/2, (ymin+ymax)/2, (zmin+zmax)/2))
    h = zmax-zmin
    w = xmax-xmin
    d = max(5.0, h*2.0)

    render_view(cam, "OrangeTopo_Front", (0, -d, center.z), center)
    render_view(cam, "OrangeTopo_Side", (d, 0, center.z), center)
    render_view(cam, "OrangeTopo_ThreeQuarterFront", (d*.78, -d*.78, center.z+.12), center)

    left_hand_target = Vector((xmin+w*0.085, ymin+(ymax-ymin)*0.28, zmin+h*0.57))
    render_view(cam, "OrangeTopo_LeftHandCloseup", (xmin-w*0.06, -d*.50, zmin+h*0.58), left_hand_target)

    right_hand_target = Vector((xmin+w*0.915, ymin+(ymax-ymin)*0.28, zmin+h*0.57))
    render_view(cam, "OrangeTopo_RightHandCloseup", (xmax+w*0.06, -d*.50, zmin+h*0.58), right_hand_target)

    face_target = Vector((center.x, ymin+(ymax-ymin)*0.12, zmin+h*0.82))
    render_view(cam, "OrangeTopo_FaceCloseup", (0, -d*.58, zmin+h*.83), face_target)

    stomach_target = Vector((center.x, ymin+(ymax-ymin)*0.18, zmin+h*.43))
    render_view(cam, "OrangeTopo_StomachCloseup", (0, -d*.68, zmin+h*.43), stomach_target)

    print("[Step01M-H] Orange X-ray topology diagnostics complete.")

if __name__ == "__main__":
    main()
