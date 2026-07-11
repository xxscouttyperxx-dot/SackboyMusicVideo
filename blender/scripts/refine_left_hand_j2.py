import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_PRIORITY = ["HANDREFINE_J1_Working", "HANDREFINE_Working", "F2"]
WORK_COLLECTION = "CHAR_HandRefine_J2"
DIAG_COLLECTION = "DIAG_HandRefine_J2_Cameras"
REPORT_DIR = "hand_refine_j2"


def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)


def pick_source():
    for name in SOURCE_PRIORITY:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            return obj
    raise RuntimeError("No suitable source mesh found for J2 hand refinement.")


def duplicate_working(source):
    col = replace_collection(WORK_COLLECTION)
    dup = source.copy()
    dup.data = source.data.copy()
    dup.name = "HANDREFINE_J2_Working"
    col.objects.link(dup)
    source.hide_render = True
    source.hide_viewport = True
    dup.hide_render = False
    dup.hide_viewport = False
    print(f"[Step01M-J2] Created working duplicate from {source.name}: {dup.name}")
    return dup


def world_bounds_bm(obj, bm):
    mw = obj.matrix_world
    coords = [mw @ v.co for v in bm.verts]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def refine_left_hand(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    mw = obj.matrix_world
    imw = mw.inverted()
    xmin, xmax, ymin, ymax, zmin, zmax = world_bounds_bm(obj, bm)
    w = xmax - xmin
    h = zmax - zmin
    d = ymax - ymin

    # Hand region estimates derived from previous diagnostics.
    hand_back = xmin + w * 0.245
    front_band = xmin + w * 0.11
    wrist_band = xmin + w * 0.34
    y_center = ymin + d * 0.29
    z_center = zmin + h * 0.57
    ry = max(0.18, d * 0.22)
    rz = max(0.18, h * 0.18)

    moved = 0
    report = {
        "source_bounds": (xmin, xmax, ymin, ymax, zmin, zmax),
        "hand_back": hand_back,
        "front_band": front_band,
        "wrist_band": wrist_band,
        "y_center": y_center,
        "z_center": z_center,
        "vertices_total": len(bm.verts),
    }

    for v in bm.verts:
        world = mw @ v.co

        # Primary hand region.
        wx = 1.0 - smoothstep(xmin, hand_back, world.x)
        if wx <= 0.0:
            continue

        dy = world.y - y_center
        dz = world.z - z_center
        ell = (dy / ry) ** 2 + (dz / rz) ** 2
        wyz = max(0.0, 1.0 - ell)
        weight = max(0.35 * wx, wx * wyz)
        if weight <= 0.0:
            continue

        # Hand shortening strongest on the forward edge.
        finger_front = 1.0 - smoothstep(xmin, front_band, world.x)
        world.x += w * (0.020 * weight + 0.040 * finger_front)

        # Palm / finger compacting.
        y_scale = 1.0 - (0.14 * weight)
        # Slightly stronger compaction on the underside.
        z_compact = 0.08 * weight + (0.08 * weight if dz < 0.0 else 0.03 * weight)
        z_scale = 1.0 - z_compact
        world.y = y_center + dy * y_scale
        world.z = z_center + dz * z_scale

        # Gentle finger-lobe preservation: keep top/mid/bottom bumps a touch proud,
        # while reducing the broad in-between mass.
        if world.x <= front_band + w * 0.03:
            lobe_centers = [z_center + 0.055, z_center + 0.0, z_center - 0.055]
            nearest = min(abs(world.z - c) for c in lobe_centers)
            valley = min(1.0, nearest / 0.05)
            # valley=0 near lobe center; valley=1 away between lobes.
            world.y = y_center + (world.y - y_center) * (1.0 - 0.05 * valley * weight)
            world.x += w * 0.005 * (1.0 - valley) * weight

        # Light wrist taper in the transition band.
        if hand_back < world.x < wrist_band:
            t = 1.0 - smoothstep(hand_back, wrist_band, world.x)
            world.y = y_center + (world.y - y_center) * (1.0 - 0.05 * t)
            world.z = z_center + (world.z - z_center) * (1.0 - 0.04 * t)

        v.co = imw @ world
        moved += 1

    # Very mild smoothing only on selected region, one pass.
    deform_verts = [v for v in bm.verts if (mw @ v.co).x <= wrist_band]
    if deform_verts:
        bmesh.ops.smooth_vert(bm, verts=deform_verts, factor=0.12, use_axis_x=False, use_axis_y=True, use_axis_z=True)

    bm.normal_update()
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()

    report["vertices_moved"] = moved
    report["notes"] = [
        "Conservative left-hand only deformation applied.",
        "Hand shortened forward, palm compacted, underside reduced, wrist lightly tapered.",
        "No whole-arm deformation beyond the wrist transition band.",
    ]
    return report


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def render_diagnostics(target):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_percentage = 100
    scene.world.color = (0.04, 0.04, 0.05)

    out_dir = project_root() / 'renders' / REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    xmin, xmax, ymin, ymax, zmin, zmax = world_bounds_for_obj(target)
    w = xmax - xmin
    h = zmax - zmin
    d = max(5.0, h * 2.0)
    hand_focus = Vector((xmin + w * 0.11, ymin + (ymax - ymin) * 0.30, zmin + h * 0.57))
    arm_focus = Vector((xmin + w * 0.22, ymin + (ymax - ymin) * 0.24, zmin + h * 0.60))

    cam_col = replace_collection(DIAG_COLLECTION)

    keep_names = {target.name}
    guide_col = bpy.data.collections.get('GUIDE_LeftHand')
    if guide_col:
        keep_names.update(obj.name for obj in guide_col.objects)

    states = {}
    for obj in bpy.context.scene.objects:
        states[obj.name] = obj.hide_render
        if obj.type == 'MESH':
            obj.hide_render = obj.name not in keep_names
    target.hide_render = False
    if guide_col:
        for obj in guide_col.objects:
            obj.hide_render = False

    views = [
        ('J2_LeftHand_Close', (xmin - w * 0.15, ymin - d * 0.18, zmin + h * 0.58), hand_focus, 76, 'J2_LeftHand_Close.png'),
        ('J2_LeftArm_ThreeQuarter', (xmin + w * 0.18, ymin - d * 0.40, zmin + h * 0.72), arm_focus, 68, 'J2_LeftArm_ThreeQuarter.png'),
        ('J2_Front', (0.0, ymin - d, zmin + h * 0.58), Vector((0.0, (ymin+ymax)/2, zmin + h*0.57)), 60, 'J2_Front.png'),
    ]

    for name, loc, aim, lens, filename in views:
        data = bpy.data.cameras.new(name + '_Data')
        cam = bpy.data.objects.new(name, data)
        cam.data.lens = lens
        cam.location = loc
        look_at(cam, aim)
        cam_col.objects.link(cam)
        scene.camera = cam
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 1280
        scene.render.filepath = str(out_dir / filename)
        bpy.ops.render.render(write_still=True)
        print(f"[Step01M-J2] Rendered {out_dir / filename}")

    for name, state in states.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = state


def world_bounds_for_obj(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def write_report(report, source_name):
    out_dir = project_root() / 'renders' / REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / 'J2_LeftHand_Report.txt'
    bounds = report['source_bounds']
    txt = []
    txt.append('Step01M-J2 Left Hand Geometry Refinement Report\n')
    txt.append('===============================================\n\n')
    txt.append(f'Source object: {source_name}\n')
    txt.append(f'Working object: HANDREFINE_J2_Working\n')
    txt.append(f'Vertices total: {report["vertices_total"]}\n')
    txt.append(f'Vertices moved: {report["vertices_moved"]}\n\n')
    txt.append('World bounds before deformation:\n')
    txt.append(f'xmin={bounds[0]:.6f} xmax={bounds[1]:.6f} ymin={bounds[2]:.6f} ymax={bounds[3]:.6f} zmin={bounds[4]:.6f} zmax={bounds[5]:.6f}\n\n')
    txt.append('Hand region parameters:\n')
    txt.append(f'hand_back={report["hand_back"]:.6f}\n')
    txt.append(f'front_band={report["front_band"]:.6f}\n')
    txt.append(f'wrist_band={report["wrist_band"]:.6f}\n')
    txt.append(f'y_center={report["y_center"]:.6f}\n')
    txt.append(f'z_center={report["z_center"]:.6f}\n\n')
    txt.append('Notes:\n')
    for note in report['notes']:
        txt.append(f'- {note}\n')
    path.write_text(''.join(txt), encoding='utf-8')
    print(f"[Step01M-J2] Wrote report: {path}")


def main():
    source = pick_source()
    target = duplicate_working(source)
    report = refine_left_hand(target)
    render_diagnostics(target)
    write_report(report, source.name)
    out = project_root() / 'blender' / 'sackboy_scene.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J2] Saved refined hand pass: {out}")


if __name__ == '__main__':
    main()
