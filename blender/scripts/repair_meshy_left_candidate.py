import sys
from pathlib import Path
import bpy
import bmesh

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_COLLECTION = "CHAR_Meshy_LeftCandidate_Working"
REPAIRED_COLLECTION = "CHAR_Meshy_LeftCandidate_Repaired"

MERGE_DISTANCE = 0.0005

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

def duplicate_source():
    source = bpy.data.collections.get(SOURCE_COLLECTION)
    if not source:
        raise RuntimeError(f"Missing collection: {SOURCE_COLLECTION}")

    remove_collection_and_objects(REPAIRED_COLLECTION)
    repaired = ensure_collection(REPAIRED_COLLECTION)

    duplicates = []
    for obj in source.objects:
        if obj.type != 'MESH':
            continue
        dup = obj.copy()
        dup.data = obj.data.copy()
        unlink_all(dup)
        repaired.objects.link(dup)
        dup.name = obj.name.replace("WORK", "REPAIRED")
        duplicates.append(dup)

    if not duplicates:
        raise RuntimeError("No mesh objects found to repair.")

    return repaired, duplicates

def repair_mesh(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    verts_before = len(bm.verts)
    faces_before = len(bm.faces)
    boundary_before = sum(1 for e in bm.edges if e.is_boundary)

    # Merge only nearly coincident vertices. This is intentionally conservative.
    if bm.verts:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=MERGE_DISTANCE)

    boundary_edges = [e for e in bm.edges if e.is_boundary]

    filled_faces = 0
    if boundary_edges:
        result = bmesh.ops.holes_fill(bm, edges=boundary_edges, sides=0)
        filled_faces = len(result.get("faces", []))

    # Recalculate normals after hole filling.
    if bm.faces:
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    bm.normal_update()

    verts_after = len(bm.verts)
    faces_after = len(bm.faces)
    boundary_after = sum(1 for e in bm.edges if e.is_boundary)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for poly in mesh.polygons:
        poly.use_smooth = True

    return {
        "name": obj.name,
        "verts_before": verts_before,
        "verts_after": verts_after,
        "faces_before": faces_before,
        "faces_after": faces_after,
        "boundary_before": boundary_before,
        "boundary_after": boundary_after,
        "filled_faces": filled_faces,
    }

def write_report(stats):
    out_dir = project_root() / "renders" / "meshy_repair_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "Meshy_topology_repair_report.txt"

    lines = ["Meshy Left Candidate Topology Repair Report\n\n"]
    for s in stats:
        lines.append(
            f"{s['name']}\n"
            f"  vertices: {s['verts_before']} -> {s['verts_after']}\n"
            f"  faces: {s['faces_before']} -> {s['faces_after']}\n"
            f"  boundary edges: {s['boundary_before']} -> {s['boundary_after']}\n"
            f"  faces created by hole fill: {s['filled_faces']}\n\n"
        )

    report.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-D] Wrote repair report: {report}")

def set_visibility():
    for name in (
        "CHAR_SackDoll",
        "BASE_Meshy_Source",
        "CHAR_Meshy_Working",
        "CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source",
        "CHAR_Meshy_LeftCandidate_Working",
        "MESHY_CandidateGallery",
        "MESHY_Components",
        "MESHY_GalleryComponents",
    ):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = True
            col.hide_render = True

    repaired = bpy.data.collections.get(REPAIRED_COLLECTION)
    if repaired:
        repaired.hide_viewport = False
        repaired.hide_render = False

def main():
    repaired, duplicates = duplicate_source()
    stats = [repair_mesh(obj) for obj in duplicates]
    write_report(stats)
    set_visibility()

    scene = bpy.context.scene
    scene["active_character_collection"] = REPAIRED_COLLECTION
    scene["meshy_repair_merge_distance"] = MERGE_DISTANCE

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print("[Step01M-D] Conservative topology repair complete.")
    print(f"[Step01M-D] Working repaired collection: {REPAIRED_COLLECTION}")
    print(f"[Step01M-D] Saved: {out}")

if __name__ == "__main__":
    main()
