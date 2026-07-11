import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_NAME = "HANDREFINE_Working"
WORK_COLLECTION = "CHAR_HandRefine_J1"
GUIDE_COLLECTION = "GUIDE_LeftHand"
CAM_COLLECTION = "DIAG_LeftHandGuide_Cameras"

def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def world_bounds(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def duplicate_working(source):
    col = replace_collection(WORK_COLLECTION)
    dup = source.copy()
    dup.data = source.data.copy()
    dup.name = "HANDREFINE_J1_Working"
    col.objects.link(dup)

    source.hide_render = True
    source.hide_viewport = True
    dup.hide_render = False
    dup.hide_viewport = False

    print(f"[Step01M-J1-v2] Created working duplicate: {dup.name}")
    return dup

def create_emissive_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.05, 0.65, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 2.0
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat

def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

def add_wire_modifier(obj, thickness=0.008):
    mod = obj.modifiers.new(name="GuideWire", type='WIREFRAME')
    mod.thickness = thickness
    mod.use_replace = True
    mod.use_even_offset = True

def make_guide_hand(target):
    guide_col = replace_collection(GUIDE_COLLECTION)
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(target)
    w=xmax-xmin
    h=zmax-zmin

    palm_center = Vector((
        xmin + w*0.11,
        ymin + (ymax-ymin)*0.30,
        zmin + h*0.57
    ))
    guide_origin = palm_center + Vector((-0.05, 0.18, 0.00))

    created = []

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24, ring_count=12,
        radius=0.115,
        location=guide_origin
    )
    palm = bpy.context.object
    palm.name = "GUIDE_Palm"
    palm.scale = (1.05, 0.82, 0.95)
    created.append(palm)

    offsets = [
        Vector((-0.085, 0.00, 0.052)),
        Vector((-0.110, 0.00, 0.000)),
        Vector((-0.085, 0.00, -0.052)),
    ]
    finger_scales = [
        (1.15, 0.78, 0.72),
        (1.28, 0.78, 0.72),
        (1.10, 0.78, 0.72),
    ]

    for i, (off, scale) in enumerate(zip(offsets, finger_scales), start=1):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=20, ring_count=10,
            radius=0.060,
            location=guide_origin + off
        )
        finger = bpy.context.object
        finger.name = f"GUIDE_Finger_{i:02d}"
        finger.scale = scale
        created.append(finger)

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=20, ring_count=10,
        radius=0.050,
        location=guide_origin + Vector((0.00, -0.015, -0.085))
    )
    thumb = bpy.context.object
    thumb.name = "GUIDE_Thumb"
    thumb.scale = (1.05, 0.85, 0.85)
    created.append(thumb)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24,
        radius=0.060,
        depth=0.18,
        location=guide_origin + Vector((0.11, 0.00, 0.00)),
        rotation=(0, 1.5708, 0)
    )
    wrist = bpy.context.object
    wrist.name = "GUIDE_Wrist"
    created.append(wrist)

    mat = create_emissive_material("MAT_LeftHandGuide_Wire")

    for obj in created:
        move_to_collection(obj, guide_col)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        add_wire_modifier(obj, thickness=0.006)
        obj.hide_render = False
        obj.hide_viewport = False

    print("[Step01M-J1-v2] Created cyan emissive wire hand guide.")
    return guide_origin

def setup_render(target, guide_origin):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world.color = (0.035, 0.035, 0.045)

    cam_col = replace_collection(CAM_COLLECTION)

    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(target)
    w=xmax-xmin
    h=zmax-zmin
    d=max(5.0,h*2.0)

    keep = {target.name}
    keep.update(obj.name for obj in bpy.data.collections[GUIDE_COLLECTION].objects)

    states = {}
    for obj in bpy.context.scene.objects:
        states[obj.name] = obj.hide_render
        if obj.type == 'MESH':
            obj.hide_render = obj.name not in keep

    target.hide_render = False
    for obj in bpy.data.collections[GUIDE_COLLECTION].objects:
        obj.hide_render = False

    out_dir = project_root() / "renders" / "hand_refine_j1"
    out_dir.mkdir(parents=True, exist_ok=True)

    views = [
        (
            "DIAG_LeftHandGuide_Compare",
            (xmin-w*0.15, ymin-d*0.18, zmin+h*0.58),
            guide_origin,
            76,
            "LeftHandGuide_Compare.png",
        ),
        (
            "DIAG_LeftArmGuide_ThreeQuarter",
            (xmin+w*0.18, ymin-d*0.40, zmin+h*0.72),
            Vector((xmin+w*0.22, ymin+(ymax-ymin)*0.24, zmin+h*0.60)),
            68,
            "LeftArmGuide_ThreeQuarter.png",
        ),
    ]

    for name, loc, aim, lens, filename in views:
        data = bpy.data.cameras.new(name+"_Data")
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
        print(f"[Step01M-J1-v2] Rendered {out_dir / filename}")

    for name, state in states.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = state

def write_notes():
    out_dir = project_root() / "renders" / "hand_refine_j1"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "LeftHand_Refinement_Notes.txt"
    path.write_text(
        "Left Hand Refinement Notes\n"
        "==========================\n\n"
        "Source hand: LEFT hand.\n"
        "Target: compact stylized Sackboy-like silhouette with three rounded finger lobes,\n"
        "a small thumb bump, reduced palm mass, and a sleeve-friendly wrist/forearm transition.\n\n"
        "J1-v2 uses cyan emissive wire guide geometry for Blender 5.1 compatibility.\n"
        "No character geometry is deformed in this pass.\n",
        encoding="utf-8"
    )
    print(f"[Step01M-J1-v2] Wrote notes: {path}")

def main():
    source = bpy.data.objects.get(SOURCE_NAME)
    if not source or source.type != 'MESH':
        raise RuntimeError("HANDREFINE_Working not found. Run Step01M-J0 first.")

    target = duplicate_working(source)
    guide_origin = make_guide_hand(target)
    setup_render(target, guide_origin)
    write_notes()

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J1-v2] Saved: {out}")

if __name__ == "__main__":
    main()
