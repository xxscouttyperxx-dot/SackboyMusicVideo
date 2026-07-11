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
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def look_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

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
    print(f"[Step01M-J1] Created working duplicate: {dup.name}")
    return dup

def create_guide_material(name, rgba, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Alpha"].default_value = alpha
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.blend_method = 'BLEND'
    mat.shadow_method = 'NONE'
    return mat

def make_guide_hand(target):
    guide_col = replace_collection(GUIDE_COLLECTION)
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(target)
    w=xmax-xmin; h=zmax-zmin

    # approximate left-hand area from diagnostics
    palm_center = Vector((xmin + w*0.11, ymin + (ymax-ymin)*0.30, zmin + h*0.57))
    guide_origin = palm_center + Vector((-0.05, 0.18, 0.00))

    # palm
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.115, location=guide_origin)
    palm = bpy.context.object
    palm.name = "GUIDE_Palm"

    # three compact finger lobes / Sackboy-ish stylization
    offsets = [
        Vector((-0.085, 0.00, 0.05)),
        Vector((-0.108, 0.00, 0.00)),
        Vector((-0.085, 0.00, -0.05)),
    ]
    fingers = []
    for i, off in enumerate(offsets, start=1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.060, location=guide_origin + off)
        f = bpy.context.object
        f.name = f"GUIDE_Finger_{i:02d}"
        fingers.append(f)

    # small thumb bump
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.050, location=guide_origin + Vector((0.00, -0.01, -0.085)))
    thumb = bpy.context.object
    thumb.name = "GUIDE_Thumb"

    # simple wrist capsule using a cylinder
    bpy.ops.mesh.primitive_cylinder_add(radius=0.060, depth=0.18, location=guide_origin + Vector((0.11, 0.00, 0.00)), rotation=(0, 1.5708, 0))
    wrist = bpy.context.object
    wrist.name = "GUIDE_Wrist"

    objs = [palm, wrist, thumb] + fingers
    mat = create_guide_material("MAT_LeftHandGuide", (0.20, 0.75, 1.0, 1.0), 0.35)

    for obj in objs:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        guide_col.objects.link(obj)
        obj.display_type = 'SOLID'
        obj.hide_render = False
        obj.data.materials.clear()
        obj.data.materials.append(mat)

    print("[Step01M-J1] Created translucent left-hand guide volumes.")
    return guide_origin

def setup_cameras(target, guide_origin):
    cam_col = replace_collection(CAM_COLLECTION)
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(target)
    w=xmax-xmin; h=zmax-zmin
    d=max(5.0,h*2.0)

    # left-hand close comparison
    focus = guide_origin + Vector((-0.02, -0.02, 0))
    views = [
        ("DIAG_LeftHandGuide_Orthoish", (xmin - w*0.12, ymin - d*0.16, zmin + h*0.58), focus, 78, "LeftHandGuide_Compare.png"),
        ("DIAG_LeftArm_ThreeQuarter", (xmin + w*0.15, ymin - d*0.38, zmin + h*0.72), Vector((xmin+w*0.22, ymin+(ymax-ymin)*0.24, zmin+h*0.60)), 72, "LeftArmGuide_ThreeQuarter.png"),
    ]

    scene = bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'

    # Hide all mesh objects except current working mesh and guide objects for the renders
    visible_keep = {target.name}
    visible_keep.update(obj.name for obj in bpy.data.collections[GUIDE_COLLECTION].objects)

    states = {}
    for obj in bpy.context.scene.objects:
        states[obj.name] = obj.hide_render
        if obj.type == 'MESH' and obj.name not in visible_keep:
            obj.hide_render = True
    for obj in bpy.data.collections[GUIDE_COLLECTION].objects:
        obj.hide_render = False
    target.hide_render = False

    def make_camera(name, loc, aim, lens):
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.data.lens=lens
        cam.location=loc
        look_at(cam, aim)
        cam_col.objects.link(cam)
        return cam

    out_dir = project_root() / "renders" / "hand_refine_j1"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name,loc,aim,lens,filename in views:
        cam=make_camera(name,loc,aim,lens)
        scene.camera=cam
        scene.render.resolution_x=1280
        scene.render.resolution_y=1280
        scene.render.filepath=str(out_dir / filename)
        bpy.ops.render.render(write_still=True)
        print(f"[Step01M-J1] Rendered {out_dir / filename}")

    # restore hide_render states
    for obj_name, hide_state in states.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_render = hide_state

def write_notes():
    out_dir = project_root() / "renders" / "hand_refine_j1"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "LeftHand_Refinement_Notes.txt"
    lines = [
        "Left Hand Refinement Notes\n",
        "==========================\n\n",
        "Source decision: use the LEFT hand as the source hand.\n",
        "Reason: it has more usable finger separation than the right-hand mitten shape.\n\n",
        "Target shape goals:\n",
        "- compact three-finger Sackboy-style silhouette\n",
        "- short rounded finger tips\n",
        "- smaller palm mass\n",
        "- soft rounded thumb bump\n",
        "- wrist/forearm thickness should blend smoothly and remain sleeve-friendly for the future hoodie\n\n",
        "This pass does not deform the mesh.\n",
        "It creates a duplicate working branch and a translucent guide volume near the better hand.\n",
    ]
    path.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-J1] Wrote notes: {path}")

def main():
    source = bpy.data.objects.get(SOURCE_NAME)
    if not source or source.type != 'MESH':
        raise RuntimeError("Expected HANDREFINE_Working was not found. Run Step01M-J0 first.")
    target = duplicate_working(source)
    guide_origin = make_guide_hand(target)
    setup_cameras(target, guide_origin)
    write_notes()

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J1] Saved guide pass: {out}")

if __name__=="__main__":
    main()
