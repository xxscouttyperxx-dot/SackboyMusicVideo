
import bpy, math
from mathutils import Vector

SCRIPT_VERSION="1.2"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Create a synthetic armature.
arm_data=bpy.data.armatures.new("PREP_TEST_ARMATURE_DATA")
arm=bpy.data.objects.new("PREP_TEST_ARMATURE",arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)

bpy.ops.object.mode_set(mode="EDIT")
root=arm_data.edit_bones.new("root")
root.head=(0,0,0)
root.tail=(0,0,1)
root.use_deform=False

ctrl=arm_data.edit_bones.new("CTRL_test")
ctrl.head=(0,0,1)
ctrl.tail=(0,0,2)
ctrl.parent=root
ctrl.use_deform=False

deform=arm_data.edit_bones.new("deform")
deform.head=(0,0,1)
deform.tail=(1,0,1)
deform.parent=ctrl
deform.use_deform=True
bpy.ops.object.mode_set(mode="OBJECT")

# Remove default bone collections and create the exact API structure used later.
for collection in list(arm_data.collections):
    arm_data.collections.remove(collection)

main=arm_data.collections.new("CTRL_Main")
defs=arm_data.collections.new("DEF_Skeleton")
main.assign(arm_data.bones["root"])
main.assign(arm_data.bones["CTRL_test"])
defs.assign(arm_data.bones["deform"])
main.is_visible=True
defs.is_visible=False

# Create and assign a custom shape.
shape_mesh=bpy.data.meshes.new("PREP_TEST_SHAPE_MESH")
segments=16
verts=[(math.cos(2*math.pi*i/segments),math.sin(2*math.pi*i/segments),0.0) for i in range(segments)]
edges=[(i,(i+1)%segments) for i in range(segments)]
shape_mesh.from_pydata(verts,edges,[])
shape_mesh.update()
shape=bpy.data.objects.new("PREP_TEST_SHAPE",shape_mesh)
bpy.context.scene.collection.objects.link(shape)
shape.hide_render=True
shape.hide_set(True)

pb=arm.pose.bones["CTRL_test"]
pb.custom_shape=shape
pb.custom_shape_scale_xyz=(0.25,0.25,0.25)

# Blender's bpy_prop_collection membership operator accepts a bone NAME,
# not a Bone object. Compare the assigned-name sets directly so this tests both
# membership and accidental extra assignments.
main_bone_names={bone.name for bone in main.bones}
deform_bone_names={bone.name for bone in defs.bones}

checks={
    "bone_collection_count":len(arm_data.collections)==2,
    "main_assignment_exact":main_bone_names=={"root","CTRL_test"},
    "deform_assignment_exact":deform_bone_names=={"deform"},
    "main_lookup_by_name":main.bones.get("CTRL_test") is not None,
    "deform_lookup_by_name":defs.bones.get("deform") is not None,
    "main_visible":main.is_visible is True,
    "deform_hidden":defs.is_visible is False,
    "custom_shape_assigned":pb.custom_shape==shape,
    "control_non_deforming":arm_data.bones["CTRL_test"].use_deform is False,
    "deform_bone_deforming":arm_data.bones["deform"].use_deform is True,
}
passed=all(checks.values())
print(f"[motion_retarget_prep_preflight] version={SCRIPT_VERSION} passed={passed} checks={checks}")
if not passed:
    raise RuntimeError("Motion-retarget preparation API preflight failed")


# ---------------------------------------------------------------------------
# Regression: animated protected objects must be compared at the same frame.
# ---------------------------------------------------------------------------
def matrix_values(matrix):
    return [[float(matrix[row][column]) for column in range(4)] for row in range(4)]

def protected_test_snapshot(obj):
    return {
        "matrix_world":matrix_values(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "action":obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else "",
    }

protected=bpy.data.objects.new("PROTECTED_ANIMATED_TEST",None)
bpy.context.scene.collection.objects.link(protected)
protected.animation_data_create()
protected_action=bpy.data.actions.new("PROTECTED_ANIMATED_TEST_ACTION")
protected.animation_data.action=protected_action

bpy.context.scene.frame_set(1)
protected.location=(0.0,0.0,0.0)
protected.keyframe_insert(data_path="location",frame=1)

bpy.context.scene.frame_set(20)
protected.location=(2.0,0.0,0.0)
protected.keyframe_insert(data_path="location",frame=20)
bpy.context.view_layer.update()

before_frame=20
bpy.context.scene.frame_set(before_frame)
bpy.context.view_layer.update()
protected_before=protected_test_snapshot(protected)

bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
protected_wrong_frame=protected_test_snapshot(protected)

bpy.context.scene.frame_set(before_frame)
bpy.context.view_layer.update()
protected_same_frame_after=protected_test_snapshot(protected)

protected_frame_checks={
    "different_frames_produce_different_evaluated_state":protected_before!=protected_wrong_frame,
    "same_frame_snapshots_match":protected_before==protected_same_frame_after,
    "comparison_frame_restored":bpy.context.scene.frame_current==before_frame,
}
protected_frame_passed=all(protected_frame_checks.values())
print(
    f"[protected_frame_regression] version={SCRIPT_VERSION} "
    f"passed={protected_frame_passed} checks={protected_frame_checks}"
)
if not protected_frame_passed:
    raise RuntimeError("Protected-object same-frame regression failed")
