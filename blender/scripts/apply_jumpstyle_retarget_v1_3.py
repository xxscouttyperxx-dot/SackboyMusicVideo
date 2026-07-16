
import bpy
import json
import math
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from mathutils import Matrix, Quaternion, Vector

SCRIPT_VERSION="1.3"
RIG="SACKBOY_RIG_PLACEMENT_V1"
SOURCE_REST_ACTION="SACKBOY_CONTROL_RIG_VALIDATION_V1"
PRESERVED_ACTION="F2_DEFORMATION_TEST_V1_2"
TARGET_ACTION="SACKBOY_JUMPSTYLE_RETARGET_V1"
TARGET_START_FRAME=400.0
REST_FRAME=300
MESH_TARGETS=["F2","Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
CONTROLS=[
    "root","CTRL_pelvis","CTRL_spine","CTRL_chest","CTRL_head",
    "IK_hand.L","IK_hand.R","IK_foot.L","IK_foot.R",
    "POLE_elbow.L","POLE_elbow.R","POLE_knee.L","POLE_knee.R",
]
IK_SWITCHES=["IK_ARM_L","IK_ARM_R","IK_LEG_L","IK_LEG_R"]
LANDMARK_NAMES=[
    "nose","left_eye_inner","left_eye","left_eye_outer",
    "right_eye_inner","right_eye","right_eye_outer",
    "left_ear","right_ear","mouth_left","mouth_right",
    "left_shoulder","right_shoulder","left_elbow","right_elbow",
    "left_wrist","right_wrist","left_pinky","right_pinky",
    "left_index","right_index","left_thumb","right_thumb",
    "left_hip","right_hip","left_knee","right_knee",
    "left_ankle","right_ankle","left_heel","right_heel",
    "left_foot_index","right_foot_index",
]
LI={name:index for index,name in enumerate(LANDMARK_NAMES)}


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

def arg_value(name):
    if "--" not in sys.argv:
        return None
    args=sys.argv[sys.argv.index("--")+1:]
    for index,value in enumerate(args):
        if value==name and index+1<len(args):
            return args[index+1]
    return None

def mlist(matrix):
    return [[float(matrix[row][column]) for column in range(4)] for row in range(4)]

def vector3(values):
    return Vector((float(values[0]),float(values[1]),float(values[2])))

def normalized(vector, fallback):
    if vector.length<1.0e-8:
        return fallback.copy()
    return vector.normalized()

def basis_matrix(right,up,forward_hint=None):
    right=normalized(right,Vector((1,0,0)))
    up=up-right*up.dot(right)
    up=normalized(up,Vector((0,0,1)))
    forward=normalized(right.cross(up),Vector((0,-1,0)))
    if forward_hint is not None and forward.dot(forward_hint)<0:
        forward=-forward
    up=normalized(forward.cross(right),Vector((0,0,1)))
    return Matrix((right,forward,up)).transposed()

def compose_matrix(position,rotation):
    matrix=rotation.to_matrix().to_4x4()
    matrix.translation=position
    return matrix

def set_pose_world(arm,bone_name,world_matrix):
    pose_bone=arm.pose.bones[bone_name]
    pose_bone.matrix=arm.matrix_world.inverted()@world_matrix

def pose_world_matrix(arm,bone_name):
    return arm.matrix_world@arm.pose.bones[bone_name].matrix

def pose_head_world(arm,bone_name):
    return arm.matrix_world@arm.pose.bones[bone_name].head

def bone_rest_snapshot(arm):
    return {
        bone.name:{
            "head":list(bone.head_local),
            "tail":list(bone.tail_local),
            "matrix_local":mlist(bone.matrix_local),
            "parent":bone.parent.name if bone.parent else "",
            "use_connect":bool(bone.use_connect),
            "use_deform":bool(bone.use_deform),
        }
        for bone in arm.data.bones
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

def mesh_binding_snapshot(obj):
    checksum=0.0
    memberships=0
    for vertex in obj.data.vertices:
        for entry in vertex.groups:
            memberships+=1
            checksum+=(vertex.index+1)*(entry.group+1)*float(entry.weight)
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
        "modifiers":[
            (modifier.name,modifier.type,getattr(modifier,"object",None).name if getattr(modifier,"object",None) else "")
            for modifier in obj.modifiers
        ],
        "vertex_groups":[group.name for group in obj.vertex_groups],
        "memberships":memberships,
        "weight_checksum":checksum,
    }

def object_snapshot(obj):
    animation=obj.animation_data
    return {
        "type":obj.type,
        "data":getattr(obj.data,"name",""),
        "matrix_world":mlist(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "parent_type":obj.parent_type,
        "parent_bone":obj.parent_bone,
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":animation.action.name if animation and animation.action else "",
        "drivers":len(animation.drivers) if animation else 0,
        "nla":len(animation.nla_tracks) if animation else 0,
        "constraints":[constraint.name for constraint in obj.constraints],
        "modifiers":[
            (modifier.name,modifier.type,getattr(modifier,"object",None).name if getattr(modifier,"object",None) else "")
            for modifier in obj.modifiers
        ],
    }

def evaluated_dimensions(obj,depsgraph):
    evaluated=obj.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=depsgraph)
    try:
        points=[evaluated.matrix_world@vertex.co for vertex in mesh.vertices]
        if not points:
            return Vector((0,0,0))
        minimum=Vector((
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        ))
        maximum=Vector((
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        ))
        return maximum-minimum
    finally:
        evaluated.to_mesh_clear()

def slerp_identity(rotation,amount):
    identity=Quaternion((1.0,0.0,0.0,0.0))
    return identity.slerp(rotation,amount)

def key_pose_bone(pose_bone,frame,location=True,rotation=True):
    if location:
        pose_bone.keyframe_insert(data_path="location",frame=frame,group=pose_bone.name)
    if rotation:
        pose_bone.rotation_mode="QUATERNION"
        pose_bone.keyframe_insert(data_path="rotation_quaternion",frame=frame,group=pose_bone.name)

def set_axis_height(point,axis,height):
    current=point.dot(axis)
    return point+axis*(height-current)

processed_path=arg_value("--processed")
analysis_path=arg_value("--analysis")
if not processed_path or not analysis_path:
    raise RuntimeError("Expected --processed and --analysis paths")

processed=json.loads(Path(processed_path).read_text(encoding="utf-8"))
analysis=json.loads(Path(analysis_path).read_text(encoding="utf-8"))
if processed.get("format")!="SCOUTAI_MEDIAPIPE_POSE_PROCESSED_V1":
    raise RuntimeError("Unsupported processed pose format")
if not processed.get("quality",{}).get("passed"):
    raise RuntimeError("Processed pose quality did not pass")
if processed["metadata"]["source_sha256"]!=analysis["sha256"]:
    raise RuntimeError("Processed pose source hash does not match the packaged reference video")

root_path=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
out_path=os.path.join(root_path,"reports","jumpstyle_mocap_v1")
os.makedirs(out_path,exist_ok=True)

arm=bpy.data.objects.get(RIG)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG}")
if len(arm.data.bones)!=34:
    raise RuntimeError("Safety stop: expected the validated 34-bone rig")
