import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_OBJ = project_root() / "reference" / "meshy_candidates" / "Meshy_Left_Standing_Candidate.obj"
SOURCE_COLLECTION = "BASE_Meshy_LeftCandidate_Source"
WORK_COLLECTION = "CHAR_Meshy_LeftCandidate_Working"
TARGET_HEIGHT = 2.75

def remove_collection_and_objects(name):
    col = bpy.data.collections.get(name)
    if not col:
        return
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def unlink_all(obj):
    for c in list(obj.users_collection):
        try:
            c.objects.unlink(obj)
        except:
            pass

def bounds_world(objects):
    xs, ys, zs = [], [], []
    for obj in objects:
        for corner in obj.bound_box:
            co = obj.matrix_world @ Vector(corner)
            xs.append(co.x); ys.append(co.y); zs.append(co.z)
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def hide_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        col.hide_viewport = True
        col.hide_render = True

def main():
    if not SOURCE_OBJ.exists():
        raise RuntimeError(f"Missing candidate OBJ: {SOURCE_OBJ}")

    remove_collection_and_objects(SOURCE_COLLECTION)
    remove_collection_and_objects(WORK_COLLECTION)

    source_col = ensure_collection(SOURCE_COLLECTION)
    work_col = ensure_collection(WORK_COLLECTION)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.obj_import(
        filepath=str(SOURCE_OBJ),
        forward_axis='NEGATIVE_Z',
        up_axis='Y',
    )

    imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not imported:
        raise RuntimeError("Candidate OBJ import produced no mesh objects.")

    for obj in imported:
        unlink_all(obj)
        source_col.objects.link(obj)

    xmin,xmax,ymin,ymax,zmin,zmax = bounds_world(imported)
    h = zmax-zmin
    scale = TARGET_HEIGHT / h
    for obj in imported:
        obj.scale *= scale

    bpy.context.view_layer.update()
    xmin,xmax,ymin,ymax,zmin,zmax = bounds_world(imported)
    cx=(xmin+xmax)/2
    cy=(ymin+ymax)/2

    for obj in imported:
        obj.location.x -= cx
        obj.location.y -= cy
        obj.location.z -= zmin

    bpy.context.view_layer.update()

    for i,obj in enumerate(imported):
        obj.name=f"MESHY_LEFT_SOURCE_{i:02d}"
        dup=obj.copy()
        if obj.data:
            dup.data=obj.data.copy()
        work_col.objects.link(dup)
        dup.name=f"MESHY_LEFT_WORK_{i:02d}"
        if dup.type=='MESH':
            for p in dup.data.polygons:
                p.use_smooth=True

    source_col.hide_viewport=True
    source_col.hide_render=True
    work_col.hide_viewport=False
    work_col.hide_render=False

    for name in (
        "CHAR_SackDoll",
        "BASE_Meshy_Source",
        "CHAR_Meshy_Working",
        "CHAR_Meshy_Isolated",
        "MESHY_CandidateGallery",
        "MESHY_Components",
        "MESHY_GalleryComponents",
    ):
        hide_collection(name)

    scene=bpy.context.scene
    scene["active_character_collection"]=WORK_COLLECTION
    scene["meshy_candidate_source"]="left standing figure spatial extraction"

    out=project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-C] Imported left standing candidate.")
    print(f"[Step01M-C] Working collection: {WORK_COLLECTION}")
    print(f"[Step01M-C] Saved: {out}")

if __name__=="__main__":
    main()
