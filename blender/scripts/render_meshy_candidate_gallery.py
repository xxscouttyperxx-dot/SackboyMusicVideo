import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SRC_COLLECTION = "CHAR_Meshy_Working"
TEMP_COLLECTION = "MESHY_GalleryTemp"
COMPONENT_COLLECTION = "MESHY_GalleryComponents"
GALLERY_COLLECTION = "MESHY_CandidateGallery"

MIN_HEIGHT = 0.65
MIN_UPRIGHT_RATIO = 0.55
MAX_CANDIDATES = 10

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
    for name in (TEMP_COLLECTION, COMPONENT_COLLECTION, GALLERY_COLLECTION):
        remove_collection_and_objects(name)
    return (
        ensure_collection(TEMP_COLLECTION),
        ensure_collection(COMPONENT_COLLECTION),
        ensure_collection(GALLERY_COLLECTION),
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
        raise RuntimeError(f"No mesh objects found in {SRC_COLLECTION}.")
    return dupes

def join_or_use_single(dupes):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in dupes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = dupes[0]

    if len(dupes) > 1:
        bpy.ops.object.join()
        return bpy.context.view_layer.objects.active
    return dupes[0]

def separate_loose(joined, component_col):
    bpy.ops.object.select_all(action='DESELECT')
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')

    parts = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not parts:
        parts = [joined]

    for i, obj in enumerate(parts):
        obj.name = f"MESHY_GALLERY_COMPONENT_{i:03d}"
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
    dist_xy = (cx ** 2 + cy ** 2) ** 0.5
    score = (h ** 2.0) * max(0.1, upright_ratio) * (1.0 / (1.0 + 0.15 * dist_xy))
    return {
        "name": obj.name,
        "w": w, "d": d, "h": h,
        "cx": cx, "cy": cy, "cz": cz,
        "upright_ratio": upright_ratio,
        "score": score,
        "object": obj,
    }

def choose_candidates(stats):
    pool = [s for s in stats if s["h"] >= MIN_HEIGHT and s["upright_ratio"] >= MIN_UPRIGHT_RATIO]
    if not pool:
        pool = sorted(stats, key=lambda x: x["score"], reverse=True)[:MAX_CANDIDATES]
    else:
        pool = sorted(pool, key=lambda x: x["score"], reverse=True)[:MAX_CANDIDATES]
    return pool

def duplicate_to_gallery(candidates, gallery_col):
    gallery = []
    for idx, s in enumerate(candidates):
        obj = s["object"]
        dup = obj.copy()
        if obj.data:
            dup.data = obj.data.copy()
        unlink_from_all(dup)
        gallery_col.objects.link(dup)
        dup.name = f"MESHY_CANDIDATE_{idx:02d}"

        xmin, xmax, ymin, ymax, zmin, zmax = object_bounds_world(dup)
        cx = (xmin + xmax) * 0.5
        cy = (ymin + ymax) * 0.5
        dup.location.x -= cx
        dup.location.y -= cy
        dup.location.z -= zmin

        mat = bpy.data.materials.get("MAT_MeshyCandidateNeutral")
        if mat is None:
            mat = bpy.data.materials.new("MAT_MeshyCandidateNeutral")
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

        gallery.append((idx, dup, s))
    return gallery

def write_report(candidates):
    out_dir = project_root() / "renders" / "meshy_candidate_gallery"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "Meshy_candidate_gallery_report.txt"
    lines = []
    lines.append("Meshy Candidate Gallery Report\n")
    lines.append("Use the candidate number (00, 01, 02...) when discussing the best model.\n\n")
    for idx, s in enumerate(candidates):
        lines.append(
            f"Candidate {idx:02d} -> {s['name']} | score={s['score']:.4f} | "
            f"h={s['h']:.4f} w={s['w']:.4f} d={s['d']:.4f} | "
            f"upright={s['upright_ratio']:.4f} | center=({s['cx']:.4f},{s['cy']:.4f},{s['cz']:.4f})\n"
        )
    report.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-B] Wrote candidate report: {report}")