for control in CONTROLS:
    if arm.pose.bones.get(control) is None:
        raise RuntimeError(f"Missing control {control}")
for switch in IK_SWITCHES:
    if switch not in arm:
        raise RuntimeError(f"Missing IK switch {switch}")
for mesh_name in MESH_TARGETS:
    if bpy.data.objects.get(mesh_name) is None:
        raise RuntimeError(f"Missing mesh/accessory {mesh_name}")
if bpy.data.actions.get(SOURCE_REST_ACTION) is None:
    raise RuntimeError(f"Missing source rest action {SOURCE_REST_ACTION}")
if bpy.data.actions.get(PRESERVED_ACTION) is None:
    raise RuntimeError(f"Missing preserved action {PRESERVED_ACTION}")
if bpy.data.actions.get(TARGET_ACTION) is not None:
    raise RuntimeError(f"Safety stop: action already exists: {TARGET_ACTION}")

scene=bpy.context.scene
original_frame=scene.frame_current
original_start=scene.frame_start
original_end=scene.frame_end
original_fps=scene.render.fps/scene.render.fps_base
if original_fps<=0:
    raise RuntimeError("Scene FPS is invalid")

actions_before=sorted(action.name for action in bpy.data.actions)
rest_bones_before=bone_rest_snapshot(arm)
constraints_before=constraint_snapshot(arm)
constraint_drivers_before=driver_snapshot(arm)
bindings_before={name:mesh_binding_snapshot(bpy.data.objects[name]) for name in MESH_TARGETS}
mutable_objects=set(MESH_TARGETS+[RIG])
protected_before={
    obj.name:object_snapshot(obj)
    for obj in bpy.data.objects
    if obj.name not in mutable_objects and not obj.name.startswith("WGT_")
}

# Obtain validated neutral control transforms from frame 300.
arm.animation_data_create()
arm.animation_data.action=bpy.data.actions[SOURCE_REST_ACTION]
scene.frame_set(REST_FRAME)
bpy.context.view_layer.update()

