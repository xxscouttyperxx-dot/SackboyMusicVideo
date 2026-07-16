
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

SCRIPT_VERSION="1.3"


def action_fcurves(action):
    """Return all F-Curves from legacy or Blender 5.1 layered Actions."""
    legacy_fcurves=getattr(action,"fcurves",None)
    if legacy_fcurves is not None:
        return list(legacy_fcurves)

    curves=[]
    seen=set()
    for layer in action.layers:
        for strip in layer.strips:
            channelbags=getattr(strip,"channelbags",None)
            if channelbags is None:
                continue
            for channelbag in channelbags:
                for curve in channelbag.fcurves:
                    pointer=curve.as_pointer()
                    if pointer in seen:
                        continue
                    seen.add(pointer)
                    curves.append(curve)
    return curves

def action_storage_diagnostic(action):
    curves=action_fcurves(action)
    layer_count=len(getattr(action,"layers",[]))
    slot_count=len(getattr(action,"slots",[]))
    channelbag_count=0
    for layer in getattr(action,"layers",[]):
        for strip in layer.strips:
            channelbags=getattr(strip,"channelbags",None)
            if channelbags is not None:
                channelbag_count+=len(channelbags)
    return {
        "storage_api":"LEGACY_ACTION_FCURVES" if hasattr(action,"fcurves") else "LAYERED_ACTION_CHANNELBAGS",
        "layer_count":layer_count,
        "slot_count":slot_count,
        "channelbag_count":channelbag_count,
        "fcurve_count":len(curves),
    }


def driver_target_snapshot(target):
    target_id=getattr(target,"id",None)
    return {
        "id_type":getattr(target,"id_type",""),
        "id_name":target_id.name_full if target_id is not None else "",
        "data_path":getattr(target,"data_path",""),
        "bone_target":getattr(target,"bone_target",""),
        "transform_type":getattr(target,"transform_type",""),
        "transform_space":getattr(target,"transform_space",""),
        "rotation_mode":getattr(target,"rotation_mode",""),
    }

def driver_snapshot(id_block):
    animation=getattr(id_block,"animation_data",None)
    if animation is None:
        return []
    result=[]
    for fcurve in animation.drivers:
        driver=fcurve.driver
        result.append({
            "data_path":fcurve.data_path,
            "array_index":int(fcurve.array_index),
            "driver_type":driver.type,
            "expression":driver.expression,
            "use_self":bool(driver.use_self),
            "variables":[
                {
                    "name":variable.name,
                    "type":variable.type,
                    "targets":[
                        driver_target_snapshot(target)
                        for target in variable.targets
                    ],
                }
                for variable in driver.variables
            ],
        })
    return sorted(
        result,
        key=lambda item:(item["data_path"],item["array_index"]),
    )

def constraint_influence_path(constraint):
    try:
        return constraint.path_from_id("influence")
    except Exception:
        return ""

def constraint_snapshot(arm):
    driver_paths={
        (item["data_path"],item["array_index"])
        for item in driver_snapshot(arm)
    }
    result={}
    for pose_bone in arm.pose.bones:
        entries=[]
        for constraint in pose_bone.constraints:
            influence_path=constraint_influence_path(constraint)
            influence_is_driven=(influence_path,0) in driver_paths
            entries.append({
                "name":constraint.name,
                "type":constraint.type,
                "target":constraint.target.name if getattr(constraint,"target",None) else "",
                "subtarget":getattr(constraint,"subtarget",""),
                "pole_target":constraint.pole_target.name if getattr(constraint,"pole_target",None) else "",
                "pole_subtarget":getattr(constraint,"pole_subtarget",""),
                "mute":bool(getattr(constraint,"mute",False)),
                "owner_space":getattr(constraint,"owner_space",""),
                "target_space":getattr(constraint,"target_space",""),
                "mix_mode":getattr(constraint,"mix_mode",""),
                "chain_count":int(getattr(constraint,"chain_count",0)),
                "pole_angle":float(getattr(constraint,"pole_angle",0.0)),
                "use_location":bool(getattr(constraint,"use_location",False)),
                "use_rotation":bool(getattr(constraint,"use_rotation",False)),
                "use_scale":bool(getattr(constraint,"use_scale",False)),
                "use_stretch":bool(getattr(constraint,"use_stretch",False)),
                "influence_path":influence_path,
                "influence_is_driven":influence_is_driven,
                # A driven influence is an evaluated animation result. Its value
                # is expected to change when IK switch properties are animated.
                # The driver definition is compared separately.
                "undriven_influence":(
                    None
                    if influence_is_driven
                    else float(constraint.influence)
                ),
            })
        result[pose_bone.name]=entries
    return result

