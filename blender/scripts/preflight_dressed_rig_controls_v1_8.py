
import bpy
from mathutils import Vector, Matrix

SCRIPT_VERSION="1.8"

# ---------------------------------------------------------------------------
# Static regression: inspect executable code in mesh_binding_snapshot only.
# This replaces the broken whole-file PowerShell text search from v1.7.
# ---------------------------------------------------------------------------
import ast
from pathlib import Path

production_path=Path(__file__).with_name("dressed_rig_controls_v1_8.py")
if not production_path.exists():
    raise RuntimeError(f"Production script not found for AST check: {production_path}")

production_source=production_path.read_text(encoding="utf-8")
production_tree=ast.parse(production_source,filename=str(production_path))

binding_function=next(
    (
        node for node in production_tree.body
        if isinstance(node,ast.FunctionDef) and node.name=="mesh_binding_snapshot"
    ),
    None,
)
if binding_function is None:
    raise RuntimeError("mesh_binding_snapshot function not found in production script")

matrix_world_accesses=[
    node for node in ast.walk(binding_function)
    if isinstance(node,ast.Attribute) and node.attr=="matrix_world"
]
matrix_basis_accesses=[
    node for node in ast.walk(binding_function)
    if isinstance(node,ast.Attribute) and node.attr=="matrix_basis"
]
parent_inverse_accesses=[
    node for node in ast.walk(binding_function)
    if isinstance(node,ast.Attribute) and node.attr=="matrix_parent_inverse"
]

static_binding_checks={
    "production_version":'SCRIPT_VERSION="1.8"' in production_source,
    "binding_function_found":binding_function is not None,
    "matrix_world_executable_access_count":len(matrix_world_accesses)==0,
    "matrix_basis_present":len(matrix_basis_accesses)>0,
    "matrix_parent_inverse_present":len(parent_inverse_accesses)>0,
    "pose_independent_marker":"POSE_INDEPENDENT_BINDING_SNAPSHOT" in production_source,
}
static_binding_passed=all(static_binding_checks.values())
print(f"[static_binding_ast_check] passed={static_binding_passed} checks={static_binding_checks}")
if not static_binding_passed:
    raise RuntimeError("Semantic binding-snapshot AST check failed")

def set_pose_world(arm,bone_name,world_matrix):
    arm.pose.bones[bone_name].matrix=arm.matrix_world.inverted()@world_matrix

def rest_world_matrix(arm,bone_name):
    return arm.matrix_world@arm.data.bones[bone_name].matrix_local

# Clean factory-startup scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

data=bpy.data.armatures.new("SYNTHETIC_ARMATURE_DATA")
arm=bpy.data.objects.new("SYNTHETIC_ARMATURE",data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)

bpy.ops.object.mode_set(mode="EDIT")
eb=data.edit_bones

root=eb.new("root")
root.head=(0.0,0.0,0.0)
root.tail=(0.0,0.0,1.0)

pelvis=eb.new("pelvis")
pelvis.head=(0.0,0.0,1.0)
pelvis.tail=(0.0,0.0,2.0)
pelvis.parent=root
pelvis.use_connect=True

ctrl=eb.new("CTRL_pelvis")
ctrl.head=pelvis.head.copy()
ctrl.tail=pelvis.tail.copy()
ctrl.roll=pelvis.roll
ctrl.parent=root
ctrl.use_connect=False
ctrl.use_deform=False

rest_head=pelvis.head.copy()
rest_tail=pelvis.tail.copy()
rest_roll=float(pelvis.roll)

# Exact production sequence.
pelvis.use_connect=False
pelvis.parent=ctrl
pelvis.head=rest_head
pelvis.tail=rest_tail
pelvis.roll=rest_roll

geometry_error=max(
    (pelvis.head-rest_head).length,
    (pelvis.tail-rest_tail).length,
    abs(float(pelvis.roll)-rest_roll),
)
if geometry_error>1.0e-8:
    raise RuntimeError(f"Synthetic preflight: ordered reparent changed geometry: {geometry_error}")

bpy.ops.object.mode_set(mode="POSE")
bpy.context.view_layer.update()

before=(arm.matrix_world@arm.pose.bones["pelvis"].head).copy()
ctrl_before=arm.pose.bones["CTRL_pelvis"].matrix.copy()
target_world=Matrix.Translation(Vector((0.0,0.0,-0.05)))@rest_world_matrix(arm,"CTRL_pelvis")
set_pose_world(arm,"CTRL_pelvis",target_world)
bpy.context.view_layer.update()

after=(arm.matrix_world@arm.pose.bones["pelvis"].head).copy()
movement=(after-before).length