def hide_non_gallery():
    for name in ("ENV_ParkingLot", "LGT_Night", "CAM_Rigs", "CHAR_SackDoll", "BASE_Meshy_Source", "CHAR_Meshy_Working", TEMP_COLLECTION, COMPONENT_COLLECTION, "CHAR_Meshy_Isolated"):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = True
            col.hide_render = True
    gallery = bpy.data.collections.get(GALLERY_COLLECTION)
    if gallery:
        gallery.hide_viewport = False
        gallery.hide_render = False

def setup_studio():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.world.color = (0.92, 0.92, 0.94)

    studio = ensure_collection("DIAG_Meshy_Candidate_Studio")

    for name in ("CAND_DIAG_Floor","CAND_DIAG_Key","CAND_DIAG_Fill","CAND_DIAG_Rim","CAND_DIAG_Camera"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor = bpy.context.object
    floor.name = "CAND_DIAG_Floor"
    floor.scale = (7,7,7)
    mat = bpy.data.materials.get("MAT_CandidateDiagFloor") or bpy.data.materials.new("MAT_CandidateDiagFloor")
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

    area("CAND_DIAG_Key", (4,-4,5), 1900, 3.5)
    area("CAND_DIAG_Fill", (-4,-2,3), 900, 4.0)
    area("CAND_DIAG_Rim", (0,4,4), 1000, 3.5)

    cam_data = bpy.data.cameras.get("CAND_DIAG_Camera_Data") or bpy.data.cameras.new("CAND_DIAG_Camera_Data")
    cam = bpy.data.objects.new("CAND_DIAG_Camera", cam_data)
    studio.objects.link(cam)
    cam.data.lens = 55
    return cam

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def render_candidate(cam, idx, obj):
    scene = bpy.context.scene
    # Hide all gallery candidates except the one being rendered
    gallery = bpy.data.collections.get(GALLERY_COLLECTION)
    for other in gallery.objects:
        other.hide_render = (other.name != obj.name)
        other.hide_viewport = (other.name != obj.name)

    xmin, xmax, ymin, ymax, zmin, zmax = object_bounds_world(obj)
    center = Vector(((xmin+xmax)/2, (ymin+ymax)/2, (zmin+zmax)/2))
    height = zmax - zmin
    distance = max(4.6, height * 2.2)

    out_dir = project_root() / "renders" / "meshy_candidate_gallery"
    out_dir.mkdir(parents=True, exist_ok=True)

    views = {
        "Front": (0, -distance, center.z),
        "ThreeQuarterFront": (distance*0.78, -distance*0.78, center.z+0.10),
    }

    for label, loc in views.items():
        cam.location = loc
        look_at(cam, center)
        scene.camera = cam
        path = out_dir / f"Candidate_{idx:02d}_{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print(f"[Step01M-B] Rendered {path}")

def main():
    temp_col, component_col, gallery_col = ensure_clean_collections()
    dupes = duplicate_source_meshes(temp_col)
    joined = join_or_use_single(dupes)
    parts = separate_loose(joined, component_col)

    stats = [component_stats(obj) for obj in component_col.objects if obj.type == 'MESH']
    if not stats:
        raise RuntimeError("No components available for candidate gallery.")

    candidates = choose_candidates(stats)
    write_report(candidates)
    gallery = duplicate_to_gallery(candidates, gallery_col)

    hide_non_gallery()
    cam = setup_studio()

    for idx, obj, stat in gallery:
        render_candidate(cam, idx, obj)

    scene = bpy.context.scene
    scene["meshy_candidate_gallery_count"] = len(gallery)

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print(f"[Step01M-B] Candidate gallery count: {len(gallery)}")
    print(f"[Step01M-B] Saved: {out}")

if __name__ == "__main__":
    main()