rest_matrices={name:pose_world_matrix(arm,name).copy() for name in CONTROLS}
rest_positions={name:rest_matrices[name].translation.copy() for name in CONTROLS}
rest_rotations={name:rest_matrices[name].to_quaternion() for name in CONTROLS}

target_left_hip=pose_head_world(arm,"thigh.L")
target_right_hip=pose_head_world(arm,"thigh.R")
target_left_shoulder=pose_head_world(arm,"upper_arm.L")
target_right_shoulder=pose_head_world(arm,"upper_arm.R")
target_hip_mid=0.5*(target_left_hip+target_right_hip)
target_shoulder_mid=0.5*(target_left_shoulder+target_right_shoulder)
target_anatomical_right=target_right_hip-target_left_hip
target_up=target_shoulder_mid-target_hip_mid
target_basis=basis_matrix(
    target_anatomical_right,
    target_up,
    Vector((0,-1,0)),
)
target_up_axis=target_basis.col[2].normalized()
target_forward_axis=target_basis.col[1].normalized()

target_leg_length=0.5*(
    (target_left_hip-rest_positions["IK_foot.L"]).length+
    (target_right_hip-rest_positions["IK_foot.R"]).length
)
target_body_height=(rest_positions["CTRL_head"]-0.5*(rest_positions["IK_foot.L"]+rest_positions["IK_foot.R"])).length
target_foot_base_height=0.5*(
    rest_positions["IK_foot.L"].dot(target_up_axis)+
    rest_positions["IK_foot.R"].dot(target_up_axis)
)

calibration_index=int(processed["metadata"]["calibration_frame"])
source_frames=processed["frames"]
calibration=source_frames[calibration_index]
source_world=[vector3(landmark) for landmark in calibration["world"]]

source_left_hip=source_world[LI["left_hip"]]
source_right_hip=source_world[LI["right_hip"]]
source_left_shoulder=source_world[LI["left_shoulder"]]
source_right_shoulder=source_world[LI["right_shoulder"]]
source_hip_mid=0.5*(source_left_hip+source_right_hip)
source_shoulder_mid=0.5*(source_left_shoulder+source_right_shoulder)
source_right=source_right_hip-source_left_hip
source_up=source_shoulder_mid-source_hip_mid
source_forward=source_right.cross(source_up)
source_nose_direction=source_world[LI["nose"]]-source_shoulder_mid
if source_forward.dot(source_nose_direction)<0:
    source_forward=-source_forward
source_basis=basis_matrix(source_right,source_up,source_forward)

source_to_target_rotation=target_basis@source_basis.inverted()
source_leg_length=float(processed["metadata"]["source_leg_length_world"])
if source_leg_length<=1.0e-6:
    raise RuntimeError("Invalid source leg length")
world_scale=target_leg_length/source_leg_length
screen_scale=target_body_height/float(processed["metadata"]["source_body_height_normalized"])
source_x_axis=normalized(
    source_to_target_rotation@Vector((1,0,0)),
    target_basis.col[0],
)

left_rest_pole_elbow=rest_positions["POLE_elbow.L"]-pose_head_world(arm,"forearm.L")
right_rest_pole_elbow=rest_positions["POLE_elbow.R"]-pose_head_world(arm,"forearm.R")
left_rest_pole_knee=rest_positions["POLE_knee.L"]-pose_head_world(arm,"shin.L")
right_rest_pole_knee=rest_positions["POLE_knee.R"]-pose_head_world(arm,"shin.R")
pole_rest_vectors={
    "POLE_elbow.L":left_rest_pole_elbow,
    "POLE_elbow.R":right_rest_pole_elbow,
    "POLE_knee.L":left_rest_pole_knee,
    "POLE_knee.R":right_rest_pole_knee,
}
pole_offsets={name:max(0.1,vector.length) for name,vector in pole_rest_vectors.items()}
previous_pole_direction={
    name:normalized(vector,Vector((0,-1,0)))
    for name,vector in pole_rest_vectors.items()
}

# Foot rest directions for orientation.
rest_foot_direction={}
for side in ("L","R"):
    foot_head=pose_head_world(arm,f"foot.{side}")
    toe_tail=arm.matrix_world@arm.pose.bones[f"toe.{side}"].tail
    rest_foot_direction[side]=normalized(
        toe_tail-foot_head,
        target_forward_axis,
    )

# Reset all pose channels before creating the new action.
for pose_bone in arm.pose.bones:
    pose_bone.matrix_basis=Matrix.Identity(4)
for switch in IK_SWITCHES:
    arm[switch]=1.0
bpy.context.view_layer.update()

action=bpy.data.actions.new(TARGET_ACTION)
arm.animation_data.action=action