def nested_diff(before,after):
    if before==after:
        return {}
    if isinstance(before,dict) and isinstance(after,dict):
        changes={}
        for key in sorted(set(before)|set(after)):
            if key not in before:
                changes[key]={"added":after[key]}
            elif key not in after:
                changes[key]={"removed":before[key]}
            else:
                child=nested_diff(before[key],after[key])
                if child:
                    changes[key]=child
        return changes
    if isinstance(before,list) and isinstance(after,list):
        if before==after:
            return {}
        return {"before":before,"after":after}
    return {"before":before,"after":after}

def arg_value(name):
    if "--" not in sys.argv:
        return None
    args=sys.argv[sys.argv.index("--")+1:]
    for index,value in enumerate(args):
        if value==name and index+1<len(args):
            return args[index+1]
    return None

processed_path=arg_value("--processed")
if not processed_path:
    raise RuntimeError("Missing --processed path")
data=json.loads(Path(processed_path).read_text(encoding="utf-8"))

checks={
    "format":data.get("format")=="SCOUTAI_MEDIAPIPE_POSE_PROCESSED_V1",
    "quality_passed":bool(data.get("quality",{}).get("passed")),
    "frame_count":len(data.get("frames",[]))>=2,
    "landmark_count":all(
        len(frame.get("world",[]))==33 and len(frame.get("normalized",[]))==33
        for frame in data.get("frames",[])[:20]
    ),
}
if not all(checks.values()):
    raise RuntimeError(f"Processed pose preflight failed: {checks}")

# Synthetic armature verifies Blender 5.1 action/keyframe and custom-property APIs.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
arm_data=bpy.data.armatures.new("RETARGET_PREFLIGHT_DATA")
arm=bpy.data.objects.new("RETARGET_PREFLIGHT",arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)

controls=[
    "root","CTRL_pelvis","CTRL_spine","CTRL_chest","CTRL_head",
    "IK_hand.L","IK_hand.R","IK_foot.L","IK_foot.R",
    "POLE_elbow.L","POLE_elbow.R","POLE_knee.L","POLE_knee.R",
]

bpy.ops.object.mode_set(mode="EDIT")
previous=None
for index,name in enumerate(controls):
    bone=arm_data.edit_bones.new(name)
    bone.head=(0.0,0.0,float(index)*0.1)
    bone.tail=(0.0,0.1,float(index)*0.1+0.08)
    bone.use_deform=False
    if name!="root":
        bone.parent=arm_data.edit_bones["root"]
bpy.ops.object.mode_set(mode="POSE")

for prop in ["IK_ARM_L","IK_ARM_R","IK_LEG_L","IK_LEG_R"]:
    arm[prop]=0.0

arm.animation_data_create()
action=bpy.data.actions.new("RETARGET_PREFLIGHT_ACTION")
arm.animation_data.action=action

for frame in (1.0,2.0,3.0):
    bpy.context.scene.frame_set(int(frame))
    arm.pose.bones["root"].location=(0.05*frame,0.0,0.0)
    arm.pose.bones["root"].keyframe_insert(data_path="location",frame=frame)
    arm.pose.bones["IK_foot.L"].location=(0.0,0.0,0.02*frame)
    arm.pose.bones["IK_foot.L"].keyframe_insert(data_path="location",frame=frame)
    arm["IK_LEG_L"]=1.0
    arm.keyframe_insert(data_path='["IK_LEG_L"]',frame=frame)

action_curves=action_fcurves(action)
action_diagnostic=action_storage_diagnostic(action)

for curve in action_curves:
    for keyframe in curve.keyframe_points:
        keyframe.interpolation="LINEAR"

checks.update({
    "action_created":arm.animation_data.action==action,
    "action_slot_assigned":getattr(arm.animation_data,"action_slot",None) is not None,
    "layered_or_legacy_storage_found":action_diagnostic["fcurve_count"]>0,
    "action_has_fcurves":len(action_curves)>0,
    "custom_property_keyed":any(
        curve.data_path=='["IK_LEG_L"]'
        for curve in action_curves
    ),
    "pose_keyed":any(
        'pose.bones["IK_foot.L"]' in curve.data_path
        for curve in action_curves
    ),
    "linear_interpolation_applied":all(
        keyframe.interpolation=="LINEAR"
        for curve in action_curves
        for keyframe in curve.keyframe_points
    ),
})
checks["action_storage_diagnostic"]=action_diagnostic


