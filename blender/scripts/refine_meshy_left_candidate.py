import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_COLLECTION = "CHAR_Meshy_LeftCandidate_Repaired"
OUTPUT_COLLECTION = "CHAR_Meshy_LeftCandidate_Refined"

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
        raise RuntimeError(f"Missing collection: {SOURCE_COLLECTION}")

    remove_collection_and_objects(OUTPUT_COLLECTION)
    out_col = ensure_collection(OUTPUT_COLLECTION)

    duplicates = []
    for obj in source.objects:
        if obj.type != 'MESH':
            continue
        dup = obj.copy()
        dup.data = obj.data.copy()
        unlink_all(dup)
        out_col.objects.link(dup)
        dup.name = obj.name.replace("REPAIRED", "REFINED")
        duplicates.append(dup)

    if not duplicates:
        raise RuntimeError("No repaired mesh objects available.")

    return out_col, duplicates

def local_bounds(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def smooth_selected(obj, selected_indices, iterations=4, factor=0.42):
    if not selected_indices:
        return 0

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    verts = [bm.verts[i] for i in selected_indices if i < len(bm.verts)]
    if verts:
        for _ in range(iterations):
            bmesh.ops.smooth_vert(
                bm,
                verts=verts,
                factor=factor,
                use_axis_x=True,
                use_axis_y=True,
                use_axis_z=True,
            )

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(verts)

def refine_mesh(obj):
    xmin, xmax, ymin, ymax, zmin, zmax = local_bounds(obj)
    width = xmax - xmin
    depth = ymax - ymin
    height = zmax - zmin

    def nx(x): return (x - xmin) / max(width, 1e-9)
    def ny(y): return (y - ymin) / max(depth, 1e-9)
    def nz(z): return (z - zmin) / max(height, 1e-9)

    # The imported candidate faces toward negative local Y in this project.
    # Use normalized coordinates to keep the edit proportional to the mesh.
    hand_count = 0
    face_count = 0
    stomach_count = 0
    seam_indices = []
    stomach_indices = []

    for i, v in enumerate(obj.data.vertices):
        x, y, z = v.co.x, v.co.y, v.co.z
        X, Y, Z = nx(x), ny(y), nz(z)

        # 1) HAND / FINGER REDUCTION
        # Distal X zones near the T-pose hand ends, upper-mid body height.
        is_left_hand = X < 0.105 and 0.46 < Z < 0.73
        is_right_hand = X > 0.895 and 0.46 < Z < 0.73

        if is_left_hand or is_right_hand:
            side = -1.0 if is_left_hand else 1.0
            center_x = xmin + (0.075 if is_left_hand else 0.925) * width
            center_y = ymin + 0.50 * depth
            center_z = zmin + 0.585 * height

            # Conservative local scale toward palm center.
            v.co.x = center_x + (v.co.x - center_x) * 0.86
            v.co.y = center_y + (v.co.y - center_y) * 0.88
            v.co.z = center_z + (v.co.z - center_z) * 0.90
            hand_count += 1

        # 2) LOCAL CENTER-FACE PROTRUSION REDUCTION
        # Only the central lower-front face region; preserve forehead, cheeks, and rear skull.
        central_x = abs(X - 0.5) < 0.26
        head_zone = Z > 0.72
        forward_zone = Y < 0.24
        lower_face = Z < 0.91

        if central_x and head_zone and forward_zone and lower_face:
            # Push only the muzzle region backward toward the head.
            # Strongest at the center and frontmost portion.
            center_weight = max(0.0, 1.0 - abs(X - 0.5) / 0.26)
            front_weight = max(0.0, (0.24 - Y) / 0.24)
            vertical_weight = max(0.0, 1.0 - abs(Z - 0.81) / 0.10)
            w = center_weight * front_weight * vertical_weight
            v.co.y += depth * 0.075 * w
            face_count += 1

        # 3) BODY CONNECTION CLEANUP
        # Neck seam and shoulder/arm connection zones.
        neck_zone = (0.37 < X < 0.63 and 0.60 < Z < 0.73)
        left_shoulder = (0.20 < X < 0.39 and 0.51 < Z < 0.68)
        right_shoulder = (0.61 < X < 0.80 and 0.51 < Z < 0.68)
        if neck_zone or left_shoulder or right_shoulder:
            seam_indices.append(i)

        # 4) SMALL LOWER-LEFT STOMACH DIMPLE / WRINKLE
        # Viewer-left corresponds to local X below center. Keep region very small.
        stomach_zone = (
            0.39 < X < 0.49 and
            Y < 0.30 and
            0.34 < Z < 0.49
        )
        if stomach_zone:
            # Slightly relax front surface outward before smoothing.
            front_target = ymin + 0.18 * depth
            if v.co.y > front_target:
                v.co.y += (front_target - v.co.y) * 0.18
            stomach_indices.append(i)
            stomach_count += 1

    seam_smoothed = smooth_selected(obj, seam_indices, iterations=3, factor=0.28)
    stomach_smoothed = smooth_selected(obj, stomach_indices, iterations=5, factor=0.46)

    # Recalculate normals after local deformation.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if bm.faces:
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    for poly in obj.data.polygons:
        poly.use_smooth = True

    return {
        "object": obj.name,
        "hand_vertices_scaled": hand_count,
        "face_vertices_adjusted": face_count,
        "seam_vertices_smoothed": seam_smoothed,
        "stomach_vertices_smoothed": stomach_smoothed,
    }

def add_mouth_guide(out_col, obj):
    # Non-destructive guide only. No boolean cut in this pass.
    # This lets us inspect position before carving a true mouth cavity.
    xmin, xmax, ymin, ymax, zmin, zmax = local_bounds(obj)
    width = xmax - xmin
    depth = ymax - ymin
    height = zmax - zmin

    curve_data = bpy.data.curves.new("MOUTH_CUT_GUIDE_Data", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 24
    curve_data.bevel_depth = width * 0.0035
    curve_data.fill_mode = 'FULL'

    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(4)

    coords = [
        (-width*0.105, 0.0,  height*0.014),
        (-width*0.055, 0.0, -height*0.004),
        ( 0.0,         0.0, -height*0.012),
        ( width*0.055, 0.0, -height*0.004),
        ( width*0.105, 0.0,  height*0.014),
    ]

    for bp, co in zip(spline.bezier_points, coords):
        bp.co = co
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    guide = bpy.data.objects.new("MOUTH_CUT_GUIDE", curve_data)

    # Place just in front of the lower-center face.
    guide.location = (
        (xmin + xmax) * 0.5,
        ymin - depth * 0.006,
        zmin + height * 0.795,
    )
    guide.rotation_euler = (1.5708, 0.0, 0.0)

    mat = bpy.data.materials.get("MAT_MouthGuide")
    if mat is None:
        mat = bpy.data.materials.new("MAT_MouthGuide")
        mat.diffuse_color = (0.08, 0.02, 0.02, 1.0)
    curve_data.materials.append(mat)

    out_col.objects.link(guide)
    return guide

def write_report(stats):
    out_dir = project_root() / "renders" / "meshy_refinement_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "Meshy_shape_cleanup_report.txt"

    lines = ["Meshy Shape Cleanup Report\n\n"]
    for s in stats:
        lines.append(
            f"{s['object']}\n"
            f"  hand vertices scaled: {s['hand_vertices_scaled']}\n"
            f"  face vertices adjusted: {s['face_vertices_adjusted']}\n"
            f"  seam vertices smoothed: {s['seam_vertices_smoothed']}\n"
            f"  stomach vertices smoothed: {s['stomach_vertices_smoothed']}\n\n"
        )
    lines.append("MOUTH_CUT_GUIDE added as non-destructive placement guide only.\n")
    report.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-E] Wrote cleanup report: {report}")

def set_visibility():
    for name in (
        "CHAR_SackDoll",
        "BASE_Meshy_Source",
        "CHAR_Meshy_Working",
        "CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source",
        "CHAR_Meshy_LeftCandidate_Working",
        "CHAR_Meshy_LeftCandidate_Repaired",
        "MESHY_CandidateGallery",
        "MESHY_Components",
        "MESHY_GalleryComponents",
    ):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = True
            col.hide_render = True

    refined = bpy.data.collections.get(OUTPUT_COLLECTION)
    if refined:
        refined.hide_viewport = False
        refined.hide_render = False

def main():
    out_col, objects = duplicate_source()
    stats = [refine_mesh(obj) for obj in objects]

    # Guide is attached to first mesh object's coordinate frame.
    add_mouth_guide(out_col, objects[0])
    write_report(stats)
    set_visibility()

    scene = bpy.context.scene
    scene["active_character_collection"] = OUTPUT_COLLECTION
    scene["shape_cleanup_version"] = "Step01M-E"

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print("[Step01M-E] Shape cleanup complete.")
    print(f"[Step01M-E] Active collection: {OUTPUT_COLLECTION}")
    print(f"[Step01M-E] Saved: {out}")

if __name__ == "__main__":
    main()