source_fps=float(processed["metadata"]["fps"])
target_frames=[
    TARGET_START_FRAME+(frame["index"]*original_fps/source_fps)
    for frame in source_frames
]
target_end=max(target_frames)

left_foot_anchor=None
right_foot_anchor=None
left_foot_rotation_anchor=None
right_foot_rotation_anchor=None
left_contact_segments=[]
right_contact_segments=[]
active_left_segment=None
active_right_segment=None

def mapped_source(vector):
    return source_to_target_rotation@vector*world_scale

def current_source_basis(frame_world):
    left_hip=frame_world[LI["left_hip"]]
    right_hip=frame_world[LI["right_hip"]]
    left_shoulder=frame_world[LI["left_shoulder"]]
    right_shoulder=frame_world[LI["right_shoulder"]]
    hip_mid=0.5*(left_hip+right_hip)
    shoulder_mid=0.5*(left_shoulder+right_shoulder)
    right=right_hip-left_hip
    up=shoulder_mid-hip_mid
    forward=right.cross(up)
    nose_direction=frame_world[LI["nose"]]-shoulder_mid
    if forward.dot(nose_direction)<0:
        forward=-forward
    return basis_matrix(right,up,forward)

def pole_position(frame_world,joint_name,a_name,b_name,control_name,pelvis_position):
    joint=mapped_source(frame_world[LI[joint_name]])+pelvis_position
    a=mapped_source(frame_world[LI[a_name]])+pelvis_position
    b=mapped_source(frame_world[LI[b_name]])+pelvis_position
    plane=(joint-a).cross(b-joint)
    direction=normalized(plane,previous_pole_direction[control_name])
    if direction.dot(previous_pole_direction[control_name])<0:
        direction=-direction
    previous_pole_direction[control_name]=direction
    return joint+direction*pole_offsets[control_name]

def foot_target(frame,frame_world,side,pelvis_position):
    prefix="left" if side=="L" else "right"
    ankle=mapped_source(frame_world[LI[f"{prefix}_ankle"]])+pelvis_position
    heel=mapped_source(frame_world[LI[f"{prefix}_heel"]])+pelvis_position
    toe=mapped_source(frame_world[LI[f"{prefix}_foot_index"]])+pelvis_position
    position=0.40*ankle+0.30*heel+0.30*toe
    height=target_foot_base_height+float(frame[f"{prefix}_foot_height_norm"])*screen_scale
    position=set_axis_height(position,target_up_axis,height)
    current_direction=normalized(toe-heel,rest_foot_direction[side])
    delta=rest_foot_direction[side].rotation_difference(current_direction)
    rotation=delta@rest_rotations[f"IK_foot.{side}"]
    return position,rotation

