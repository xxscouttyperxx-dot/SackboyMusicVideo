
import bpy, os, json, math
from mathutils import Vector
from datetime import datetime, timezone

SCRIPT_VERSION="1.2"
ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","motion_retarget_prep_v1_2")
CONFIG_DIR=os.path.join(ROOT,"configs")
os.makedirs(OUT,exist_ok=True)
os.makedirs(CONFIG_DIR,exist_ok=True)

RIG="SACKBOY_RIG_PLACEMENT_V1"
ACTIVE_ACTION="SACKBOY_CONTROL_RIG_VALIDATION_V1"
PRESERVED_ACTION="F2_DEFORMATION_TEST_V1_2"
MESH_TARGETS=["F2","Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
CONTROL_MAIN=["root","CTRL_pelvis","CTRL_spine","CTRL_chest","CTRL_head"]
CONTROL_IK=["IK_hand.L","IK_hand.R","IK_foot.L","IK_foot.R"]
CONTROL_POLES=["POLE_elbow.L","POLE_elbow.R","POLE_knee.L","POLE_knee.R"]
ALL_CONTROLS=CONTROL_MAIN+CONTROL_IK+CONTROL_POLES
BONE_COLLECTIONS={
    "CTRL_Main":CONTROL_MAIN,
    "CTRL_IK":CONTROL_IK,
    "CTRL_Poles":CONTROL_POLES,
}
SHAPE_COLLECTION="RIG_UI_SHAPES"
SHAPE_OBJECTS=["WGT_ROOT_V1","WGT_MAIN_V1","WGT_IK_V1","WGT_POLE_V1"]
REST_FRAME=300
REST_TOL=1.0e-5

def mlist(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def object_snapshot(obj):
    ad=obj.animation_data
    return {
        "type":obj.type,
        "data":getattr(obj.data,"name",""),
        "matrix_world":mlist(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "parent_type":obj.parent_type,
        "parent_bone":obj.parent_bone,
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "drivers":len(ad.drivers) if ad else 0,
        "nla":len(ad.nla_tracks) if ad else 0,
        "modifiers":[(m.name,m.type,getattr(m,"object",None).name if getattr(m,"object",None) else "") for m in obj.modifiers],
        "constraints":[c.name for c in obj.constraints],
    }

def snapshot_diff_keys(before,after):
    return [
        key
        for key in sorted(set(before)|set(after))
        if before.get(key)!=after.get(key)
    ]

def rest_bone_snapshot(arm):
    return {
        b.name:{
            "head":list(b.head_local),
            "tail":list(b.tail_local),
            "matrix_local":mlist(b.matrix_local),
            "parent":b.parent.name if b.parent else "",
            "use_connect":bool(b.use_connect),
            "use_deform":bool(b.use_deform),
        }
        for b in arm.data.bones
    }

def constraint_snapshot(arm):
    return {
        pb.name:[
            {
                "name":c.name,
                "type":c.type,
                "target":c.target.name if getattr(c,"target",None) else "",
                "subtarget":getattr(c,"subtarget",""),
                "pole_target":c.pole_target.name if getattr(c,"pole_target",None) else "",
                "pole_subtarget":getattr(c,"pole_subtarget",""),
                "influence":float(c.influence),
            }
            for c in pb.constraints
        ]
        for pb in arm.pose.bones
    }

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
        "modifiers":[(m.name,m.type,getattr(m,"object",None).name if getattr(m,"object",None) else "") for m in obj.modifiers],
        "vertex_groups":[g.name for g in obj.vertex_groups],
        "memberships":memberships,
        "weight_checksum":checksum,
    }

def evaluated_points(obj,depsgraph):
    evaluated=obj.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=depsgraph)
    try:
        matrix=evaluated.matrix_world.copy()
        return [matrix@vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

def max_point_error(before,after):
    if len(before)!=len(after):
        raise RuntimeError("Evaluated vertex count changed")
    return max(((a-b).length for a,b in zip(before,after)),default=0.0)

def create_wire_shape(name,kind):
    mesh=bpy.data.meshes.new(name+"_MESH")
    if kind=="circle":
        segments=32
        vertices=[(math.cos(2*math.pi*i/segments),math.sin(2*math.pi*i/segments),0.0) for i in range(segments)]
        edges=[(i,(i+1)%segments) for i in range(segments)]
    elif kind=="square":
        vertices=[(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)]
        edges=[(0,1),(1,2),(2,3),(3,0)]
    elif kind=="diamond":
        vertices=[(0,-1,0),(1,0,0),(0,1,0),(-1,0,0),(0,0,-0.6),(0,0,0.6)]
        edges=[(0,1),(1,2),(2,3),(3,0),(4,0),(4,1),(4,2),(4,3),(5,0),(5,1),(5,2),(5,3)]
    elif kind=="root":
        vertices=[
            (-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),
            (-1.35,0,0),(1.35,0,0),(0,-1.35,0),(0,1.35,0)
        ]
        edges=[(0,1),(1,2),(2,3),(3,0),(4,5),(6,7)]
    else:
        raise RuntimeError(f"Unknown shape kind: {kind}")
    mesh.from_pydata(vertices,edges,[])
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    shape_collection.objects.link(obj)
    obj.hide_render=True
    obj.hide_set(True)
    return obj

# ---------- preflight ----------
arm=bpy.data.objects.get(RIG)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG}")
if len(arm.data.bones)!=34:
    raise RuntimeError("Safety stop: expected the validated 34-bone control rig")
for name in ALL_CONTROLS:
    if arm.data.bones.get(name) is None:
        raise RuntimeError(f"Missing control bone {name}")
for name in MESH_TARGETS:
    if bpy.data.objects.get(name) is None:
        raise RuntimeError(f"Missing target object {name}")
if not arm.animation_data or not arm.animation_data.action or arm.animation_data.action.name!=ACTIVE_ACTION:
    raise RuntimeError(f"Safety stop: expected active action {ACTIVE_ACTION}")
if bpy.data.actions.get(PRESERVED_ACTION) is None:
    raise RuntimeError(f"Safety stop: preserved action {PRESERVED_ACTION} is missing")
if bpy.data.collections.get(SHAPE_COLLECTION) is not None:
    raise RuntimeError("Safety stop: rig UI shape collection already exists")
for name in SHAPE_OBJECTS:
    if bpy.data.objects.get(name) is not None:
        raise RuntimeError(f"Safety stop: custom shape object already exists: {name}")

deform_names=sorted(b.name for b in arm.data.bones if b.use_deform)
if len(deform_names)!=21:
    raise RuntimeError("Safety stop: expected 21 deform bones")
if set(deform_names)&set(ALL_CONTROLS):
    raise RuntimeError("Safety stop: a control bone is unexpectedly deforming")

scene=bpy.context.scene
original_frame=scene.frame_current
protected_check_frame=original_frame
frame_start_before=scene.frame_start
frame_end_before=scene.frame_end
active_action_before=arm.animation_data.action.name
actions_before=sorted(action.name for action in bpy.data.actions)
rest_before=rest_bone_snapshot(arm)
constraints_before=constraint_snapshot(arm)
bindings_before={name:mesh_binding_snapshot(bpy.data.objects[name]) for name in MESH_TARGETS}
mutable_existing=set(MESH_TARGETS+[RIG])
protected_before={obj.name:object_snapshot(obj) for obj in bpy.data.objects if obj.name not in mutable_existing}

scene.frame_set(REST_FRAME)
bpy.context.view_layer.update()
depsgraph=bpy.context.evaluated_depsgraph_get()
rest_points_before={name:evaluated_points(bpy.data.objects[name],depsgraph) for name in MESH_TARGETS}

# ---------- replace bone collection organization ----------
for collection in list(arm.data.collections):
    arm.data.collections.remove(collection)

created_collections={}
for collection_name in ["CTRL_Main","CTRL_IK","CTRL_Poles","DEF_Skeleton"]:
    created_collections[collection_name]=arm.data.collections.new(collection_name)

for collection_name,bones in BONE_COLLECTIONS.items():
    collection=created_collections[collection_name]
    for bone_name in bones:
        collection.assign(arm.data.bones[bone_name])

deform_collection=created_collections["DEF_Skeleton"]
for bone_name in deform_names:
    deform_collection.assign(arm.data.bones[bone_name])

# Validate exact assignments using bone names. Blender collection membership
# must not be tested by passing a Bone object to `in collection.bones`.
expected_collection_bones={
    "CTRL_Main":set(CONTROL_MAIN),
    "CTRL_IK":set(CONTROL_IK),
    "CTRL_Poles":set(CONTROL_POLES),
    "DEF_Skeleton":set(deform_names),
}
actual_collection_bones={
    name:{bone.name for bone in collection.bones}
    for name,collection in created_collections.items()
}
collection_assignment_checks={
    name:actual_collection_bones[name]==expected_collection_bones[name]
    for name in expected_collection_bones
}
collection_assignment_checks_passed=all(collection_assignment_checks.values())
print(
    f"[bone_collection_assignments] passed={collection_assignment_checks_passed} "
    f"checks={collection_assignment_checks} actual={actual_collection_bones}"
)
if not collection_assignment_checks_passed:
    raise RuntimeError("Safety stop: bone collection assignments are not exact")

created_collections["CTRL_Main"].is_visible=True
created_collections["CTRL_IK"].is_visible=True
created_collections["CTRL_Poles"].is_visible=True
created_collections["DEF_Skeleton"].is_visible=False

# ---------- create custom shapes ----------
shape_collection=bpy.data.collections.new(SHAPE_COLLECTION)
scene.collection.children.link(shape_collection)
shape_collection.hide_render=True

shape_root=create_wire_shape("WGT_ROOT_V1","root")
shape_main=create_wire_shape("WGT_MAIN_V1","circle")
shape_ik=create_wire_shape("WGT_IK_V1","square")
shape_pole=create_wire_shape("WGT_POLE_V1","diamond")

shape_map={}
for bone_name in CONTROL_MAIN:
    pb=arm.pose.bones[bone_name]
    if bone_name=="root":
        pb.custom_shape=shape_root
        pb.custom_shape_scale_xyz=(0.55,0.55,0.55)
    else:
        pb.custom_shape=shape_main
        scale=0.28 if bone_name!="CTRL_head" else 0.35
        pb.custom_shape_scale_xyz=(scale,scale,scale)
    shape_map[bone_name]=pb.custom_shape.name

for bone_name in CONTROL_IK:
    pb=arm.pose.bones[bone_name]
    pb.custom_shape=shape_ik
    scale=0.24 if "hand" in bone_name else 0.30
    pb.custom_shape_scale_xyz=(scale,scale,scale)
    shape_map[bone_name]=pb.custom_shape.name

for bone_name in CONTROL_POLES:
    pb=arm.pose.bones[bone_name]
    pb.custom_shape=shape_pole
    pb.custom_shape_scale_xyz=(0.18,0.18,0.18)
    shape_map[bone_name]=pb.custom_shape.name

arm.show_in_front=True
arm.data.display_type="OCTAHEDRAL"
arm["Rig_View_Default"]="CONTROLS_ONLY"
arm["Rig_Bone_Collections"]="CTRL_Main;CTRL_IK;CTRL_Poles;DEF_Skeleton"
arm["Retarget_Profile"]="SACKBOY_RETARGET_PROFILE_V1"
arm["Retarget_Source_Schema"]="MEDIAPIPE_POSE_33"
arm["Retarget_Target_Action"]="SACKBOY_JUMPSTYLE_RETARGET_V1"

bpy.context.view_layer.update()

# ---------- manifests ----------
rig_manifest={
    "manifest_version":"1.0",
    "generated_utc":datetime.now(timezone.utc).isoformat(),
    "armature":RIG,
    "bone_count":len(arm.data.bones),
    "controls":{
        "main":CONTROL_MAIN,
        "ik":CONTROL_IK,
        "poles":CONTROL_POLES,
    },
    "deform_bones":deform_names,
    "bone_collections":{
        name:{
            "visible":bool(collection.is_visible),
            "bones":sorted(bone.name for bone in collection.bones),
        }
        for name,collection in created_collections.items()
    },
    "bones":{
        bone.name:{
            "head_local":list(bone.head_local),
            "tail_local":list(bone.tail_local),
            "matrix_local":mlist(bone.matrix_local),
            "parent":bone.parent.name if bone.parent else "",
            "use_connect":bool(bone.use_connect),
            "use_deform":bool(bone.use_deform),
        }
        for bone in arm.data.bones
    },
    "constraints":constraint_snapshot(arm),
    "ik_switches":{
        name:float(arm[name])
        for name in ["IK_ARM_L","IK_ARM_R","IK_LEG_L","IK_LEG_R"]
    },
    "custom_shapes":shape_map,
}
rig_manifest_path=os.path.join(OUT,"SackboyRigManifestV1.json")
with open(rig_manifest_path,"w",encoding="utf-8") as file:
    json.dump(rig_manifest,file,indent=2)

profile={
    "profile_version":"1.0",
    "profile_name":"SACKBOY_RETARGET_PROFILE_V1",
    "source_schema":"MEDIAPIPE_POSE_33",
    "target_armature":RIG,
    "target_action_name":"SACKBOY_JUMPSTYLE_RETARGET_V1",
    "controls":{
        "root":"root",
        "pelvis":"CTRL_pelvis",
        "spine":"CTRL_spine",
        "chest":"CTRL_chest",
        "head":"CTRL_head",
        "left_hand_ik":"IK_hand.L",
        "right_hand_ik":"IK_hand.R",
        "left_elbow_pole":"POLE_elbow.L",
        "right_elbow_pole":"POLE_elbow.R",
        "left_foot_ik":"IK_foot.L",
        "right_foot_ik":"IK_foot.R",
        "left_knee_pole":"POLE_knee.L",
        "right_knee_pole":"POLE_knee.R",
    },
    "ik_switches":{
        "left_arm":"IK_ARM_L",
        "right_arm":"IK_ARM_R",
        "left_leg":"IK_LEG_L",
        "right_leg":"IK_LEG_R",
    },
    "source_landmarks":{
        "pelvis":["left_hip","right_hip"],
        "chest":["left_shoulder","right_shoulder","left_hip","right_hip"],
        "head":["nose","left_ear","right_ear"],
        "left_arm":["left_shoulder","left_elbow","left_wrist"],
        "right_arm":["right_shoulder","right_elbow","right_wrist"],
        "left_leg":["left_hip","left_knee","left_ankle","left_heel","left_foot_index"],
        "right_leg":["right_hip","right_knee","right_ankle","right_heel","right_foot_index"],
    },
    "rules":{
        "root_translation":"Smoothed pelvis midpoint relative to calibrated start",
        "pelvis_rotation":"Hip axis plus torso-up direction",
        "spine_chest":"Distribute torso orientation",
        "hands":"Wrist positions scaled into target rig space",
        "feet":"Contact-aware ankle/heel/foot-index targets",
        "elbow_poles":"Shoulder-elbow-wrist plane normal with temporal continuity",
        "knee_poles":"Hip-knee-ankle plane normal with temporal continuity",
        "foot_lock":"Lock support foot and solve root/pelvis around contact",
    },
}
profile_path=os.path.join(CONFIG_DIR,"SackboyRetargetProfileV1.json")
with open(profile_path,"w",encoding="utf-8") as file:
    json.dump(profile,file,indent=2)

# ---------- safety validation ----------
scene.frame_set(REST_FRAME)
bpy.context.view_layer.update()
rest_points_after={name:evaluated_points(bpy.data.objects[name],depsgraph) for name in MESH_TARGETS}
rest_errors={name:max_point_error(rest_points_before[name],rest_points_after[name]) for name in MESH_TARGETS}
rest_visual_max=max(rest_errors.values(),default=0.0)
if rest_visual_max>REST_TOL:
    raise RuntimeError(f"Safety stop: rig-display preparation changed the rest appearance: {rest_visual_max}")

rest_after=rest_bone_snapshot(arm)
rest_changes=[name for name in rest_before if rest_before[name]!=rest_after.get(name)]
if rest_changes:
    raise RuntimeError("Safety stop: rest bones changed: "+", ".join(rest_changes))

constraints_after=constraint_snapshot(arm)
constraint_changes=[] if constraints_before==constraints_after else ["constraint_snapshot_changed"]
if constraint_changes:
    raise RuntimeError("Safety stop: control constraints changed")

actions_after=sorted(action.name for action in bpy.data.actions)
action_changes=[] if actions_before==actions_after and arm.animation_data.action.name==active_action_before else ["action_state_changed"]
if action_changes:
    raise RuntimeError("Safety stop: animation actions changed")

bindings_after={name:mesh_binding_snapshot(bpy.data.objects[name]) for name in MESH_TARGETS}
binding_changes=[name for name in MESH_TARGETS if bindings_before[name]!=bindings_after[name]]
if binding_changes:
    raise RuntimeError("Safety stop: mesh binding/weight changes: "+", ".join(binding_changes))

# Protected objects may be animated. Their evaluated matrix_world is meaningful
# only when the before/after snapshots are taken at the same frame. The v1.1
# script captured before at original_frame but compared after at REST_FRAME,
# causing false changes for Empty, FINAL_ORBIT_RIG, and Lightning.
scene.frame_set(protected_check_frame)
bpy.context.view_layer.update()

protected_after={
    obj.name:object_snapshot(obj)
    for obj in bpy.data.objects
    if obj.name not in mutable_existing and obj.name not in SHAPE_OBJECTS
}
protected_change_details={}
before_names=set(protected_before)
after_names=set(protected_after)
if before_names!=after_names:
    protected_change_details["__object_set__"]={
        "added":sorted(after_names-before_names),
        "removed":sorted(before_names-after_names),
    }
for name in sorted(before_names&after_names):
    changed_keys=snapshot_diff_keys(protected_before[name],protected_after[name])
    if changed_keys:
        protected_change_details[name]=changed_keys

protected_changes=sorted(protected_change_details)
protected_diagnostic={
    "script_version":SCRIPT_VERSION,
    "comparison_frame":protected_check_frame,
    "before_object_count":len(protected_before),
    "after_object_count":len(protected_after),
    "change_count":len(protected_changes),
    "changes":protected_change_details,
}
with open(os.path.join(OUT,"ProtectedObjectDiagnosticV1_2.json"),"w",encoding="utf-8") as file:
    json.dump(protected_diagnostic,file,indent=2)
print(
    f"[protected_diagnostic] frame={protected_check_frame} "
    f"changes={protected_change_details}"
)
if protected_changes:
    readable=[]
    for name in protected_changes[:10]:
        readable.append(f"{name}:{protected_change_details[name]}")
    raise RuntimeError(
        "Safety stop: true protected object changes at normalized frame: "
        +", ".join(readable)
    )

collection_counts={
    name:len(collection.bones)
    for name,collection in created_collections.items()
}
custom_shaped=sum(1 for name in ALL_CONTROLS if arm.pose.bones[name].custom_shape is not None)
controls_only_default=(
    created_collections["CTRL_Main"].is_visible and
    created_collections["CTRL_IK"].is_visible and
    created_collections["CTRL_Poles"].is_visible and
    not created_collections["DEF_Skeleton"].is_visible
)
frame_range_changed=(scene.frame_start!=frame_start_before or scene.frame_end!=frame_end_before)

# The protected-object comparison already restored the user's original frame.
if scene.frame_current!=original_frame:
    raise RuntimeError("Safety stop: original frame was not restored")

status={
    "script_version":SCRIPT_VERSION,
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "saved_blend":False,
    "armature":RIG,
    "total_bone_count":len(arm.data.bones),
    "bone_collection_count":len(arm.data.collections),
    "bone_collection_counts":collection_counts,
    "bone_collection_assignment_checks":collection_assignment_checks,
    "bone_collection_assignment_checks_passed":collection_assignment_checks_passed,
    "bone_collection_assignments":{
        name:sorted(bones)
        for name,bones in actual_collection_bones.items()
    },
    "main_control_count":collection_counts["CTRL_Main"],
    "ik_control_count":collection_counts["CTRL_IK"],
    "pole_control_count":collection_counts["CTRL_Poles"],
    "deform_bone_count":collection_counts["DEF_Skeleton"],
    "custom_shaped_control_count":custom_shaped,
    "shape_object_count":len(SHAPE_OBJECTS),
    "shape_objects":SHAPE_OBJECTS,
    "controls_only_default":controls_only_default,
    "rest_visual_errors":rest_errors,
    "rest_visual_max_error":rest_visual_max,
    "rest_bone_change_count":len(rest_changes),
    "rest_bone_changes":rest_changes,
    "constraint_change_count":len(constraint_changes),
    "constraint_changes":constraint_changes,
    "action_change_count":len(action_changes),
    "action_changes":action_changes,
    "mesh_binding_snapshot_type":"POSE_INDEPENDENT_BINDING_SNAPSHOT",
    "mesh_binding_change_count":len(binding_changes),
    "mesh_binding_changes":binding_changes,
    "protected_comparison_frame":protected_check_frame,
    "protected_snapshot_mode":"SAME_FRAME_EVALUATED_STATE",
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "protected_change_details":protected_change_details,
    "scene_frame_range_changed":frame_range_changed,
    "original_frame_restored":scene.frame_current==original_frame,
    "retarget_profile_written":os.path.exists(profile_path),
    "retarget_profile_path":os.path.relpath(profile_path,ROOT),
    "rig_manifest_written":os.path.exists(rig_manifest_path),
    "rig_manifest_path":os.path.relpath(rig_manifest_path,ROOT),
    "active_action":arm.animation_data.action.name,
    "preserved_action_present":bpy.data.actions.get(PRESERVED_ACTION) is not None,
}

with open(os.path.join(OUT,"MotionRetargetPrepV1_2_status.json"),"w",encoding="utf-8") as file:
    json.dump(status,file,indent=2)
with open(os.path.join(OUT,"MotionRetargetPrepV1_2_report.txt"),"w",encoding="utf-8") as file:
    file.write("SACKBOY MOTION RETARGET PREP V1.2\n")
    file.write(f"bone_collections={collection_counts}\n")
    file.write(f"bone_collection_assignments_passed={collection_assignment_checks_passed}\n")
    file.write(f"custom_shaped_controls={custom_shaped}\n")
    file.write(f"controls_only_default={controls_only_default}\n")
    file.write(f"rest_visual_max_error={rest_visual_max:.12f}\n")
    file.write(f"rest_bone_changes={len(rest_changes)}\n")
    file.write(f"constraint_changes={len(constraint_changes)}\n")
    file.write(f"action_changes={len(action_changes)}\n")
    file.write(f"mesh_binding_changes={len(binding_changes)}\n")
    file.write(f"protected_comparison_frame={protected_check_frame}\n")
    file.write("protected_snapshot_mode=SAME_FRAME_EVALUATED_STATE\n")
    file.write(f"protected_changes={len(protected_changes)}\n")
    file.write(f"retarget_profile={status['retarget_profile_path']}\n")
    file.write(f"rig_manifest={status['rig_manifest_path']}\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"MotionRetargetPrepV1_2_status.json"),"w",encoding="utf-8") as file:
    json.dump(status,file,indent=2)

print(f"[version] motion retarget prep v{SCRIPT_VERSION}")
print(f"[collections] counts={collection_counts} assignments_passed={collection_assignment_checks_passed} controls_only={controls_only_default}")
print(f"[custom_shapes] assigned={custom_shaped} shape_objects={len(SHAPE_OBJECTS)}")
print(f"[rest] visual_error={rest_visual_max:.12f}")
print(f"[safety] rest_bone_changes={len(rest_changes)} constraints={len(constraint_changes)} actions={len(action_changes)} bindings={len(binding_changes)} protected={len(protected_changes)} frame_range_changed={frame_range_changed}")
print(f"[outputs] profile={status['retarget_profile_path']} manifest={status['rig_manifest_path']}")
print("[save] blend saved")
