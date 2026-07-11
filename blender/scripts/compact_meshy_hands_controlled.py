import sys
from pathlib import Path
import bpy
import bmesh

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_COLLECTION = "CHAR_Meshy_LeftCandidate_Refined"  # Step01M-E, before the failed structural pass
OUTPUT_COLLECTION = "CHAR_Meshy_LeftCandidate_HandCompact"

def remove_collection_and_objects(name):
    col = bpy.data.collections.get(name)
    if not col:
        return
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def unlink_all(obj):
    for col in list(obj.users_collection):
        try:
            col.objects.unlink(obj)
        except:
            pass

def duplicate_source():
    source = bpy.data.collections.get(SOURCE_COLLECTION)
    if not source:
        raise RuntimeError(
            f"Missing {SOURCE_COLLECTION}. Step01M-E must remain in the .blend file."
        )

    remove_collection_and_objects(OUTPUT_COLLECTION)
    out_col = ensure_collection(OUTPUT_COLLECTION)

    objects = []
    for obj in source.objects:
        if obj.type != 'MESH':
            continue
        dup = obj.copy()
        dup.data = obj.data.copy()
        unlink_all(dup)
        out_col.objects.link(dup)
        dup.name = obj.name.replace("REFINED", "HANDCOMPACT")
        objects.append(dup)

    if not objects:
        raise RuntimeError("No Step01M-E mesh objects found.")
    return out_col, objects

def local_bounds(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def compact_hands_without_smoothing(obj):
    xmin,xmax,ymin,ymax,zmin,zmax = local_bounds(obj)
    width=xmax-xmin
    depth=ymax-ymin
    height=zmax-zmin

    def nx(x): return (x-xmin)/max(width,1e-9)
    def ny(y): return (y-ymin)/max(depth,1e-9)
    def nz(z): return (z-zmin)/max(height,1e-9)

    counts = {"left":0, "right":0}

    for v in obj.data.vertices:
        X,Y,Z = nx(v.co.x), ny(v.co.y), nz(v.co.z)

        is_left = X < 0.115 and 0.455 < Z < 0.705
        is_right = X > 0.885 and 0.455 < Z < 0.705

        if not (is_left or is_right):
            continue

        if is_left:
            cx = xmin + width*0.080
            counts["left"] += 1
        else:
            cx = xmin + width*0.920
            counts["right"] += 1

        cy = ymin + depth*0.50
        cz = zmin + height*0.585

        # IMPORTANT: no smoothing. Preserve existing finger valleys/separation.
        # Compact the whole hand volume around its own palm center.
        v.co.x = cx + (v.co.x-cx)*0.82
        v.co.y = cy + (v.co.y-cy)*0.84
        v.co.z = cz + (v.co.z-cz)*0.88

    # Normals only; do not smooth vertices.
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    if bm.faces:
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    for poly in obj.data.polygons:
        poly.use_smooth=True

    return counts

def write_report(stats):
    out_dir=project_root()/"renders"/"meshy_handcompact_diagnostics"
    out_dir.mkdir(parents=True,exist_ok=True)
    report=out_dir/"Meshy_hand_compact_report.txt"
    lines=["Step01M-G Controlled Hand Compact Report\n\n"]
    for name,counts in stats:
        lines.append(
            f"{name}\n"
            f"  left hand vertices compacted: {counts['left']}\n"
            f"  right hand vertices compacted: {counts['right']}\n"
            "  vertex smoothing: NONE\n"
            "  face deformation: NONE\n"
            "  neck deformation: NONE\n"
            "  shoulder/hip deformation: NONE\n\n"
        )
    report.write_text("".join(lines),encoding="utf-8")
    print(f"[Step01M-G] Wrote report: {report}")

def set_visibility():
    for name in (
        "CHAR_SackDoll","BASE_Meshy_Source","CHAR_Meshy_Working",
        "CHAR_Meshy_Isolated","BASE_Meshy_LeftCandidate_Source",
        "CHAR_Meshy_LeftCandidate_Working","CHAR_Meshy_LeftCandidate_Repaired",
        "CHAR_Meshy_LeftCandidate_Refined","CHAR_Meshy_LeftCandidate_Structural",
        "MESHY_CandidateGallery","MESHY_Components","MESHY_GalleryComponents",
    ):
        col=bpy.data.collections.get(name)
        if col:
            col.hide_viewport=True
            col.hide_render=True

    out=bpy.data.collections.get(OUTPUT_COLLECTION)
    if out:
        out.hide_viewport=False
        out.hide_render=False

def main():
    out_col,objects=duplicate_source()
    stats=[]
    for obj in objects:
        stats.append((obj.name,compact_hands_without_smoothing(obj)))

    write_report(stats)
    set_visibility()

    scene=bpy.context.scene
    scene["active_character_collection"]=OUTPUT_COLLECTION
    scene["shape_cleanup_version"]="Step01M-G"

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print("[Step01M-G] Controlled hand compact pass complete.")
    print("[Step01M-G] Base source: Step01M-E refined collection.")
    print("[Step01M-G] No smoothing or whole-body deformation applied.")
    print(f"[Step01M-G] Saved: {out}")

if __name__=="__main__":
    main()