for index,(source_frame,target_frame) in enumerate(zip(source_frames,target_frames)):
    frame_world=[vector3(landmark) for landmark in source_frame["world"]]
    body_basis_source=current_source_basis(frame_world)
    current_target_basis=source_to_target_rotation@body_basis_source
    body_delta=(current_target_basis@target_basis.inverted()).to_quaternion()
    body_delta.normalize()

    horizontal_delta=(
        source_x_axis
        *float(source_frame["pelvis_screen_delta_x"])
        *screen_scale
    )
    vertical_delta=(
        target_up_axis
        *float(source_frame["pelvis_height_delta_norm"])
        *screen_scale
    )

    root_position=rest_positions["root"]+horizontal_delta
    pelvis_position=rest_positions["CTRL_pelvis"]+horizontal_delta+vertical_delta

    root_matrix=compose_matrix(root_position,rest_rotations["root"])
    pelvis_matrix=compose_matrix(
        pelvis_position,
        body_delta@rest_rotations["CTRL_pelvis"],
    )
    spine_matrix=compose_matrix(
        rest_positions["CTRL_spine"]+horizontal_delta+vertical_delta,
        slerp_identity(body_delta,0.40)@rest_rotations["CTRL_spine"],
    )
    chest_matrix=compose_matrix(
        rest_positions["CTRL_chest"]+horizontal_delta+vertical_delta,
        slerp_identity(body_delta,0.78)@rest_rotations["CTRL_chest"],
    )
    head_matrix=compose_matrix(
        rest_positions["CTRL_head"]+horizontal_delta+vertical_delta,
        body_delta@rest_rotations["CTRL_head"],
    )

    set_pose_world(arm,"root",root_matrix)
    bpy.context.view_layer.update()
    set_pose_world(arm,"CTRL_pelvis",pelvis_matrix)
    set_pose_world(arm,"CTRL_spine",spine_matrix)
    set_pose_world(arm,"CTRL_chest",chest_matrix)
    set_pose_world(arm,"CTRL_head",head_matrix)

    left_hand=pelvis_position+mapped_source(frame_world[LI["left_wrist"]])
    right_hand=pelvis_position+mapped_source(frame_world[LI["right_wrist"]])
    set_pose_world(
        arm,"IK_hand.L",
        compose_matrix(left_hand,rest_rotations["IK_hand.L"]),
    )
    set_pose_world(
        arm,"IK_hand.R",
        compose_matrix(right_hand,rest_rotations["IK_hand.R"]),
    )

    left_foot,left_rotation=foot_target(source_frame,frame_world,"L",pelvis_position)
    right_foot,right_rotation=foot_target(source_frame,frame_world,"R",pelvis_position)

    left_contact=bool(source_frame["left_foot_contact"])
    right_contact=bool(source_frame["right_foot_contact"])

    if left_contact:
        if left_foot_anchor is None:
            left_foot_anchor=left_foot.copy()
            left_foot_anchor=set_axis_height(left_foot_anchor,target_up_axis,target_foot_base_height)
            left_foot_rotation_anchor=left_rotation.copy()
            active_left_segment={"start":index,"positions":[]}
        left_foot=left_foot_anchor.copy()
        left_rotation=left_foot_rotation_anchor.copy()
        active_left_segment["positions"].append(list(left_foot))
    elif left_foot_anchor is not None:
        active_left_segment["end"]=index-1
        left_contact_segments.append(active_left_segment)
        active_left_segment=None
        left_foot_anchor=None
        left_foot_rotation_anchor=None

    if right_contact:
        if right_foot_anchor is None:
            right_foot_anchor=right_foot.copy()
            right_foot_anchor=set_axis_height(right_foot_anchor,target_up_axis,target_foot_base_height)
            right_foot_rotation_anchor=right_rotation.copy()
            active_right_segment={"start":index,"positions":[]}
        right_foot=right_foot_anchor.copy()
        right_rotation=right_foot_rotation_anchor.copy()
        active_right_segment["positions"].append(list(right_foot))
    elif right_foot_anchor is not None:
        active_right_segment["end"]=index-1
        right_contact_segments.append(active_right_segment)
        active_right_segment=None
        right_foot_anchor=None
        right_foot_rotation_anchor=None

    set_pose_world(arm,"IK_foot.L",compose_matrix(left_foot,left_rotation))
    set_pose_world(arm,"IK_foot.R",compose_matrix(right_foot,right_rotation))

    pole_positions={
        "POLE_elbow.L":pole_position(
            frame_world,"left_elbow","left_shoulder","left_wrist","POLE_elbow.L",pelvis_position
        ),
        "POLE_elbow.R":pole_position(
            frame_world,"right_elbow","right_shoulder","right_wrist","POLE_elbow.R",pelvis_position
        ),
        "POLE_knee.L":pole_position(
            frame_world,"left_knee","left_hip","left_ankle","POLE_knee.L",pelvis_position
        ),
        "POLE_knee.R":pole_position(
            frame_world,"right_knee","right_hip","right_ankle","POLE_knee.R",pelvis_position
        ),
    }
    for control,position in pole_positions.items():
        set_pose_world(
            arm,control,
            compose_matrix(position,rest_rotations[control]),
        )

    bpy.context.view_layer.update()

    for control in ["root","CTRL_pelvis","CTRL_spine","CTRL_chest","CTRL_head"]:
        key_pose_bone(arm.pose.bones[control],target_frame,location=True,rotation=True)
    for control in ["IK_hand.L","IK_hand.R","IK_foot.L","IK_foot.R"]:
        key_pose_bone(arm.pose.bones[control],target_frame,location=True,rotation=True)
    for control in ["POLE_elbow.L","POLE_elbow.R","POLE_knee.L","POLE_knee.R"]:
        key_pose_bone(arm.pose.bones[control],target_frame,location=True,rotation=False)

    for switch in IK_SWITCHES:
        arm[switch]=1.0
        arm.keyframe_insert(data_path=f'["{switch}"]',frame=target_frame,group="IK_SWITCHES")

if active_left_segment is not None:
    active_left_segment["end"]=len(source_frames)-1
    left_contact_segments.append(active_left_segment)
if active_right_segment is not None:
    active_right_segment["end"]=len(source_frames)-1
    right_contact_segments.append(active_right_segment)

target_action_fcurves=action_fcurves(action)
target_action_diagnostic=action_storage_diagnostic(action)
if not target_action_fcurves:
    raise RuntimeError(
        "Safety stop: generated Action contains no F-Curves in its "
        "legacy or layered channel storage"
    )

for fcurve in target_action_fcurves:
    for keyframe in fcurve.keyframe_points:
        keyframe.interpolation="LINEAR"