# Driven constraint influences are evaluated animation results. The structural
# checker must identify them as driven, exclude their evaluated value, preserve
# the driver definition, and still detect real changes to undriven influences.
#
# Some Blender factory-startup/background configurations do not immediately
# refresh a newly created driver's evaluated influence after a custom-property
# assignment. That runtime refresh is diagnostic only; it is not a valid reason
# to fail the structural-snapshot test.
arm["IK_DRIVER_TEST"]=0.0
driven_constraint=arm.pose.bones["IK_foot.R"].constraints.new("COPY_LOCATION")
driven_constraint.name="RETARGET_PREFLIGHT_DRIVEN_CONSTRAINT"
driven_constraint.target=arm
driven_constraint.subtarget="root"
driver_curve=driven_constraint.driver_add("influence")
driver_curve.driver.type="SCRIPTED"
driver_variable=driver_curve.driver.variables.new()
driver_variable.name="switch"
driver_variable.type="SINGLE_PROP"
driver_target=driver_variable.targets[0]
driver_target.id=arm
driver_target.data_path='["IK_DRIVER_TEST"]'
driver_curve.driver.expression="switch"

scene=bpy.context.scene
original_test_frame=scene.frame_current

# Establish the first structural snapshot.
arm.update_tag()
scene.frame_set(original_test_frame)
bpy.context.view_layer.update()
constraint_structure_before=constraint_snapshot(arm)
constraint_drivers_before=driver_snapshot(arm)
evaluated_influence_before=float(driven_constraint.influence)

# Attempt a full dependency refresh after changing the property. Whether the
# synthetic influence visibly refreshes is recorded, but the required test is
# that structural and driver definitions remain unchanged.
arm["IK_DRIVER_TEST"]=1.0
arm.update_tag()
scene.frame_set(original_test_frame+1)
scene.frame_set(original_test_frame)
bpy.context.view_layer.update()
constraint_structure_after=constraint_snapshot(arm)
constraint_drivers_after=driver_snapshot(arm)
evaluated_influence_after=float(driven_constraint.influence)

driven_entry=next(
    (
        entry
        for entry in constraint_structure_after["IK_foot.R"]
        if entry["name"]=="RETARGET_PREFLIGHT_DRIVEN_CONSTRAINT"
    ),
    None,
)

# Prove that the same snapshot still catches a real undriven influence edit.
undriven_constraint=arm.pose.bones["IK_hand.R"].constraints.new("COPY_LOCATION")
undriven_constraint.name="RETARGET_PREFLIGHT_UNDRIVEN_CONSTRAINT"
undriven_constraint.target=arm
undriven_constraint.subtarget="root"
undriven_constraint.influence=0.25
undriven_before=constraint_snapshot(arm)
undriven_constraint.influence=0.75
undriven_after=constraint_snapshot(arm)
undriven_diff=nested_diff(undriven_before,undriven_after)

driver_regression_required_checks={
    "constraint_structure_unchanged_for_driven_value":(
        constraint_structure_before==constraint_structure_after
    ),
    "constraint_driver_definition_unchanged":(
        constraint_drivers_before==constraint_drivers_after
    ),
    "driven_influence_detected":(
        driven_entry is not None
        and driven_entry["influence_is_driven"]
        and driven_entry["undriven_influence"] is None
    ),
    "driver_count_stable":(
        len(constraint_drivers_before)==len(constraint_drivers_after)
        and len(constraint_drivers_after)>=1
    ),
    "undriven_influence_change_detected":bool(undriven_diff),
}
driver_regression_diagnostic={
    "evaluated_influence_before":evaluated_influence_before,
    "evaluated_influence_after":evaluated_influence_after,
    "evaluated_influence_refreshed":abs(
        evaluated_influence_after-evaluated_influence_before
    )>0.9,
    "required_checks":driver_regression_required_checks,
    "undriven_diff":undriven_diff,
}
driver_regression_passed=all(
    driver_regression_required_checks.values()
)
checks["driven_constraint_regression_passed"]=driver_regression_passed
checks["driven_constraint_regression"]=driver_regression_diagnostic
print(
    f"[driven_constraint_regression] version={SCRIPT_VERSION} "
    f"passed={driver_regression_passed} "
    f"influence_before={evaluated_influence_before} "
    f"influence_after={evaluated_influence_after} "
    f"evaluated_refresh_diagnostic="
    f"{driver_regression_diagnostic['evaluated_influence_refreshed']} "
    f"required_checks={driver_regression_required_checks}"
)
if not driver_regression_passed:
    raise RuntimeError(
        "Driven constraint structural-snapshot regression failed"
    )

passed=all(checks.values())
print(f"[jumpstyle_retarget_preflight] version={SCRIPT_VERSION} passed={passed} checks={checks}")
if not passed:
    raise RuntimeError("Jumpstyle retarget Blender API preflight failed")