arm.pose.bones["CTRL_pelvis"].matrix=ctrl_before
bpy.context.view_layer.update()
restored=(arm.matrix_world@arm.pose.bones["pelvis"].head).copy()
restore_error=(restored-before).length

checks={
    "geometry_preserved":geometry_error<=1.0e-8,
    "parent_is_control":arm.data.bones["pelvis"].parent==arm.data.bones["CTRL_pelvis"],
    "pelvis_disconnected":arm.data.bones["pelvis"].use_connect is False,
    "control_non_deforming":arm.data.bones["CTRL_pelvis"].use_deform is False,
    "movement":movement>0.049,
    "restore":restore_error<1.0e-6,
}
passed=all(checks.values())
print(f"[synthetic_preflight] version={SCRIPT_VERSION} passed={passed} geometry_error={geometry_error} movement={movement} restore_error={restore_error} checks={checks}")
if not passed:
    raise RuntimeError("Synthetic Blender preflight failed")


# ---------------------------------------------------------------------------
# Regression: pose-dependent world transforms are not binding changes.
# ---------------------------------------------------------------------------
def mlist(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def structural_binding_snapshot(obj):
    return {
        "mesh":obj.data.name,
        "vertices":len(obj.data.vertices),
        "edges":len(obj.data.edges),
        "polygons":len(obj.data.polygons),
        "matrix_basis":mlist(obj.matrix_basis),
        "matrix_parent_inverse":mlist(obj.matrix_parent_inverse),
        "parent":obj.parent.name if obj.parent else "",
        "parent_type":obj.parent_type,
        "parent_bone":obj.parent_bone,
        "modifiers":[(m.name,m.type,getattr(m,"object",None).name if getattr(m,"object",None) else "") for m in obj.modifiers],
        "vertex_groups":[g.name for g in obj.vertex_groups],
    }

# Add a head bone and an eye offset from its rotation axis.
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
head=data.edit_bones.new("head")
head.head=(0.0,0.0,2.0)
head.tail=(0.0,0.0,3.0)
head.parent=data.edit_bones["pelvis"]
head.use_connect=False
bpy.ops.object.mode_set(mode="OBJECT")

mesh=bpy.data.meshes.new("SYNTHETIC_EYE_MESH")
mesh.from_pydata(
    [(0.18,0.0,2.45),(0.22,0.0,2.45),(0.20,0.04,2.45)],
    [],
    [(0,1,2)],
)
mesh.update()
eye=bpy.data.objects.new("SYNTHETIC_EYE",mesh)
bpy.context.scene.collection.objects.link(eye)
eye_world=eye.matrix_world.copy()
eye.parent=arm
eye.parent_type="BONE"
eye.parent_bone="head"
eye.matrix_world=eye_world

arm.animation_data_create()
old_action=bpy.data.actions.new("SYNTHETIC_OLD_ACTION")
arm.animation_data.action=old_action
pb=arm.pose.bones["head"]
pb.rotation_mode="QUATERNION"

bpy.context.scene.frame_set(1)
pb.rotation_quaternion=(1.0,0.0,0.0,0.0)
pb.keyframe_insert(data_path="rotation_quaternion",frame=1,group="head")

bpy.context.scene.frame_set(265)
pb.rotation_quaternion=Vector((0.0,0.0,1.0)).rotation_difference(Vector((0.35,0.0,0.9367496998)))
pb.keyframe_insert(data_path="rotation_quaternion",frame=265,group="head")
bpy.context.view_layer.update()

old_world=eye.matrix_world.copy()
old_structural=structural_binding_snapshot(eye)

new_action=bpy.data.actions.new("SYNTHETIC_NEW_ACTION")
arm.animation_data.action=new_action
pb.rotation_quaternion=(1.0,0.0,0.0,0.0)
pb.keyframe_insert(data_path="rotation_quaternion",frame=265,group="head")
bpy.context.scene.frame_set(265)
bpy.context.view_layer.update()

new_world=eye.matrix_world.copy()
new_structural=structural_binding_snapshot(eye)
world_delta=max(abs(old_world[r][c]-new_world[r][c]) for r in range(4) for c in range(4))
structural_equal=(old_structural==new_structural)

action_switch_checks={
    "world_transform_changes_between_actions":world_delta>0.001,
    "structural_binding_unchanged":structural_equal,
    "eye_parent_preserved":eye.parent==arm and eye.parent_type=="BONE" and eye.parent_bone=="head",
}
action_switch_passed=all(action_switch_checks.values())
print(f"[action_switch_regression] passed={action_switch_passed} world_delta={world_delta} structural_equal={structural_equal} checks={action_switch_checks}")
if not action_switch_passed:
    raise RuntimeError("Synthetic action-switch binding regression failed")