print(f"[action_storage] {target_action_diagnostic}")

# Validate contact anchors are stationary.
def segment_slide(segments):
    maximum=0.0
    for segment in segments:
        positions=[Vector(position) for position in segment["positions"]]
        if positions:
            anchor=positions[0]
            maximum=max(maximum,max((position-anchor).length for position in positions))
    return maximum

left_slide=segment_slide(left_contact_segments)
right_slide=segment_slide(right_contact_segments)

scene.frame_start=int(math.floor(TARGET_START_FRAME))
scene.frame_end=int(math.ceil(target_end))
scene.frame_set(scene.frame_start)
bpy.context.view_layer.update()

# Geometry sanity checks at evenly spaced samples.
depsgraph=bpy.context.evaluated_depsgraph_get()
sample_indices=sorted(set(
    int(round(value))
    for value in [
        0,
        len(source_frames)*0.1,
        len(source_frames)*0.2,
        len(source_frames)*0.3,
        len(source_frames)*0.4,
        len(source_frames)*0.5,
        len(source_frames)*0.6,
        len(source_frames)*0.7,
        len(source_frames)*0.8,
        len(source_frames)*0.9,
        len(source_frames)-1,
    ]
))
rest_dimensions={}
arm.animation_data.action=bpy.data.actions[SOURCE_REST_ACTION]
scene.frame_set(REST_FRAME)
bpy.context.view_layer.update()
for name in ["F2","Lowerpoly hoodie","Cargo pants"]:
    rest_dimensions[name]=evaluated_dimensions(bpy.data.objects[name],depsgraph)

arm.animation_data.action=action
geometry_samples={}
geometry_passed=True
for sample_index in sample_indices:
    frame=target_frames[sample_index]
    scene.frame_set(int(round(frame)))
    bpy.context.view_layer.update()
    geometry_samples[str(sample_index)]={}
    for name in ["F2","Lowerpoly hoodie","Cargo pants"]:
        dimensions=evaluated_dimensions(bpy.data.objects[name],depsgraph)
        ratios=[
            float(dimensions[axis]/rest_dimensions[name][axis])
            if rest_dimensions[name][axis]>1.0e-8 else 1.0
            for axis in range(3)
        ]
        finite=all(math.isfinite(value) for value in ratios)
        passed=finite and all(0.20<=value<=4.0 for value in ratios)
        geometry_samples[str(sample_index)][name]={
            "dimensions":list(dimensions),
            "ratios":ratios,
            "finite":finite,
            "passed":passed,
        }
        geometry_passed=geometry_passed and passed
if not geometry_passed:
    raise RuntimeError("Safety stop: retargeted geometry sanity check failed")

# Structural safety validation.
rest_bones_after=bone_rest_snapshot(arm)
rest_bone_changes=[
    name for name in rest_bones_before
    if rest_bones_before[name]!=rest_bones_after.get(name)
]
if rest_bone_changes:
    raise RuntimeError("Safety stop: rest bones changed: "+", ".join(rest_bone_changes))

constraints_after=constraint_snapshot(arm)
constraint_drivers_after=driver_snapshot(arm)
constraint_structure_diff=nested_diff(constraints_before,constraints_after)
constraint_driver_diff=nested_diff(
    constraint_drivers_before,
    constraint_drivers_after,
)
constraint_changes=[]
if constraint_structure_diff:
    constraint_changes.append("constraint_structure")
if constraint_driver_diff:
    constraint_changes.append("constraint_drivers")

constraint_diagnostic={
    "script_version":SCRIPT_VERSION,
    "snapshot_mode":"STRUCTURAL_CONSTRAINTS_WITH_DRIVEN_INFLUENCE_EXCLUDED",
    "driven_influence_policy":"COMPARE_DRIVER_DEFINITION_NOT_EVALUATED_VALUE",
    "structure_change_count":1 if constraint_structure_diff else 0,
    "driver_change_count":1 if constraint_driver_diff else 0,
    "structure_diff":constraint_structure_diff,
    "driver_diff":constraint_driver_diff,
    "driver_count_before":len(constraint_drivers_before),
    "driver_count_after":len(constraint_drivers_after),
}
with open(
    os.path.join(out_path,"ConstraintDiagnosticV1_3.json"),
    "w",
    encoding="utf-8",
) as file:
    json.dump(constraint_diagnostic,file,indent=2)

print(
    f"[constraint_diagnostic] mode={constraint_diagnostic['snapshot_mode']} "
    f"drivers=({len(constraint_drivers_before)},{len(constraint_drivers_after)}) "
    f"structure_changes={bool(constraint_structure_diff)} "
    f"driver_changes={bool(constraint_driver_diff)}"
)
if constraint_changes:
    raise RuntimeError(
        "Safety stop: true rig constraint/driver structure changed: "
        +", ".join(constraint_changes)
    )

