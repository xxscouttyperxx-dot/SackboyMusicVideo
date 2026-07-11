import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_COLLECTION = "CHAR_Meshy_LeftCandidate_Refined"
OUTPUT_COLLECTION = "CHAR_Meshy_LeftCandidate_Structural"

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
        dup.name = obj.name.replace("REFINED", "STRUCTURAL")
        duplicates.append(dup)

    if not duplicates:
        raise RuntimeError("No refined mesh objects found.")
    return out_col, duplicates

def local_bounds(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def smooth_selected(obj, selected_indices, iterations=4, factor=0.35):
    if not selected_indices:
        return 0
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    verts = [bm.verts[i] for i in selected_indices if i < len(bm.verts)]
    for _ in range(iterations):
        if verts:
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

def remove_nonlargest_components(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    unvisited = set(v.index for v in bm.verts)
    components = []

    while unvisited:
        start = bm.verts[next(iter(unvisited))]
        stack = [start]
        comp = []
        while stack:
            v = stack.pop()
            if v.index not in unvisited:
                continue
            unvisited.remove(v.index)
            comp.append(v)
            for e in v.link_edges:
                ov = e.other_vert(v)
                if ov.index in unvisited:
                    stack.append(ov)
        components.append(comp)

    removed = 0
    before = len(components)

    if len(components) > 1:
        largest = max(components, key=len)
        to_delete = []
        for comp in components:
            if comp is largest:
                continue
            to_delete.extend(comp)
        if to_delete:
            removed = len(to_delete)
            bmesh.ops.delete(bm, geom=to_delete, context='VERTS')

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return before, removed

def refine_mesh(obj):
    xmin, xmax, ymin, ymax, zmin, zmax = local_bounds(obj)
    width = xmax - xmin
    depth = ymax - ymin
    height = zmax - zmin
    cx = (xmin + xmax) * 0.5
    cy = (ymin + ymax) * 0.5

    def nx(x): return (x - xmin) / max(width, 1e-9)
    def ny(y): return (y - ymin) / max(depth, 1e-9)
    def nz(z): return (z - zmin) / max(height, 1e-9)

    face_indices = []
    left_hand_indices = []
    right_hand_indices = []
    neck_indices = []
    shoulder_indices = []
    hip_indices = []
    stomach_indices = []

    head_lift_count = 0
    hand_count = 0
    face_count = 0
    stomach_count = 0

    for i, v in enumerate(obj.data.vertices):
        x, y, z = v.co.x, v.co.y, v.co.z
        X, Y, Z = nx(x), ny(y), nz(z)

        # 1) HEAD LIFT / LIGHTER NECK CREATION
        # Gently raise head mass to reveal more neck while preserving overall head shape.
        if Z > 0.71:
            center_weight = max(0.0, 1.0 - abs(X - 0.5) / 0.42)
            z_weight = max(0.0, (Z - 0.71) / 0.29)
            lift = height * 0.030 * (0.35 + 0.65 * z_weight) * (0.75 + 0.25 * center_weight)
            v.co.z += lift
            head_lift_count += 1

        # 2) NECK THINNING / DEEPER JOINT CUT
        neck_zone = (0.41 < X < 0.59 and 0.55 < Z < 0.73)
        if neck_zone:
            neck_center_x = cx
            neck_center_y = ymin + depth * 0.50
            # pull inward to make neck slimmer
            v.co.x = neck_center_x + (v.co.x - neck_center_x) * 0.72
            v.co.y = neck_center_y + (v.co.y - neck_center_y) * 0.84
            neck_indices.append(i)

        # 3) SHOULDER / ARM JOINT THINNING
        left_shoulder = (0.19 < X < 0.39 and 0.50 < Z < 0.67)
        right_shoulder = (0.61 < X < 0.81 and 0.50 < Z < 0.67)
        if left_shoulder or right_shoulder:
            target_x = cx - width * 0.20 if left_shoulder else cx + width * 0.20
            target_y = ymin + depth * 0.50
            v.co.x = target_x + (v.co.x - target_x) * 0.86
            v.co.y = target_y + (v.co.y - target_y) * 0.88
            shoulder_indices.append(i)

        # 4) HIP / LEG JOINT THINNING
        left_hip = (0.31 < X < 0.46 and 0.20 < Z < 0.40)
        right_hip = (0.54 < X < 0.69 and 0.20 < Z < 0.40)
        if left_hip or right_hip:
            target_x = cx - width * 0.11 if left_hip else cx + width * 0.11
            target_y = ymin + depth * 0.51
            v.co.x = target_x + (v.co.x - target_x) * 0.86
            v.co.y = target_y + (v.co.y - target_y) * 0.90
            hip_indices.append(i)

        # 5) STRONGER HAND / FINGER REDUCTION
        is_left_hand = X < 0.125 and 0.44 < Z < 0.73
        is_right_hand = X > 0.875 and 0.44 < Z < 0.73
        if is_left_hand or is_right_hand:
            center_x = xmin + (0.078 if is_left_hand else 0.922) * width
            center_y = ymin + 0.50 * depth
            center_z = zmin + 0.585 * height
            v.co.x = center_x + (v.co.x - center_x) * 0.73
            v.co.y = center_y + (v.co.y - center_y) * 0.76
            v.co.z = center_z + (v.co.z - center_z) * 0.82
            hand_count += 1
            if is_left_hand:
                left_hand_indices.append(i)
            else:
                right_hand_indices.append(i)

        # 6) STRONGER LOCAL FACE PROTRUSION REDUCTION
        central_x = abs(X - 0.5) < 0.25
        head_zone = Z > 0.73
        forward_zone = Y < 0.26
        lower_face = Z < 0.915
        if central_x and head_zone and forward_zone and lower_face:
            center_weight = max(0.0, 1.0 - abs(X - 0.5) / 0.25)
            front_weight = max(0.0, (0.26 - Y) / 0.26)
            vertical_weight = max(0.0, 1.0 - abs(Z - 0.82) / 0.12)
            w = center_weight * front_weight * vertical_weight
            v.co.y += depth * 0.110 * w
            face_count += 1
            face_indices.append(i)

        # 7) STOMACH LOWER-LEFT WRINKLE / DIMPLE
        stomach_zone = (0.39 < X < 0.49 and Y < 0.31 and 0.34 < Z < 0.50)
        if stomach_zone:
            front_target = ymin + 0.19 * depth
            if v.co.y > front_target:
                v.co.y += (front_target - v.co.y) * 0.24
            stomach_indices.append(i)
            stomach_count += 1

    # Smoothing passes
    left_hand_smoothed = smooth_selected(obj, left_hand_indices, iterations=6, factor=0.50)
    right_hand_smoothed = smooth_selected(obj, right_hand_indices, iterations=5, factor=0.42)
    face_smoothed = smooth_selected(obj, face_indices, iterations=4, factor=0.24)
    neck_smoothed = smooth_selected(obj, neck_indices, iterations=5, factor=0.36)
    shoulder_smoothed = smooth_selected(obj, shoulder_indices, iterations=4, factor=0.30)
    hip_smoothed = smooth_selected(obj, hip_indices, iterations=4, factor=0.28)
    stomach_smoothed = smooth_selected(obj, stomach_indices, iterations=6, factor=0.50)

    # Remove disconnected junk if any exists after prior repairs.
    components_before, loose_removed = remove_nonlargest_components(obj)

    # Normals + smooth shading
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
        "head_vertices_lifted": head_lift_count,
        "hand_vertices_scaled": hand_count,
        "face_vertices_adjusted": face_count,
        "stomach_vertices_adjusted": stomach_count,
        "left_hand_smoothed": left_hand_smoothed,
        "right_hand_smoothed": right_hand_smoothed,
        "face_smoothed": face_smoothed,
        "neck_smoothed": neck_smoothed,
        "shoulder_smoothed": shoulder_smoothed,
        "hip_smoothed": hip_smoothed,
        "stomach_smoothed": stomach_smoothed,
        "components_before": components_before,
        "loose_vertices_removed": loose_removed,
    }

def add_mouth_guide(out_col, obj):
    xmin, xmax, ymin, ymax, zmin, zmax = local_bounds(obj)
    width = xmax - xmin
    depth = ymax - ymin
    height = zmax - zmin

    curve_data = bpy.data.curves.new("MOUTH_CUT_GUIDE_STRUCT_Data", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 24
    curve_data.bevel_depth = width * 0.0032
    curve_data.fill_mode = 'FULL'

    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(4)
    coords = [
        (-width*0.110, 0.0,  height*0.016),
        (-width*0.060, 0.0, -height*0.004),
        ( 0.0,         0.0, -height*0.014),
        ( width*0.060, 0.0, -height*0.004),
        ( width*0.110, 0.0,  height*0.016),
    ]
    for bp, co in zip(spline.bezier_points, coords):
        bp.co = co
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    guide = bpy.data.objects.new("MOUTH_CUT_GUIDE_STRUCT", curve_data)
    guide.location = (
        (xmin + xmax) * 0.5,
        ymin - depth * 0.006,
        zmin + height * 0.805,
    )
    guide.rotation_euler = (1.5708, 0.0, 0.0)

    mat = bpy.data.materials.get("MAT_MouthGuideStruct")
    if mat is None:
        mat = bpy.data.materials.new("MAT_MouthGuideStruct")
        mat.diffuse_color = (0.08, 0.02, 0.02, 1.0)
    curve_data.materials.append(mat)

    out_col.objects.link(guide)
    return guide

def write_report(stats):
    out_dir = project_root() / "renders" / "meshy_structural_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "Meshy_structural_refinement_report.txt"

    lines = ["Meshy Structural Refinement Report\n\n"]
    for s in stats:
        lines.append(
            f"{s['object']}\n"
            f"  head vertices lifted: {s['head_vertices_lifted']}\n"
            f"  hand vertices scaled: {s['hand_vertices_scaled']}\n"
            f"  face vertices adjusted: {s['face_vertices_adjusted']}\n"
            f"  stomach vertices adjusted: {s['stomach_vertices_adjusted']}\n"
            f"  left hand smoothed verts: {s['left_hand_smoothed']}\n"
            f"  right hand smoothed verts: {s['right_hand_smoothed']}\n"
            f"  face smoothed verts: {s['face_smoothed']}\n"
            f"  neck smoothed verts: {s['neck_smoothed']}\n"
            f"  shoulder smoothed verts: {s['shoulder_smoothed']}\n"
            f"  hip smoothed verts: {s['hip_smoothed']}\n"
            f"  stomach smoothed verts: {s['stomach_smoothed']}\n"
            f"  connected components before cleanup: {s['components_before']}\n"
            f"  loose vertices removed: {s['loose_vertices_removed']}\n\n"
        )
    lines.append("MOUTH_CUT_GUIDE_STRUCT added as non-destructive mouth-cavity placement guide.\n")
    report.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-F] Wrote structural report: {report}")

def set_visibility():
    for name in (
        "CHAR_SackDoll",
        "BASE_Meshy_Source",
        "CHAR_Meshy_Working",
        "CHAR_Meshy_Isolated",
        "BASE_Meshy_LeftCandidate_Source",
        "CHAR_Meshy_LeftCandidate_Working",
        "CHAR_Meshy_LeftCandidate_Repaired",
        "CHAR_Meshy_LeftCandidate_Refined",
        "MESHY_CandidateGallery",
        "MESHY_Components",
        "MESHY_GalleryComponents",
    ):
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = True
            col.hide_render = True
    out = bpy.data.collections.get(OUTPUT_COLLECTION)
    if out:
        out.hide_viewport = False
        out.hide_render = False

def main():
    out_col, objs = duplicate_source()
    stats = [refine_mesh(obj) for obj in objs]
    add_mouth_guide(out_col, objs[0])
    write_report(stats)
    set_visibility()

    scene = bpy.context.scene
    scene["active_character_collection"] = OUTPUT_COLLECTION
    scene["shape_cleanup_version"] = "Step01M-F"

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))

    print("[Step01M-F] Structural refinement complete.")
    print(f"[Step01M-F] Active collection: {OUTPUT_COLLECTION}")
    print(f"[Step01M-F] Saved: {out}")

if __name__ == "__main__":
    main()
