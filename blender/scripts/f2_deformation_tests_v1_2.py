
import bpy, os, json, math
from mathutils import Vector, Matrix, Quaternion
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","f2_deformation_tests_v1_2")
os.makedirs(OUT,exist_ok=True)

RIG="SACKBOY_RIG_PLACEMENT_V1"
F2="F2"
SCRIPT_VERSION="1.2"
ACTION_NAME="F2_DEFORMATION_TEST_V1_2"
OTHER_TARGETS=["Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
TEST_FRAMES={
    205:"shoulders",
    215:"elbows",
    225:"wrists",
    235:"squat",
    245:"left_kick",
    255:"right_kick",
    265:"torso",
}
REST_FRAMES=[1,200,210,220,230,240,250,260,270]
PRODUCTION_CHECK_FRAMES=[1,30,60,90,120]

def mlist(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def obj_snapshot(obj):
    ad=obj.animation_data
    return {
        "type":obj.type,
        "data":getattr(obj.data,"name",""),
        "matrix":mlist(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "drivers":len(ad.drivers) if ad else 0,
        "nla":len(ad.nla_tracks) if ad else 0,
        "modifiers":[(m.name,m.type) for m in obj.modifiers],
        "constraints":[c.name for c in obj.constraints],
    }

def rest_snapshot(arm):
    return {
        b.name:{
            "head":list(b.head_local),
            "tail":list(b.tail_local),
            "parent":b.parent.name if b.parent else "",
            "use_connect":bool(b.use_connect),
            "use_deform":bool(b.use_deform),
        }
        for b in arm.data.bones
    }

def eval_mesh(obj,dg):
    ev=obj.evaluated_get(dg)
    me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        mw=ev.matrix_world.copy()
        points=[mw@v.co for v in me.vertices]
        edges=[(e.vertices[0],e.vertices[1]) for e in me.edges]
        return points,edges
    finally:
        ev.to_mesh_clear()

def bounds(points):
    mn=Vector((min(p.x for p in points),min(p.y for p in points),min(p.z for p in points)))
    mx=Vector((max(p.x for p in points),max(p.y for p in points),max(p.z for p in points)))
    return mn,mx,mx-mn

def max_point_error(a,b):
    if len(a)!=len(b):
        raise RuntimeError("Vertex count changed")
    return max(((p-q).length for p,q in zip(a,b)),default=0.0)

def finite_points(points):
    return all(math.isfinite(v) for p in points for v in (p.x,p.y,p.z))

def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode="QUATERNION"
        pb.location=(0.0,0.0,0.0)
        pb.rotation_quaternion=(1.0,0.0,0.0,0.0)
        pb.scale=(1.0,1.0,1.0)

def apply_world_axis_rotation(arm,bone_name,axis_world,angle_radians):
    pb=arm.pose.bones[bone_name]
    bone=arm.data.bones[bone_name]
    axis_arm=arm.matrix_world.inverted().to_3x3() @ Vector(axis_world)
    axis_local=bone.matrix_local.to_3x3().inverted() @ axis_arm
    axis_local.normalize()
    q=Quaternion(axis_local,angle_radians)
    pb.rotation_mode="QUATERNION"
    pb.rotation_quaternion=q @ pb.rotation_quaternion

def key_all_pose_bones(arm,frame):
    for pb in arm.pose.bones:
        pb.keyframe_insert(data_path="location",frame=frame)
        pb.keyframe_insert(data_path="rotation_quaternion",frame=frame)
        pb.keyframe_insert(data_path="scale",frame=frame)

def set_pose(arm,pose_name):
    reset_pose(arm)
    d=math.radians

    if pose_name=="shoulders":
        apply_world_axis_rotation(arm,"upper_arm.L",(0,1,0),-d(24))
        apply_world_axis_rotation(arm,"upper_arm.R",(0,1,0), d(24))

    elif pose_name=="elbows":
        apply_world_axis_rotation(arm,"upper_arm.L",(0,1,0),-d(10))
        apply_world_axis_rotation(arm,"upper_arm.R",(0,1,0), d(10))
        apply_world_axis_rotation(arm,"forearm.L",(0,1,0),-d(55))
        apply_world_axis_rotation(arm,"forearm.R",(0,1,0), d(55))

    elif pose_name=="wrists":
        apply_world_axis_rotation(arm,"forearm.L",(0,1,0),-d(25))
        apply_world_axis_rotation(arm,"forearm.R",(0,1,0), d(25))
        apply_world_axis_rotation(arm,"hand.L",(0,1,0), d(30))
        apply_world_axis_rotation(arm,"hand.R",(0,1,0),-d(30))

    elif pose_name=="squat":
        apply_world_axis_rotation(arm,"pelvis",(1,0,0),-d(6))
        apply_world_axis_rotation(arm,"thigh.L",(1,0,0),-d(28))
        apply_world_axis_rotation(arm,"thigh.R",(1,0,0),-d(28))
        apply_world_axis_rotation(arm,"shin.L",(1,0,0), d(48))
        apply_world_axis_rotation(arm,"shin.R",(1,0,0), d(48))
        apply_world_axis_rotation(arm,"foot.L",(1,0,0),-d(18))
        apply_world_axis_rotation(arm,"foot.R",(1,0,0),-d(18))

    elif pose_name=="left_kick":
        apply_world_axis_rotation(arm,"pelvis",(0,0,1),-d(5))
        apply_world_axis_rotation(arm,"thigh.L",(1,0,0),-d(46))
        apply_world_axis_rotation(arm,"shin.L",(1,0,0), d(18))
        apply_world_axis_rotation(arm,"foot.L",(1,0,0), d(10))
        apply_world_axis_rotation(arm,"thigh.R",(1,0,0),-d(8))
        apply_world_axis_rotation(arm,"shin.R",(1,0,0), d(16))
        apply_world_axis_rotation(arm,"upper_arm.L",(0,1,0), d(12))
        apply_world_axis_rotation(arm,"upper_arm.R",(0,1,0),-d(12))

    elif pose_name=="right_kick":
        apply_world_axis_rotation(arm,"pelvis",(0,0,1), d(5))
        apply_world_axis_rotation(arm,"thigh.R",(1,0,0),-d(46))
        apply_world_axis_rotation(arm,"shin.R",(1,0,0), d(18))
        apply_world_axis_rotation(arm,"foot.R",(1,0,0), d(10))
        apply_world_axis_rotation(arm,"thigh.L",(1,0,0),-d(8))
        apply_world_axis_rotation(arm,"shin.L",(1,0,0), d(16))
        apply_world_axis_rotation(arm,"upper_arm.L",(0,1,0), d(12))
        apply_world_axis_rotation(arm,"upper_arm.R",(0,1,0),-d(12))

    elif pose_name=="torso":
        apply_world_axis_rotation(arm,"spine",(1,0,0),-d(9))
        apply_world_axis_rotation(arm,"chest",(0,0,1), d(12))
        apply_world_axis_rotation(arm,"neck",(0,0,1),-d(5))
        apply_world_axis_rotation(arm,"head",(1,0,0), d(6))

    else:
        raise RuntimeError(f"Unknown pose {pose_name}")

# ---------- preflight ----------
arm=bpy.data.objects.get(RIG)
f2=bpy.data.objects.get(F2)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG}")
if f2 is None or f2.type!="MESH":
    raise RuntimeError("Missing F2 mesh")
if bpy.data.actions.get(ACTION_NAME):
    raise RuntimeError(f"Safety stop: action {ACTION_NAME} already exists")
if arm.animation_data and (arm.animation_data.action or len(arm.animation_data.drivers) or len(arm.animation_data.nla_tracks)):
    raise RuntimeError("Safety stop: rig already contains animation data")
arm_mods=[m for m in f2.modifiers if m.type=="ARMATURE" and m.object==arm]
if len(arm_mods)!=1:
    raise RuntimeError("Safety stop: F2 is not bound to the approved rig exactly once")
if f2.parent is not None:
    raise RuntimeError("Safety stop: F2 should remain unparented")

root=arm.data.bones.get("root")
if root is None or root.use_deform:
    raise RuntimeError("Safety stop: root must exist and remain non-deforming")
if f2.vertex_groups.get("root") is not None:
    raise RuntimeError("Safety stop: F2 unexpectedly has a root deform group")

mutable={RIG,F2}
protected_before={o.name:obj_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
rest_before=rest_snapshot(arm)
scene=bpy.context.scene
original_frame=scene.frame_current
frame_start_before=scene.frame_start
frame_end_before=scene.frame_end

dg=bpy.context.evaluated_depsgraph_get()
scene.frame_set(1)
reset_pose(arm)
bpy.context.view_layer.update()
rest_points,edges=eval_mesh(f2,dg)
rest_min,rest_max,rest_dim=bounds(rest_points)
rest_edge_lengths=[]
for a,b in edges:
    l=(rest_points[a]-rest_points[b]).length
    rest_edge_lengths.append(l)

# ---------- create action ----------
arm.animation_data_create()
action=bpy.data.actions.new(ACTION_NAME)
arm.animation_data.action=action

for frame in REST_FRAMES:
    scene.frame_set(frame)
    reset_pose(arm)
    key_all_pose_bones(arm,frame)

for frame,pose_name in TEST_FRAMES.items():
    scene.frame_set(frame)
    set_pose(arm,pose_name)
    key_all_pose_bones(arm,frame)

arm["F2_Deformation_Test_Action"]=ACTION_NAME
arm["F2_Deformation_Test_Frames"]="205 shoulders; 215 elbows; 225 wrists; 235 squat; 245 left kick; 255 right kick; 265 torso; 270 rest"

# ---------- validate production rest ----------
production_errors={}
for frame in PRODUCTION_CHECK_FRAMES:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pts,_=eval_mesh(f2,dg)
    production_errors[str(frame)]=max_point_error(rest_points,pts)
production_rest=max(production_errors.values(),default=0.0)<=1.0e-5

# ---------- validate each pose ----------
pose_metrics={}
all_pose_checks=True
for frame,pose_name in TEST_FRAMES.items():
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pts,pose_edges=eval_mesh(f2,dg)
    mn,mx,dim=bounds(pts)

    finite=finite_points(pts)
    max_disp=max_point_error(rest_points,pts)
    dim_ratios=[
        dim[i]/rest_dim[i] if rest_dim[i]>1.0e-8 else 1.0
        for i in range(3)
    ]

    max_edge_ratio=0.0
    min_edge_ratio=1.0e9
    for idx,(a,b) in enumerate(pose_edges):
        rest_len=rest_edge_lengths[idx]
        if rest_len<=1.0e-9:
            continue
        ratio=(pts[a]-pts[b]).length/rest_len
        max_edge_ratio=max(max_edge_ratio,ratio)
        min_edge_ratio=min(min_edge_ratio,ratio)

    passed=(
        finite and
        0.015<max_disp<2.5 and
        max(dim_ratios)<2.2 and
        min(dim_ratios)>0.35 and
        max_edge_ratio<5.0 and
        min_edge_ratio>0.02 and
        mn.z>-1.0
    )
    all_pose_checks=all_pose_checks and passed
    pose_metrics[str(frame)]={
        "name":pose_name,
        "finite":finite,
        "max_vertex_displacement":max_disp,
        "bounds_min":list(mn),
        "bounds_max":list(mx),
        "dimension_ratios":dim_ratios,
        "max_edge_stretch_ratio":max_edge_ratio,
        "min_edge_stretch_ratio":min_edge_ratio,
        "passed":passed,
    }

if not production_rest:
    raise RuntimeError(f"Safety stop: production frame rest validation failed: {production_errors}")
if not all_pose_checks:
    failed=[k for k,v in pose_metrics.items() if not v["passed"]]
    raise RuntimeError("Safety stop: deformation geometry checks failed at frames "+", ".join(failed))

# Return to the exact original scene frame before comparing protected objects.
# Lightning, FINAL_ORBIT_RIG, and other scene helpers are legitimately animated,
# so comparing their evaluated matrices at a test frame would be a false positive.
scene.frame_set(original_frame)
bpy.context.view_layer.update()

# ---------- safety snapshots ----------
rest_after=rest_snapshot(arm)
rest_changes=[n for n in rest_before if rest_before[n]!=rest_after.get(n)]
if rest_changes:
    raise RuntimeError("Safety stop: armature rest bones changed: "+", ".join(rest_changes))

other_arm_mods=sum(
    1 for n in OTHER_TARGETS
    for m in bpy.data.objects[n].modifiers if m.type=="ARMATURE"
)
if other_arm_mods:
    raise RuntimeError("Safety stop: a non-F2 target was bound")

protected_after={o.name:obj_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
protected_changes=[]
if set(protected_before)!=set(protected_after):
    protected_changes.append("object_set_changed")
for n in sorted(set(protected_before)&set(protected_after)):
    if protected_before[n]!=protected_after[n]:
        protected_changes.append(n)
if protected_changes:
    raise RuntimeError("Safety stop: protected object changes: "+", ".join(protected_changes[:10]))

# Re-assert the user's original frame after all safety checks.
scene.frame_set(original_frame)
bpy.context.view_layer.update()

status={
    "script_version":SCRIPT_VERSION,
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "action_name":ACTION_NAME,
    "test_pose_count":len(TEST_FRAMES),
    "test_frames":{str(k):v for k,v in TEST_FRAMES.items()},
    "rest_frames":REST_FRAMES,
    "production_check_frames":PRODUCTION_CHECK_FRAMES,
    "production_frame_errors":production_errors,
    "production_frames_rest_verified":production_rest,
    "pose_metrics":pose_metrics,
    "all_pose_geometry_checks_passed":all_pose_checks,
    "root_bone_use_deform":root.use_deform,
    "root_vertex_group_present":f2.vertex_groups.get("root") is not None,
    "armature_rest_change_count":len(rest_changes),
    "armature_rest_changes":rest_changes,
    "other_target_armature_modifier_count":other_arm_mods,
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "scene_frame_start_before":frame_start_before,
    "scene_frame_start_after":scene.frame_start,
    "scene_frame_start_changed":scene.frame_start!=frame_start_before,
    "scene_frame_end_before":frame_end_before,
    "scene_frame_end_after":scene.frame_end,
    "scene_frame_end_changed":scene.frame_end!=frame_end_before,
    "original_frame_restored":scene.frame_current==original_frame,
    "created_backup_blend_files":0,
}

with open(os.path.join(OUT,"F2DeformationTestsV1_2_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"F2DeformationTestsV1_2_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY F2 DEFORMATION TESTS V1.2\n")
    f.write(f"action={ACTION_NAME}\n")
    f.write(f"production_frames_rest={production_rest}\n")
    f.write(f"all_pose_checks={all_pose_checks}\n")
    f.write(f"root_use_deform={root.use_deform}\n")
    f.write(f"root_vertex_group_present={f2.vertex_groups.get('root') is not None}\n")
    f.write(f"rest_bone_changes={len(rest_changes)}\n")
    f.write(f"other_targets_bound={other_arm_mods}\n")
    f.write(f"protected_changes={len(protected_changes)}\n")
    for frame in sorted(TEST_FRAMES):
        f.write(f"frame {frame}: {pose_metrics[str(frame)]}\n")
with open(os.path.join(OUT,"F2_Deformation_Tests_V1_2.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy F2 Deformation Tests v1\n\n")
    f.write(f"- Action: `{ACTION_NAME}`\n")
    f.write(f"- Production frames remain rest: **{production_rest}**\n")
    f.write(f"- All automatic geometry checks: **{all_pose_checks}**\n")
    f.write(f"- Root bone deforming: **{root.use_deform}**\n")
    f.write(f"- Other character targets bound: **{other_arm_mods}**\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**\n\n")
    f.write("## Inspection frames\n\n")
    for frame,name in TEST_FRAMES.items():
        f.write(f"- `{frame}` — {name}; passed={pose_metrics[str(frame)]['passed']}\n")
    f.write("\nTemporarily hide clothing, eyes, and shoes in the viewport to inspect F2 clearly.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"F2DeformationTestsV1_2_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print(f"[version] F2 deformation tests v{SCRIPT_VERSION}")
print("[deformation] F2 test action created")
print(f"[action] {ACTION_NAME}")
print(f"[production] rest_verified={production_rest} errors={production_errors}")
print(f"[poses] passed={all_pose_checks} metrics={pose_metrics}")
print(f"[root] use_deform={root.use_deform} vertex_group_present={f2.vertex_groups.get('root') is not None}")
print(f"[safety] rest_changes={len(rest_changes)} other_targets_bound={other_arm_mods} protected_changes={len(protected_changes)} frame_range={scene.frame_start}-{scene.frame_end}")
print("[save] blend saved")