bindings_after={name:mesh_binding_snapshot(bpy.data.objects[name]) for name in MESH_TARGETS}
binding_changes=[
    name for name in MESH_TARGETS
    if bindings_before[name]!=bindings_after[name]
]
if binding_changes:
    raise RuntimeError("Safety stop: mesh bindings/weights changed: "+", ".join(binding_changes))

# Compare animated protected objects at the same original frame.
scene.frame_set(original_frame)
bpy.context.view_layer.update()
protected_after={
    obj.name:object_snapshot(obj)
    for obj in bpy.data.objects
    if obj.name not in mutable_objects and not obj.name.startswith("WGT_")
}
protected_changes=[]
if set(protected_before)!=set(protected_after):
    protected_changes.append("__object_set__")
for name in sorted(set(protected_before)&set(protected_after)):
    if protected_before[name]!=protected_after[name]:
        protected_changes.append(name)
if protected_changes:
    raise RuntimeError("Safety stop: protected object changes: "+", ".join(protected_changes[:10]))

actions_after=sorted(action.name for action in bpy.data.actions)
expected_actions=sorted(actions_before+[TARGET_ACTION])
if actions_after!=expected_actions:
    raise RuntimeError("Safety stop: unexpected action set after retarget")

# Validate fcurves and switches.
keyed_controls={
    control:any(f'pose.bones["{control}"]' in curve.data_path for curve in target_action_fcurves)
    for control in CONTROLS
}
switch_curves={
    switch:any(curve.data_path==f'["{switch}"]' for curve in target_action_fcurves)
    for switch in IK_SWITCHES
}
if not all(keyed_controls.values()):
    missing=[name for name,value in keyed_controls.items() if not value]
    raise RuntimeError("Safety stop: missing keyed controls: "+", ".join(missing))
if not all(switch_curves.values()):
    missing=[name for name,value in switch_curves.items() if not value]
    raise RuntimeError("Safety stop: missing keyed switches: "+", ".join(missing))

# Leave the generated action active for user playback.
arm.animation_data.action=action
scene.frame_set(scene.frame_start)
bpy.context.view_layer.update()

status={
    "script_version":SCRIPT_VERSION,
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "saved_blend":False,
    "source_video":analysis["source_file"],
    "source_sha256":analysis["sha256"],
    "source_width":analysis["width"],
    "source_height":analysis["height"],
    "source_fps":source_fps,
    "source_frame_count":len(source_frames),
    "source_duration_seconds":analysis["duration_seconds"],
    "source_audio_usable":analysis["audio_analysis"]["usable_audio"],
    "pose_quality":processed["quality"],
    "calibration_frame":calibration_index,
    "target_action":TARGET_ACTION,
    "target_start_frame":TARGET_START_FRAME,
    "target_end_frame":target_end,
    "scene_fps":original_fps,
    "scene_frame_start_before":original_start,
    "scene_frame_end_before":original_end,
    "scene_frame_start_after":scene.frame_start,
    "scene_frame_end_after":scene.frame_end,
    "scene_frame_range_changed_intentionally":True,
    "world_scale":world_scale,
    "screen_scale":screen_scale,
    "target_leg_length":target_leg_length,
    "source_leg_length":source_leg_length,
    "keyed_control_count":sum(keyed_controls.values()),
    "keyed_controls":keyed_controls,
    "keyed_switch_count":sum(switch_curves.values()),
    "keyed_switches":switch_curves,
    "action_storage_api":target_action_diagnostic["storage_api"],
    "action_layer_count":target_action_diagnostic["layer_count"],
    "action_slot_count":target_action_diagnostic["slot_count"],
    "action_channelbag_count":target_action_diagnostic["channelbag_count"],
    "fcurve_count":len(target_action_fcurves),
    "keyframe_point_count":sum(
        len(curve.keyframe_points)
        for curve in target_action_fcurves
    ),
    "left_contact_segment_count":len(left_contact_segments),
    "right_contact_segment_count":len(right_contact_segments),
    "left_contact_max_target_slide":left_slide,
    "right_contact_max_target_slide":right_slide,
    "geometry_sample_count":len(sample_indices),
    "geometry_samples":geometry_samples,
    "geometry_checks_passed":geometry_passed,
    "rest_bone_change_count":len(rest_bone_changes),
    "constraint_snapshot_mode":"STRUCTURAL_CONSTRAINTS_WITH_DRIVEN_INFLUENCE_EXCLUDED",
    "constraint_driver_policy":"COMPARE_DRIVER_DEFINITION_NOT_EVALUATED_VALUE",
    "constraint_change_count":len(constraint_changes),
    "constraint_structure_change_count":1 if constraint_structure_diff else 0,
    "constraint_driver_change_count":1 if constraint_driver_diff else 0,
    "constraint_driver_count_before":len(constraint_drivers_before),
    "constraint_driver_count_after":len(constraint_drivers_after),
    "mesh_binding_change_count":len(binding_changes),
    "protected_change_count":len(protected_changes),
    "existing_actions_preserved":all(bpy.data.actions.get(name) is not None for name in actions_before),
    "active_action":arm.animation_data.action.name,
}

