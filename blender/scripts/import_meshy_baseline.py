import sys
from pathlib import Path
import bpy

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_OBJ = project_root() / "reference" / "meshy_baseline" / "Meshy_AI_T_Pose_Reference_Shee_0710063952_generate.obj"
TARGET_HEIGHT = 2.75

SOURCE_COLLECTION = "BASE_Meshy_Source"
WORK_COLLECTION = "CHAR_Meshy_Working"
PROCEDURAL_COLLECTION = "CHAR_SackDoll"

def remove_collection_and_objects(name):
    col = bpy.data.collections.get(name)
    if not col:
        return
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def unlink_from_all(obj):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)

def bounds_world(objects):
    xs, ys, zs = [], [], []
    for obj in objects:
        for corner in obj.bound_box:
            co = obj.matrix_world @ __import__("mathutils").Vector(corner)
            xs.append(co.x); ys.append(co.y); zs.append(co.z)
    return (
        min(xs), max(xs),
        min(ys), max(ys),
        min(zs), max(zs),
    )

def set_collection_visibility(name, viewport, render):
    col = bpy.data.collections.get(name)
    if col:
        col.hide_viewport = not viewport
        col.hide_render = not render

def import_obj():
    if not SOURCE_OBJ.exists():
        raise RuntimeError(f"Missing source OBJ: {SOURCE_OBJ}")

    remove_collection_and_objects(SOURCE_COLLECTION)
    remove_collection_and_objects(WORK_COLLECTION)

    source_col = ensure_collection(SOURCE_COLLECTION)
    work_col = ensure_collection(WORK_COLLECTION)

    # Deselect everything before import.
    bpy.ops.object.select_all(action='DESELECT')

    # Blender 4+ / 5.x OBJ importer.
    bpy.ops.wm.obj_import(
        filepath=str(SOURCE_OBJ),
        forward_axis='NEGATIVE_Z',
        up_axis='Y',
    )

    imported = list(bpy.context.selected_objects)
    if not imported:
        raise RuntimeError("OBJ importer returned no selected objects.")

    # Consolidate imported objects into source collection.
    for obj in imported:
        unlink_from_all(obj)
        source_col.objects.link(obj)

    # Normalize source to target height and put feet on Z=0.
    xmin, xmax, ymin, ymax, zmin, zmax = bounds_world(imported)
    height = zmax - zmin
    if height <= 0:
        raise RuntimeError("Imported OBJ has invalid zero height.")

    scale = TARGET_HEIGHT / height
    for obj in imported:
        obj.scale *= scale

    bpy.context.view_layer.update()
    xmin, xmax, ymin, ymax, zmin, zmax = bounds_world(imported)
    cx = (xmin + xmax) * 0.5
    cy = (ymin + ymax) * 0.5

    for obj in imported:
        obj.location.x -= cx
        obj.location.y -= cy
        obj.location.z -= zmin

    bpy.context.view_layer.update()

    # Rename source objects and duplicate into editable working collection.
    working = []
    for index, obj in enumerate(imported):
        obj.name = f"MESHY_SOURCE_{index:02d}"
        dup = obj.copy()
        if obj.data:
            dup.data = obj.data.copy()
        work_col.objects.link(dup)
        dup.name = f"MESHY_WORK_{index:02d}"
        working.append(dup)

    # Lock original baseline from viewport/render; use working duplicate.
    source_col.hide_viewport = True
    source_col.hide_render = True
    work_col.hide_viewport = False
    work_col.hide_render = False

    # Hide the old procedural graybox but keep it in the file for comparison/rollback.
    set_collection_visibility(PROCEDURAL_COLLECTION, viewport=False, render=False)

    # Smooth shading on the working copy where supported.
    for obj in working:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

    # Custom metadata.
    scene = bpy.context.scene
    scene["meshy_baseline_source"] = str(SOURCE_OBJ)
    scene["meshy_target_height"] = TARGET_HEIGHT
    scene["active_character_collection"] = WORK_COLLECTION

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print(f"[Step01M] Imported Meshy baseline from: {SOURCE_OBJ}")
    print(f"[Step01M] Source collection: {SOURCE_COLLECTION} (hidden/locked by convention)")
    print(f"[Step01M] Working collection: {WORK_COLLECTION}")
    print(f"[Step01M] Saved: {out}")

if __name__ == "__main__":
    import_obj()
