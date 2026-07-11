import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SRC_COLLECTION = "CHAR_Meshy_Working"
SOURCE_LOCKED = "BASE_Meshy_Source"
TEMP_COLLECTION = "MESHY_TempAnalysis"
COMPONENT_COLLECTION = "MESHY_Components"
ISOLATED_COLLECTION = "CHAR_Meshy_Isolated"

def remove_collection_and_objects(name):
    col = bpy.data.collections.get(name)
    if not col:
        return
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def unlink_from_all(obj):
    for col in list(obj.users_collection):
        try:
            col.objects.unlink(obj)
        except:
            pass

def ensure_clean_collections():
    for name in (TEMP_COLLECTION, COMPONENT_COLLECTION, ISOLATED_COLLECTION):
        remove_collection_and_objects(name)
    return (
        ensure_collection(TEMP_COLLECTION),
        ensure_collection(COMPONENT_COLLECTION),
        ensure_collection(ISOLATED_COLLECTION),
    )

def object_bounds_world(obj):
    xs, ys, zs = [], [], []
    for corner in obj.bound_box:
        co = obj.matrix_world @ Vector(corner)
        xs.append(co.x); ys.append(co.y); zs.append(co.z)
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def duplicate_source_meshes(temp_col):
    src = bpy.data.collections.get(SRC_COLLECTION)
    if not src:
        raise RuntimeError(f"Missing collection: {SRC_COLLECTION}")

    dupes = []
    for obj in src.objects:
        if obj.type != 'MESH':
            continue
        dup = obj.copy()
        if obj.data:
            dup.data = obj.data.copy()
        unlink_from_all(dup)
        temp_col.objects.link(dup)
        dupes.append(dup)
    if not dupes:
        raise RuntimeError("No mesh objects found in CHAR_Meshy_Working.")
    return dupes

def join_and_separate_loose(dupes, component_col):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in dupes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = dupes[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = "MESHY_JOINED_ANALYSIS"

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')

    parts = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not parts:
        # fallback: sometimes Blender leaves only active object selected
        parts = [joined]

    for i, obj in enumerate(parts):
        obj.name = f"MESHY_COMPONENT_{i:03d}"
        unlink_from_all(obj)
        component_col.objects.link(obj)

    return parts

def component_stats(obj):
    xmin, xmax, ymin, ymax, zmin, zmax = object_bounds_world(obj)
    w = xmax - xmin
    d = ymax - ymin
    h = zmax - zmin
    cx = (xmin + xmax) * 0.5
    cy = (ymin + ymax) * 0.5
    cz = (zmin + zmax) * 0.5
    footprint = max(w, d, 1e-6)
    upright_ratio = h / footprint
    volume_like = max(w * d * h, 1e-9)
    dist_xy = (cx ** 2 + cy ** 2) ** 0.5
    ground_penalty = abs(zmin)

    # Heuristic: prefer upright human-like figures with substantial height.
    score = (
        (h ** 2.0)
        * max(0.1, upright_ratio)
        * (1.0 / (1.0 + 0.15 * dist_xy))
        * (1.0 / (1.0 + 0.7 * ground_penalty))
    )
    return {
        "name": obj.name,
        "w": w, "d": d, "h": h,
        "cx": cx, "cy": cy, "cz": cz,
        "zmin": zmin, "zmax": zmax,
        "upright_ratio": upright_ratio,
        "dist_xy": dist_xy,
        "score": score,
        "object": obj,
    }

def write_report(stats):
    out = project_root() / "renders" / "meshy_baseline_diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    report = out / "Meshy_component_report.txt"
    lines = []
    lines.append("Meshy Component Report\n")
    lines.append("Sorted by descending heuristic score.\n\n")
    for idx, s in enumerate(sorted(stats, key=lambda x: x["score"], reverse=True), start=1):
        lines.append(
            f"{idx:02d}. {s['name']} | score={s['score']:.4f} | "
            f"h={s['h']:.4f} w={s['w']:.4f} d={s['d']:.4f} | "
            f"upright={s['upright_ratio']:.4f} | "
            f"center=({s['cx']:.4f},{s['cy']:.4f},{s['cz']:.4f}) | "
            f"zmin={s['zmin']:.4f}\n"
        )
    report.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-A] Wrote component report: {report}")

def choose_best_component(stats):
    # Prefer candidates with meaningful height and upright proportion.
    filtered = [s for s in stats if s["h"] > 0.8 and s["upright_ratio"] > 1.0]
    pool = filtered if filtered else stats
    best = sorted(pool, key=lambda x: x["score"], reverse=True)[0]
    return best

def duplicate_to_isolated(best_obj, isolated_col):
    dup = best_obj.copy()
    if best_obj.data:
        dup.data = best_obj.data.copy()
    unlink_from_all(dup)
    isolated_col.objects.link(dup)
    dup.name = "MESHY_ISOLATED_BASE"

    # Center and ground it.
    xmin, xmax, ymin, ymax, zmin, zmax = object_bounds_world(dup)
    cx = (xmin + xmax) * 0.5
    cy = (ymin + ymax) * 0.5

    dup.location.x -= cx
    dup.location.y -= cy
    dup.location.z -= zmin

    bpy.context.view_layer.update()

    # Neutral material for diagnostics.
    mat = bpy.data.materials.get("MAT_MeshyIsolatedNeutral")
    if mat is None:
        mat = bpy.data.materials.new("MAT_MeshyIsolatedNeutral")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.84, 0.84, 0.86, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.68

    if hasattr(dup.data, "materials"):
        dup.data.materials.clear()
        dup.data.materials.append(mat)

    for poly in dup.data.polygons:
        poly.use_smooth = True

    return dup

def set_visibility():
    for name in (SRC_COLLECTION, SOURCE_LOCKED, TEMP_COLLECTION):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = True
            col.hide_render = True

    comp = bpy.data.collections.get(COMPONENT_COLLECTION)
    if comp:
        comp.hide_viewport = True
        comp.hide_render = True

    iso = bpy.data.collections.get(ISOLATED_COLLECTION)
    if iso:
        iso.hide_viewport = False
        iso.hide_render = False

def main():
    temp_col, component_col, isolated_col = ensure_clean_collections()
    dupes = duplicate_source_meshes(temp_col)
    parts = join_and_separate_loose(dupes, component_col)

    stats = [component_stats(obj) for obj in component_col.objects if obj.type == 'MESH']
    if not stats:
        raise RuntimeError("No components available after loose-part separation.")

    write_report(stats)
    best = choose_best_component(stats)
    isolated = duplicate_to_isolated(best["object"], isolated_col)

    set_visibility()

    scene = bpy.context.scene
    scene["meshy_isolated_from"] = best["name"]
    scene["active_character_collection"] = ISOLATED_COLLECTION

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print(f"[Step01M-A] Best component chosen: {best['name']}")
    print(f"[Step01M-A] Best component stats: h={best['h']:.4f} w={best['w']:.4f} d={best['d']:.4f} upright={best['upright_ratio']:.4f}")
    print(f"[Step01M-A] Isolated object saved as: {isolated.name}")
    print(f"[Step01M-A] Saved: {out}")

if __name__ == "__main__":
    main()