with open(os.path.join(out_path,"JumpstyleMocapV1_status.json"),"w",encoding="utf-8") as file:
    json.dump(status,file,indent=2)
with open(os.path.join(out_path,"JumpstyleMocapV1_report.txt"),"w",encoding="utf-8") as file:
    file.write("SACKBOY AUTOMATED JUMPSTYLE MOCAP V1\n")
    file.write(f"source_frames={len(source_frames)}\n")
    file.write(f"source_fps={source_fps}\n")
    file.write(f"source_duration_seconds={analysis['duration_seconds']}\n")
    file.write(f"pose_detection_rate={processed['quality']['detection_rate']:.6f}\n")
    file.write(f"median_key_visibility={processed['quality']['median_key_visibility']:.6f}\n")
    file.write(f"calibration_frame={calibration_index}\n")
    file.write(f"target_action={TARGET_ACTION}\n")
    file.write(f"target_frame_range={TARGET_START_FRAME},{target_end}\n")
    file.write(f"keyed_controls={sum(keyed_controls.values())}\n")
    file.write(f"keyed_switches={sum(switch_curves.values())}\n")
    file.write(f"action_storage_api={target_action_diagnostic['storage_api']}\n")
    file.write(f"action_layers={target_action_diagnostic['layer_count']}\n")
    file.write(f"action_slots={target_action_diagnostic['slot_count']}\n")
    file.write(f"action_channelbags={target_action_diagnostic['channelbag_count']}\n")
    file.write(f"fcurves={len(target_action_fcurves)}\n")
    file.write(f"keyframe_points={status['keyframe_point_count']}\n")
    file.write(f"left_contact_segments={len(left_contact_segments)}\n")
    file.write(f"right_contact_segments={len(right_contact_segments)}\n")
    file.write(f"left_contact_max_target_slide={left_slide:.12f}\n")
    file.write(f"right_contact_max_target_slide={right_slide:.12f}\n")
    file.write(f"geometry_checks_passed={geometry_passed}\n")
    file.write(f"rest_bone_changes={len(rest_bone_changes)}\n")
    file.write("constraint_snapshot_mode=STRUCTURAL_CONSTRAINTS_WITH_DRIVEN_INFLUENCE_EXCLUDED\n")
    file.write("constraint_driver_policy=COMPARE_DRIVER_DEFINITION_NOT_EVALUATED_VALUE\n")
    file.write(f"constraint_changes={len(constraint_changes)}\n")
    file.write(f"constraint_structure_changes={1 if constraint_structure_diff else 0}\n")
    file.write(f"constraint_driver_changes={1 if constraint_driver_diff else 0}\n")
    file.write(f"constraint_driver_count_before={len(constraint_drivers_before)}\n")
    file.write(f"constraint_driver_count_after={len(constraint_drivers_after)}\n")
    file.write(f"mesh_binding_changes={len(binding_changes)}\n")
    file.write(f"protected_changes={len(protected_changes)}\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(out_path,"JumpstyleMocapV1_status.json"),"w",encoding="utf-8") as file:
    json.dump(status,file,indent=2)

print(f"[version] automated jumpstyle mocap v{SCRIPT_VERSION}")
print(f"[source] frames={len(source_frames)} fps={source_fps} duration={analysis['duration_seconds']}")
print(f"[pose_quality] {processed['quality']}")
print(f"[retarget] action={TARGET_ACTION} range=({TARGET_START_FRAME},{target_end}) controls={sum(keyed_controls.values())} switches={sum(switch_curves.values())}")
print(f"[contacts] left_segments={len(left_contact_segments)} right_segments={len(right_contact_segments)} slide=({left_slide},{right_slide})")
print(f"[geometry] samples={len(sample_indices)} passed={geometry_passed}")
print(f"[safety] rest_bones={len(rest_bone_changes)} constraint_structure={1 if constraint_structure_diff else 0} constraint_drivers={1 if constraint_driver_diff else 0} bindings={len(binding_changes)} protected={len(protected_changes)}")
print("[save] blend saved")
