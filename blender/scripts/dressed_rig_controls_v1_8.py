
import bpy, os, json, math, statistics
from mathutils import Vector, Matrix
from datetime import datetime, timezone

SCRIPT_VERSION="1.8"
ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","dressed_rig_controls_v1_8")
os.makedirs(OUT,exist_ok=True)

RIG="SACKBOY_RIG_PLACEMENT_V1"
OLD_ACTION="F2_DEFORMATION_TEST_V1_2"
NEW_ACTION="SACKBOY_CONTROL_RIG_VALIDATION_V1"
F2="F2"
HOODIE="Lowerpoly hoodie"
PANTS="Cargo pants"
EYES=["L.Eye","R.Eye"]
SHOES=["Plane.001","Plane.022"]
MESH_TARGETS=[F2,HOODIE,PANTS]+EYES+SHOES
DEFORMED_MESHES=[F2,HOODIE,PANTS]
ORIGINAL_BONES=[
    "root","pelvis","spine","chest","neck","head",
    "clavicle.L","upper_arm.L","forearm.L","hand.L",
    "clavicle.R","upper_arm.R","forearm.R","hand.R",
    "thigh.L","shin.L","foot.L","toe.L",
    "thigh.R","shin.R","foot.R","toe.R"
]
CONTROL_BONES=[
    "CTRL_pelvis","CTRL_spine","CTRL_chest","CTRL_head",
    "IK_hand.L","POLE_elbow.L","IK_hand.R","POLE_elbow.R",
    "IK_foot.L","POLE_knee.L","IK_foot.R","POLE_knee.R"
]
IK_SWITCHES=["IK_ARM_L","IK_ARM_R","IK_LEG_L","IK_LEG_R"]
TEST_FRAMES={
    300:"rest",
    310:"root_move",
    320:"torso_head",
    330:"arm_ik",
    340:"elbow_poles",
    350:"squat_planted",
    360:"left_kick",
    370:"right_kick",
    380:"weight_shift_planted",
    390:"rest",
}
STAGE9_FRAMES=[205,215,225,235,245,255,265]
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

def original_bone_snapshot(arm):
    return {
        n:{
            "head":list(arm.data.bones[n].head_local),
            "tail":list(arm.data.bones[n].tail_local),
            "matrix_local":mlist(arm.data.bones[n].matrix_local),
            "parent":arm.data.bones[n].parent.name if arm.data.bones[n].parent else "",
            "use_connect":bool(arm.data.bones[n].use_connect),
            "use_deform":bool(arm.data.bones[n].use_deform),
        }
        for n in ORIGINAL_BONES
    }

def vector_list_error(a,b):
    return max(abs(float(x)-float(y)) for x,y in zip(a,b))

def matrix_list_error(a,b):
    return max(abs(float(a[r][c])-float(b[r][c])) for r in range(4) for c in range(4))

def mesh_binding_snapshot(obj):
    # POSE_INDEPENDENT_BINDING_SNAPSHOT
    # matrix_world is intentionally excluded. It is evaluated from the active
    # armature action for bone-parented eyes/shoes and is not binding state.
    checksum=0.0
    membership_count=0
    for v in obj.data.vertices:
        for e in v.groups:
            membership_count+=1
            checksum+=(v.index+1)*(e.group+1)*float(e.weight)
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
        "weight_memberships":membership_count,
        "weight_checksum":checksum,
    }

def snapshot_diff_keys(before,after):
    keys=sorted(set(before)|set(after))
    return [key for key in keys if before.get(key)!=after.get(key)]

def eval_mesh(obj,dg):
    ev=obj.evaluated_get(dg)
    me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        mw=ev.matrix_world.copy()
        points=[mw@v.co for v in me.vertices]
        edges=[tuple(e.vertices) for e in me.edges]
        return points,edges
    finally:
        ev.to_mesh_clear()

def finite(points):
    return all(math.isfinite(x) for p in points for x in (p.x,p.y,p.z))

def bounds(points):
    mn=Vector((min(p.x for p in points),min(p.y for p in points),min(p.z for p in points)))
    mx=Vector((max(p.x for p in points),max(p.y for p in points),max(p.z for p in points)))
    return mn,mx,mx-mn

def centroid(points):
    if not points:
        return Vector((0,0,0))
    total=Vector((0,0,0))
    for p in points:
        total+=p
    return total/len(points)

def percentile(values,q):
    values=sorted(values)
    if not values:
        return 1.0
    pos=(len(values)-1)*q
    lo=int(math.floor(pos))
    hi=min(lo+1,len(values)-1)
    t=pos-lo
    return values[lo]*(1.0-t)+values[hi]*t

def max_point_error(a,b):
    if len(a)!=len(b):
        raise RuntimeError("Evaluated vertex count changed")
    return max(((p-q).length for p,q in zip(a,b)),default=0.0)

def weight_coverage(obj,deform_names):
    indices={obj.vertex_groups[n].index for n in deform_names if obj.vertex_groups.get(n)}
    unweighted=0
    invalid=0
    max_influences=0
    for v in obj.data.vertices:
        entries=[e for e in v.groups if e.group in indices and e.weight>1.0e-8]
        total=sum(e.weight for e in entries)
        max_influences=max(max_influences,len(entries))
        if not entries:
            unweighted+=1
        elif abs(total-1.0)>2.0e-4:
            invalid+=1
    return {"unweighted":unweighted,"invalid":invalid,"max_influences":max_influences}

def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode="QUATERNION"
        pb.location=(0.0,0.0,0.0)
        pb.rotation_quaternion=(1.0,0.0,0.0,0.0)
        pb.scale=(1.0,1.0,1.0)

def rest_world_matrix(arm,bone_name):
    return arm.matrix_world @ arm.data.bones[bone_name].matrix_local

def pivot_rotate(matrix_world,pivot_world,axis_world,angle):
    return (
        Matrix.Translation(pivot_world) @
        Matrix.Rotation(angle,4,Vector(axis_world)) @
        Matrix.Translation(-pivot_world) @
        matrix_world
    )

def set_control_world(arm,bone_name,world_matrix):
    arm.pose.bones[bone_name].matrix=arm.matrix_world.inverted() @ world_matrix

def translate_control(arm,bone_name,delta_world):
    set_control_world(arm,bone_name,Matrix.Translation(Vector(delta_world)) @ rest_world_matrix(arm,bone_name))

def rotate_control(arm,bone_name,axis_world,angle):
    base=rest_world_matrix(arm,bone_name)
    pivot=arm.matrix_world @ arm.data.bones[bone_name].head_local
    set_control_world(arm,bone_name,pivot_rotate(base,pivot,axis_world,angle))

def translate_rotate_control(arm,bone_name,delta_world,axis_world,angle):
    base=rest_world_matrix(arm,bone_name)
    pivot=arm.matrix_world @ arm.data.bones[bone_name].head_local
    rotated=pivot_rotate(base,pivot,axis_world,angle)
    set_control_world(arm,bone_name,Matrix.Translation(Vector(delta_world)) @ rotated)

def set_ik_switches(arm,arm_l=0.0,arm_r=0.0,leg_l=0.0,leg_r=0.0):
    values={
        "IK_ARM_L":float(arm_l),
        "IK_ARM_R":float(arm_r),
        "IK_LEG_L":float(leg_l),
        "IK_LEG_R":float(leg_r),
    }
    for name,value in values.items():
        arm[name]=value

def key_ik_switches(arm,frame):
    for name in IK_SWITCHES:
        arm.keyframe_insert(data_path=f'["{name}"]',frame=frame,group="IK_SWITCHES")

def key_controls(arm,frame):
    names=["root"]+CONTROL_BONES
    for name in names:
        pb=arm.pose.bones[name]
        pb.rotation_mode="QUATERNION"
        pb.keyframe_insert(data_path="location",frame=frame,group=name)
        pb.keyframe_insert(data_path="rotation_quaternion",frame=frame,group=name)
        pb.keyframe_insert(data_path="scale",frame=frame,group=name)
    key_ik_switches(arm,frame)

def drive_constraint_influence(constraint,arm,property_name):
    fcurve=constraint.driver_add("influence")
    driver=fcurve.driver
    driver.type="SCRIPTED"
    var=driver.variables.new()
    var.name="switch"
    var.type="SINGLE_PROP"
    target=var.targets[0]
    target.id=arm
    target.data_path=f'["{property_name}"]'
    driver.expression="switch"
    return fcurve

def pose_chain_score(arm,names):
    score=0.0
    for name in names:
        pb=arm.pose.bones[name]
        rest=arm.data.bones[name].matrix_local
        for r in range(4):
            for c in range(4):
                d=pb.matrix[r][c]-rest[r][c]
                score+=d*d
    return score

def choose_pole_angle(arm,constraint,chain_names):
    # Sweep the full circle and select the pole angle that most closely
    # reproduces the original rest matrices, including roll/twist.
    candidates=[-math.pi+(2.0*math.pi*i/32.0) for i in range(32)]
    best=None
    for angle in candidates:
        constraint.pole_angle=angle
        bpy.context.view_layer.update()
        score=pose_chain_score(arm,chain_names)
        if best is None or score<best[0]:
            best=(score,angle)
    constraint.pole_angle=best[1]
    bpy.context.view_layer.update()
    return {"angle":best[1],"rest_matrix_score":best[0]}

def add_copy_constraint(pb,name,target_bone,ctype="COPY_ROTATION"):
    c=pb.constraints.new(ctype)
    c.name=name
    c.target=arm
    c.subtarget=target_bone
    c.target_space="POSE"
    c.owner_space="POSE"
    return c

# ---------- preflight ----------
arm=bpy.data.objects.get(RIG)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG}")
for name in MESH_TARGETS:
    if bpy.data.objects.get(name) is None:
        raise RuntimeError(f"Missing target {name}")
if len(arm.data.bones)!=22:
    raise RuntimeError("Safety stop: expected 22-bone rig before controls")
for name in ORIGINAL_BONES:
    if arm.data.bones.get(name) is None:
        raise RuntimeError(f"Missing original bone {name}")
for name in CONTROL_BONES:
    if arm.data.bones.get(name) is not None:
        raise RuntimeError(f"Safety stop: control bone already exists: {name}")
for name in IK_SWITCHES:
    if name in arm:
        raise RuntimeError(f"Safety stop: IK switch property already exists: {name}")
if bpy.data.actions.get(NEW_ACTION):
    raise RuntimeError(f"Safety stop: validation action already exists: {NEW_ACTION}")
if not arm.animation_data or not arm.animation_data.action or arm.animation_data.action.name!=OLD_ACTION:
    raise RuntimeError(f"Safety stop: expected active action {OLD_ACTION}")

deform_names=[b.name for b in arm.data.bones if b.use_deform]
if len(deform_names)!=21:
    raise RuntimeError("Safety stop: expected 21 deform bones")

f2=bpy.data.objects[F2]
hoodie=bpy.data.objects[HOODIE]
pants=bpy.data.objects[PANTS]
for obj in [f2,hoodie,pants]:
    mods=[m for m in obj.modifiers if m.type=="ARMATURE" and m.object==arm]
    if len(mods)!=1:
        raise RuntimeError(f"Safety stop: {obj.name} must have exactly one rig Armature modifier")
for eye in EYES:
    obj=bpy.data.objects[eye]
    if not (obj.parent==arm and obj.parent_type=="BONE" and obj.parent_bone=="head"):
        raise RuntimeError(f"Safety stop: {eye} is not attached to head")
shoe_map={"Plane.001":"foot.L","Plane.022":"foot.R"}
for shoe,bone in shoe_map.items():
    obj=bpy.data.objects[shoe]
    if not (obj.parent==arm and obj.parent_type=="BONE" and obj.parent_bone==bone):
        raise RuntimeError(f"Safety stop: {shoe} is not attached to {bone}")

scene=bpy.context.scene
original_frame=scene.frame_current
frame_start_before=scene.frame_start
frame_end_before=scene.frame_end
mutable=set(MESH_TARGETS+[RIG])
protected_before={o.name:object_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
original_bones_before=original_bone_snapshot(arm)
mesh_bindings_before={name:mesh_binding_snapshot(bpy.data.objects[name]) for name in MESH_TARGETS}
old_action=arm.animation_data.action
old_action.use_fake_user=True

# ---------- Stage 9 dressed review ----------
dg=bpy.context.evaluated_depsgraph_get()
scene.frame_set(1)
bpy.context.view_layer.update()
# Exact pre-control rest reference for body, clothing, eyes, and shoes.
pre_control_rest_points={}
for name in MESH_TARGETS:
    pre_control_rest_points[name]=eval_mesh(bpy.data.objects[name],dg)[0]

stage9_rest={}
stage9_edges={}
stage9_edge_lengths={}
stage9_dims={}
for name in DEFORMED_MESHES:
    pts,edges=eval_mesh(bpy.data.objects[name],dg)
    stage9_rest[name]=pts
    stage9_edges[name]=edges
    stage9_edge_lengths[name]=[(pts[a]-pts[b]).length for a,b in edges]
    stage9_dims[name]=bounds(pts)[2]

stage9_metrics={}
stage9_pass=True
for frame in STAGE9_FRAMES:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    frame_metrics={}
    for name in DEFORMED_MESHES:
        pts,edges=eval_mesh(bpy.data.objects[name],dg)
        mn,mx,dim=bounds(pts)
        ratios=[dim[i]/stage9_dims[name][i] if stage9_dims[name][i]>1.0e-8 else 1.0 for i in range(3)]

        edge_ratios=[]
        for idx,(a,b) in enumerate(edges):
            rest_len=stage9_edge_lengths[name][idx]
            if rest_len<=1.0e-8:
                continue
            edge_ratios.append((pts[a]-pts[b]).length/rest_len)

        p001=percentile(edge_ratios,0.001)
        p01=percentile(edge_ratios,0.01)
        median_ratio=percentile(edge_ratios,0.50)
        p99=percentile(edge_ratios,0.99)
        p999=percentile(edge_ratios,0.999)
        extreme_count=sum(1 for ratio in edge_ratios if ratio<0.002 or ratio>8.0)
        extreme_fraction=(extreme_count/len(edge_ratios)) if edge_ratios else 0.0

        # Garments can contain tiny, doubled, or folded edges that make a
        # single absolute minimum misleading. Use bounds plus percentile-based
        # topology checks and allow only a very small extreme-edge fraction.
        passed=(
            finite(pts) and
            max(ratios)<2.5 and min(ratios)>0.20 and
            p001>0.001 and p999<10.0 and
            extreme_fraction<0.02 and
            mn.z>-1.0
        )
        stage9_pass=stage9_pass and passed
        frame_metrics[name]={
            "finite":finite(pts),
            "dimension_ratios":ratios,
            "edge_ratio_p001":p001,
            "edge_ratio_p01":p01,
            "edge_ratio_median":median_ratio,
            "edge_ratio_p99":p99,
            "edge_ratio_p999":p999,
            "extreme_edge_count":extreme_count,
            "extreme_edge_fraction":extreme_fraction,
            "passed":passed,
        }
    stage9_metrics[str(frame)]=frame_metrics

weight_checks={name:weight_coverage(bpy.data.objects[name],deform_names) for name in [F2,HOODIE,PANTS]}
for name,metrics in weight_checks.items():
    if metrics["unweighted"] or metrics["invalid"]:
        stage9_pass=False

# Always write and print Stage 9 diagnostics before any safety stop.
stage9_diagnostic={
    "script_version":SCRIPT_VERSION,
    "frames":STAGE9_FRAMES,
    "metrics":stage9_metrics,
    "weight_checks":weight_checks,
    "passed":stage9_pass,
}
with open(os.path.join(OUT,"Stage9DressedReviewDiagnosticV1_8.json"),"w",encoding="utf-8") as f:
    json.dump(stage9_diagnostic,f,indent=2)
print(f"[stage9_diagnostic] passed={stage9_pass} metrics={stage9_metrics} weights={weight_checks}")

if not stage9_pass:
    failed=[]
    for frame,frame_metrics in stage9_metrics.items():
        for name,metrics in frame_metrics.items():
            if not metrics["passed"]:
                failed.append(f"{frame}:{name}")
    for name,metrics in weight_checks.items():
        if metrics["unweighted"] or metrics["invalid"]:
            failed.append(f"weights:{name}")
    raise RuntimeError("Safety stop: Stage 9 dressed-character review failed: "+", ".join(failed))

stage9_corrections=[]

# Return to rest before building controls.
scene.frame_set(1)
bpy.context.view_layer.update()

# ---------- Stage 10 create controls ----------
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb=arm.data.edit_bones

def duplicate_control(new_name,source_name,parent_name="root"):
    src=eb[source_name]
    b=eb.new(new_name)
    b.head=src.head.copy()
    b.tail=src.tail.copy()
    b.roll=src.roll
    b.use_deform=False
    b.use_connect=False
    if parent_name:
        b.parent=eb[parent_name]
    return b

duplicate_control("CTRL_pelvis","pelvis")
duplicate_control("CTRL_spine","spine")
duplicate_control("CTRL_chest","chest")
duplicate_control("CTRL_head","head")
duplicate_control("IK_hand.L","hand.L")
duplicate_control("IK_hand.R","hand.R")
duplicate_control("IK_foot.L","foot.L")
duplicate_control("IK_foot.R","foot.R")

inv=arm.matrix_world.inverted()
def add_pole(name,joint_local,offset_world):
    joint_world=arm.matrix_world@joint_local
    head=inv@(joint_world+Vector(offset_world))
    b=eb.new(name)
    b.head=head
    b.tail=head+Vector((0,0,0.12))
    b.use_deform=False
    b.use_connect=False
    b.parent=eb["root"]
    return b

add_pole("POLE_elbow.L",eb["forearm.L"].head,(0,-0.55,0))
add_pole("POLE_elbow.R",eb["forearm.R"].head,(0,-0.55,0))
add_pole("POLE_knee.L",eb["shin.L"].head,(0,-0.55,0))
add_pole("POLE_knee.R",eb["shin.R"].head,(0,-0.55,0))

# The original pelvis may be anchored/connected in a way that prevents any
# pose-space Copy Location/Transforms constraint from translating it. Make the
# non-deforming CTRL_pelvis its direct parent instead. Head, tail, roll, and
# armature-space rest matrix remain unchanged; only the control hierarchy changes.
pelvis_edit=eb["pelvis"]
pelvis_rest_head=pelvis_edit.head.copy()
pelvis_rest_tail=pelvis_edit.tail.copy()
pelvis_rest_roll=float(pelvis_edit.roll)

# Critical order for Blender 5.1:
# 1. Disconnect from the old parent before assigning the new parent.
# 2. Assign CTRL_pelvis.
# 3. Explicitly restore armature-space head, tail, and roll.
# Assigning the new parent while use_connect is still True snaps the pelvis to
# the new parent's tail, which is exactly what stopped v1.5.
pelvis_edit.use_connect=False
pelvis_edit.parent=eb["CTRL_pelvis"]
pelvis_edit.head=pelvis_rest_head
pelvis_edit.tail=pelvis_rest_tail
pelvis_edit.roll=pelvis_rest_roll

pelvis_edit_geometry_error=max(
    (pelvis_edit.head-pelvis_rest_head).length,
    (pelvis_edit.tail-pelvis_rest_tail).length,
    abs(float(pelvis_edit.roll)-pelvis_rest_roll),
)
print(f"[pelvis_edit_reparent] geometry_error={pelvis_edit_geometry_error}")
if pelvis_edit_geometry_error>1.0e-8:
    raise RuntimeError("Safety stop: pelvis rest geometry changed after ordered reparent/restore")

bpy.ops.object.mode_set(mode="POSE")
reset_pose(arm)

# IK is intentionally disabled at rest. This guarantees that adding the
# control rig cannot alter the approved neutral character. The switches are
# animated to 1.0 only on validation frames that exercise IK.
set_ik_switches(arm,0.0,0.0,0.0,0.0)
for property_name in IK_SWITCHES:
    ui=arm.id_properties_ui(property_name)
    ui.update(min=0.0,max=1.0,soft_min=0.0,soft_max=1.0,description="0 = FK/rest, 1 = IK control")
bpy.context.view_layer.update()

constraint_names=[]
driver_names=[]

# Center controls. CTRL_pelvis drives the body through direct bone parenting.
c=add_copy_constraint(arm.pose.bones["spine"],"CTRL_SPINE","CTRL_spine","COPY_ROTATION"); constraint_names.append(c.name)
c=add_copy_constraint(arm.pose.bones["chest"],"CTRL_CHEST","CTRL_chest","COPY_ROTATION"); constraint_names.append(c.name)
c=add_copy_constraint(arm.pose.bones["head"],"CTRL_HEAD","CTRL_head","COPY_ROTATION"); constraint_names.append(c.name)

pole_results={}
for side in ("L","R"):
    arm_switch=f"IK_ARM_{side}"
    leg_switch=f"IK_LEG_{side}"

    ik=arm.pose.bones[f"forearm.{side}"].constraints.new("IK")
    ik.name=f"IK_ARM.{side}"
    ik.target=arm
    ik.subtarget=f"IK_hand.{side}"
    ik.pole_target=arm
    ik.pole_subtarget=f"POLE_elbow.{side}"
    ik.chain_count=2
    ik.use_stretch=False
    drive_constraint_influence(ik,arm,arm_switch)
    constraint_names.append(ik.name)
    driver_names.append(f"{ik.name}:{arm_switch}")

    cr=add_copy_constraint(arm.pose.bones[f"hand.{side}"],f"CTRL_HAND_ROT.{side}",f"IK_hand.{side}","COPY_ROTATION")
    drive_constraint_influence(cr,arm,arm_switch)
    constraint_names.append(cr.name)
    driver_names.append(f"{cr.name}:{arm_switch}")

    leg=arm.pose.bones[f"shin.{side}"].constraints.new("IK")
    leg.name=f"IK_LEG.{side}"
    leg.target=arm
    leg.subtarget=f"IK_foot.{side}"
    leg.pole_target=arm
    leg.pole_subtarget=f"POLE_knee.{side}"
    leg.chain_count=2
    leg.use_stretch=False
    drive_constraint_influence(leg,arm,leg_switch)
    constraint_names.append(leg.name)
    driver_names.append(f"{leg.name}:{leg_switch}")

    fr=add_copy_constraint(arm.pose.bones[f"foot.{side}"],f"CTRL_FOOT_ROT.{side}",f"IK_foot.{side}","COPY_ROTATION")
    drive_constraint_influence(fr,arm,leg_switch)
    constraint_names.append(fr.name)
    driver_names.append(f"{fr.name}:{leg_switch}")

bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.objects.active=arm
reset_pose(arm)
bpy.context.view_layer.update()

# Choose pole angles with IK temporarily enabled, then return every switch to
# zero before the rest-appearance comparison.
set_ik_switches(arm,1.0,1.0,1.0,1.0)
bpy.context.view_layer.update()
for side in ("L","R"):
    pole_results[f"arm.{side}"]=choose_pole_angle(
        arm,arm.pose.bones[f"forearm.{side}"].constraints[f"IK_ARM.{side}"],
        [f"upper_arm.{side}",f"forearm.{side}"]
    )
    pole_results[f"leg.{side}"]=choose_pole_angle(
        arm,arm.pose.bones[f"shin.{side}"].constraints[f"IK_LEG.{side}"],
        [f"thigh.{side}",f"shin.{side}"]
    )

# Validate that the default FK/rest state is visually identical.
scene.frame_set(1)
reset_pose(arm)
set_ik_switches(arm,0.0,0.0,0.0,0.0)
bpy.context.view_layer.update()
control_rest_before=pre_control_rest_points
control_rest_after={name:eval_mesh(bpy.data.objects[name],dg)[0] for name in MESH_TARGETS}
rest_errors={name:max_point_error(control_rest_before[name],control_rest_after[name]) for name in MESH_TARGETS}
rest_visual_max=max(rest_errors.values(),default=0.0)
rest_check=rest_visual_max<=REST_TOL
if not rest_check:
    raise RuntimeError(f"Safety stop: controls changed rest appearance; max_error={rest_visual_max}")

# Validate original-bone geometry and the one intentional hierarchy change.
original_bones_after=original_bone_snapshot(arm)
original_bone_changes=[]
allowed_hierarchy_changes=[]

for name in ORIGINAL_BONES:
    before=original_bones_before[name]
    after=original_bones_after[name]

    # Rest geometry, roll/orientation, and deform flags are immutable.
    head_error=vector_list_error(before["head"],after["head"])
    tail_error=vector_list_error(before["tail"],after["tail"])
    matrix_error=matrix_list_error(before["matrix_local"],after["matrix_local"])
    geometry_changed=(
        head_error>1.0e-7 or
        tail_error>1.0e-7 or
        matrix_error>1.0e-7 or
        before["use_deform"]!=after["use_deform"]
    )
    if geometry_changed:
        original_bone_changes.append(
            f"{name}:rest_geometry(head={head_error},tail={tail_error},matrix={matrix_error})"
        )
        continue

    if name=="pelvis":
        hierarchy_ok=(after["parent"]=="CTRL_pelvis" and after["use_connect"] is False)
        if not hierarchy_ok:
            original_bone_changes.append("pelvis:control_parent")
        elif before["parent"]!=after["parent"] or before["use_connect"]!=after["use_connect"]:
            allowed_hierarchy_changes.append("pelvis->CTRL_pelvis")
    elif before["parent"]!=after["parent"] or before["use_connect"]!=after["use_connect"]:
        original_bone_changes.append(f"{name}:hierarchy")

if original_bone_changes:
    raise RuntimeError("Safety stop: unintended original-bone changes: "+", ".join(original_bone_changes))
if allowed_hierarchy_changes!=["pelvis->CTRL_pelvis"]:
    raise RuntimeError("Safety stop: expected exactly the pelvis control-parent hierarchy change")

# Direct hierarchy propagation probe. This must pass before the validation action
# is created, and the exact rest pose must be restored afterward.
scene.frame_set(1)
reset_pose(arm)
set_ik_switches(arm,0.0,0.0,0.0,0.0)
bpy.context.view_layer.update()

pelvis_parent_checks={
    "pelvis_parent_is_control":arm.data.bones["pelvis"].parent==arm.data.bones["CTRL_pelvis"],
    "pelvis_not_connected":arm.data.bones["pelvis"].use_connect is False,
    "control_parent_is_root":arm.data.bones["CTRL_pelvis"].parent==arm.data.bones["root"],
    "control_non_deforming":arm.data.bones["CTRL_pelvis"].use_deform is False,
}

pelvis_probe_before=(arm.matrix_world@arm.pose.bones["pelvis"].head).copy()
ctrl_probe_before=arm.pose.bones["CTRL_pelvis"].matrix.copy()
translate_control(arm,"CTRL_pelvis",(0.0,0.0,-0.05))
bpy.context.view_layer.update()
pelvis_probe_after=(arm.matrix_world@arm.pose.bones["pelvis"].head).copy()
pelvis_probe_movement=(pelvis_probe_after-pelvis_probe_before).length

arm.pose.bones["CTRL_pelvis"].matrix=ctrl_probe_before
bpy.context.view_layer.update()
pelvis_probe_restored=(arm.matrix_world@arm.pose.bones["pelvis"].head).copy()
pelvis_probe_restore_error=(pelvis_probe_restored-pelvis_probe_before).length

pelvis_parent_checks["probe_movement"]=(pelvis_probe_movement>0.049)
pelvis_parent_checks["probe_restored"]=(pelvis_probe_restore_error<1.0e-6)
pelvis_parent_checks_passed=all(pelvis_parent_checks.values())

print(f"[pelvis_parent_probe] passed={pelvis_parent_checks_passed} movement={pelvis_probe_movement} restore_error={pelvis_probe_restore_error} checks={pelvis_parent_checks}")
if not pelvis_parent_checks_passed:
    raise RuntimeError("Safety stop: CTRL_pelvis hierarchy failed the direct propagation probe")

# ---------- Stage 11 validation action ----------
arm.animation_data_create()
arm.animation_data.action=None
new_action=bpy.data.actions.new(NEW_ACTION)
arm.animation_data.action=new_action

REST_KEY_FRAMES=[1,120,290,300,390,400]
for frame in REST_KEY_FRAMES:
    scene.frame_set(frame)
    reset_pose(arm)
    set_ik_switches(arm,0.0,0.0,0.0,0.0)
    key_controls(arm,frame)

# 310 root movement.
scene.frame_set(310); reset_pose(arm)
set_ik_switches(arm,0.0,0.0,0.0,0.0)
translate_control(arm,"root",(0.12,0.0,0.08))
key_controls(arm,310)

# 320 torso/head.
scene.frame_set(320); reset_pose(arm)
set_ik_switches(arm,0.0,0.0,0.0,0.0)
rotate_control(arm,"CTRL_spine",(0,0,1),math.radians(8))
rotate_control(arm,"CTRL_chest",(0,0,1),math.radians(14))
rotate_control(arm,"CTRL_head",(0,0,1),math.radians(-10))
key_controls(arm,320)

# 330 arm IK reach.
scene.frame_set(330); reset_pose(arm)
set_ik_switches(arm,1.0,1.0,0.0,0.0)
translate_control(arm,"IK_hand.L",(0.10,-0.28,-0.10))
translate_control(arm,"IK_hand.R",(-0.10,-0.28,-0.10))
translate_control(arm,"POLE_elbow.L",(0,-0.12,0.05))
translate_control(arm,"POLE_elbow.R",(0,-0.12,0.05))
key_controls(arm,330)

# 340 pole steering.
scene.frame_set(340); reset_pose(arm)
set_ik_switches(arm,1.0,1.0,0.0,0.0)
translate_control(arm,"IK_hand.L",(0.05,-0.24,-0.08))
translate_control(arm,"IK_hand.R",(-0.05,-0.24,-0.08))
translate_control(arm,"POLE_elbow.L",(0,-0.18,0.16))
translate_control(arm,"POLE_elbow.R",(0,-0.18,-0.10))
key_controls(arm,340)

# 350 squat with both feet planted.
scene.frame_set(350); reset_pose(arm)
set_ik_switches(arm,0.0,0.0,1.0,1.0)
translate_control(arm,"CTRL_pelvis",(0,-0.03,-0.22))
translate_control(arm,"POLE_knee.L",(0,-0.16,0))
translate_control(arm,"POLE_knee.R",(0,-0.16,0))
key_controls(arm,350)

# 360 left kick; right foot planted.
scene.frame_set(360); reset_pose(arm)
set_ik_switches(arm,1.0,1.0,1.0,1.0)
translate_rotate_control(arm,"CTRL_pelvis",(0,-0.02,-0.07),(0,0,1),math.radians(-5))
translate_control(arm,"IK_foot.L",(-0.04,-0.36,0.30))
translate_control(arm,"POLE_knee.L",(0,-0.20,0.08))
translate_control(arm,"POLE_knee.R",(0,-0.12,0))
translate_control(arm,"IK_hand.L",(0.02,-0.12,0.05))
translate_control(arm,"IK_hand.R",(-0.02,0.10,-0.04))
key_controls(arm,360)

# 370 right kick; left foot planted.
scene.frame_set(370); reset_pose(arm)
set_ik_switches(arm,1.0,1.0,1.0,1.0)
translate_rotate_control(arm,"CTRL_pelvis",(0,-0.02,-0.07),(0,0,1),math.radians(5))
translate_control(arm,"IK_foot.R",(0.04,-0.36,0.30))
translate_control(arm,"POLE_knee.R",(0,-0.20,0.08))
translate_control(arm,"POLE_knee.L",(0,-0.12,0))
translate_control(arm,"IK_hand.R",(-0.02,-0.12,0.05))
translate_control(arm,"IK_hand.L",(0.02,0.10,-0.04))
key_controls(arm,370)

# 380 planted-foot lateral weight shift.
scene.frame_set(380); reset_pose(arm)
set_ik_switches(arm,0.0,0.0,1.0,1.0)
translate_rotate_control(arm,"CTRL_pelvis",(0.12,0,-0.12),(0,0,1),math.radians(-7))
rotate_control(arm,"CTRL_chest",(0,0,1),math.radians(8))
translate_control(arm,"POLE_knee.L",(0,-0.14,0))
translate_control(arm,"POLE_knee.R",(0,-0.14,0))
key_controls(arm,380)

arm["Rig_Control_Set"]="root; "+ "; ".join(CONTROL_BONES)
arm["Rig_Validation_Action"]=NEW_ACTION
arm["Rig_Validation_Frames"]="300 rest; 310 root; 320 torso; 330 arm IK; 340 poles; 350 squat; 360 left kick; 370 right kick; 380 weight shift; 390 rest"

# ---------- automated Stage 11 checks ----------
scene.frame_set(300)
bpy.context.view_layer.update()
stage11_rest_points={name:eval_mesh(bpy.data.objects[name],dg)[0] for name in MESH_TARGETS}
stage11_rest_centers={name:centroid(stage11_rest_points[name]) for name in MESH_TARGETS}
stage11_rest_dims={name:bounds(stage11_rest_points[name])[2] for name in DEFORMED_MESHES}

pose_metrics={}
all_pose_geometry=True
for frame,name in TEST_FRAMES.items():
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    obj_metrics={}
    for obj_name in DEFORMED_MESHES:
        pts,_=eval_mesh(bpy.data.objects[obj_name],dg)
        mn,mx,dim=bounds(pts)
        ratios=[dim[i]/stage11_rest_dims[obj_name][i] if stage11_rest_dims[obj_name][i]>1.0e-8 else 1.0 for i in range(3)]
        passed=finite(pts) and max(ratios)<2.5 and min(ratios)>0.25 and mn.z>-1.2
        all_pose_geometry=all_pose_geometry and passed
        obj_metrics[obj_name]={
            "finite":finite(pts),
            "dimension_ratios":ratios,
            "max_vertex_movement":max_point_error(stage11_rest_points[obj_name],pts),
            "passed":passed,
        }
    pose_metrics[str(frame)]={"name":name,"objects":obj_metrics}

def object_center_at(name,frame):
    scene.frame_set(frame); bpy.context.view_layer.update()
    return centroid(eval_mesh(bpy.data.objects[name],dg)[0])

def bone_head_world(name,frame):
    scene.frame_set(frame); bpy.context.view_layer.update()
    return arm.matrix_world@arm.pose.bones[name].head

def bone_tail_world(name,frame):
    scene.frame_set(frame); bpy.context.view_layer.update()
    return arm.matrix_world@arm.pose.bones[name].tail

root_move=(object_center_at(F2,310)-stage11_rest_centers[F2]).length
head_move=(object_center_at("L.Eye",320)-stage11_rest_centers["L.Eye"]).length

arm_reach={}
for side in ("L","R"):
    wrist=bone_head_world(f"hand.{side}",330)
    target=bone_head_world(f"IK_hand.{side}",330)
    arm_reach[side]=(wrist-target).length

shoe_rest_centers={name:stage11_rest_centers[name] for name in SHOES}
squat_shoe_move={name:(object_center_at(name,350)-shoe_rest_centers[name]).length for name in SHOES}
squat_body_centroid_move=(object_center_at(F2,350)-stage11_rest_centers[F2]).length

left_kick_move=(object_center_at("Plane.001",360)-shoe_rest_centers["Plane.001"]).length
left_support_move=(object_center_at("Plane.022",360)-shoe_rest_centers["Plane.022"]).length
right_kick_move=(object_center_at("Plane.022",370)-shoe_rest_centers["Plane.022"]).length
right_support_move=(object_center_at("Plane.001",370)-shoe_rest_centers["Plane.001"]).length
plant_moves={name:(object_center_at(name,380)-shoe_rest_centers[name]).length for name in SHOES}
plant_body_centroid_move=(object_center_at(F2,380)-stage11_rest_centers[F2]).length

# Pelvis controls primarily move the hip/torso while planted IK counter-moves the
# legs. A full-body centroid can therefore remain nearly stationary even when the
# control works correctly. Validate the control itself and the driven pelvis bone.
pelvis_rest_head=bone_head_world("pelvis",300)
ctrl_pelvis_rest_head=bone_head_world("CTRL_pelvis",300)

squat_pelvis_head=bone_head_world("pelvis",350)
squat_ctrl_head=bone_head_world("CTRL_pelvis",350)
squat_pelvis_move=(squat_pelvis_head-pelvis_rest_head).length
squat_ctrl_move=(squat_ctrl_head-ctrl_pelvis_rest_head).length
squat_follow_error=(squat_pelvis_head-squat_ctrl_head).length

shift_pelvis_head=bone_head_world("pelvis",380)
shift_ctrl_head=bone_head_world("CTRL_pelvis",380)
shift_pelvis_move=(shift_pelvis_head-pelvis_rest_head).length
shift_ctrl_move=(shift_ctrl_head-ctrl_pelvis_rest_head).length
shift_follow_error=(shift_pelvis_head-shift_ctrl_head).length

control_checks={
    "root_moves_character":root_move>0.05,
    "torso_head_control_moves_head":head_move>0.01,
    "arm_ik_reaches_targets":all(v<0.12 for v in arm_reach.values()),
    "squat_feet_planted":all(v<0.12 for v in squat_shoe_move.values()),
    "squat_pelvis_control_moves":squat_ctrl_move>0.15,
    "squat_pelvis_bone_follows":squat_pelvis_move>0.12 and squat_follow_error<0.02,
    "left_kick_moves_left_foot":left_kick_move>0.12,
    "left_support_foot_planted":left_support_move<0.15,
    "right_kick_moves_right_foot":right_kick_move>0.12,
    "right_support_foot_planted":right_support_move<0.15,
    "weight_shift_feet_planted":all(v<0.12 for v in plant_moves.values()),
    "weight_shift_pelvis_control_moves":shift_ctrl_move>0.10,
    "weight_shift_pelvis_bone_follows":shift_pelvis_move>0.08 and shift_follow_error<0.02,
}
automatic_checks=all_pose_geometry and all(control_checks.values())

stage11_diagnostic={
    "script_version":SCRIPT_VERSION,
    "pose_geometry_passed":all_pose_geometry,
    "control_checks":control_checks,
    "measurements":{
        "root_character_movement":root_move,
        "head_movement":head_move,
        "arm_reach_error":arm_reach,
        "squat_shoe_movement":squat_shoe_move,
        "squat_body_centroid_movement":squat_body_centroid_move,
        "squat_control_movement":squat_ctrl_move,
        "squat_pelvis_bone_movement":squat_pelvis_move,
        "squat_pelvis_follow_error":squat_follow_error,
        "left_kick_movement":left_kick_move,
        "left_support_movement":left_support_move,
        "right_kick_movement":right_kick_move,
        "right_support_movement":right_support_move,
        "weight_shift_shoe_movement":plant_moves,
        "weight_shift_body_centroid_movement":plant_body_centroid_move,
        "weight_shift_control_movement":shift_ctrl_move,
        "weight_shift_pelvis_bone_movement":shift_pelvis_move,
        "weight_shift_pelvis_follow_error":shift_follow_error,
    },
    "passed":automatic_checks,
}
with open(os.path.join(OUT,"Stage11ControlDiagnosticV1_8.json"),"w",encoding="utf-8") as f:
    json.dump(stage11_diagnostic,f,indent=2)
print(f"[stage11_diagnostic] passed={automatic_checks} checks={control_checks} measurements={stage11_diagnostic['measurements']}")

if not automatic_checks:
    failed=[k for k,v in control_checks.items() if not v]
    if not all_pose_geometry:
        failed.append("pose_geometry")
    raise RuntimeError("Safety stop: Stage 11 automatic checks failed: "+", ".join(failed))

# ---------- final unchanged-resource validation ----------
scene.frame_set(original_frame)
bpy.context.view_layer.update()

mesh_bindings_after={name:mesh_binding_snapshot(bpy.data.objects[name]) for name in MESH_TARGETS}
mesh_binding_change_details={
    name:snapshot_diff_keys(mesh_bindings_before[name],mesh_bindings_after[name])
    for name in MESH_TARGETS
    if mesh_bindings_before[name]!=mesh_bindings_after[name]
}
mesh_binding_changes=sorted(mesh_binding_change_details)

binding_diagnostic={
    "script_version":SCRIPT_VERSION,
    "snapshot_type":"POSE_INDEPENDENT_BINDING_SNAPSHOT",
    "active_action_before":OLD_ACTION,
    "active_action_after":arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else "",
    "original_frame":original_frame,
    "change_count":len(mesh_binding_changes),
    "changes":mesh_binding_change_details,
}
with open(os.path.join(OUT,"MeshBindingDiagnosticV1_8.json"),"w",encoding="utf-8") as f:
    json.dump(binding_diagnostic,f,indent=2)
print(f"[binding_diagnostic] changes={mesh_binding_change_details}")

if mesh_binding_changes:
    readable=[f"{name}({','.join(mesh_binding_change_details[name])})" for name in mesh_binding_changes]
    raise RuntimeError("Safety stop: true structural mesh binding/weight changes: "+", ".join(readable))

protected_after={o.name:object_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
protected_changes=[]
if set(protected_before)!=set(protected_after):
    protected_changes.append("object_set_changed")
for name in sorted(set(protected_before)&set(protected_after)):
    if protected_before[name]!=protected_after[name]:
        protected_changes.append(name)
if protected_changes:
    raise RuntimeError("Safety stop: protected object changes: "+", ".join(protected_changes[:10]))

if bpy.data.actions.get(OLD_ACTION) is None:
    raise RuntimeError("Safety stop: previous deformation action was lost")
if arm.animation_data.action is None or arm.animation_data.action.name!=NEW_ACTION:
    raise RuntimeError("Safety stop: validation action is not active")

frame_range_changed=(scene.frame_start!=frame_start_before or scene.frame_end!=frame_end_before)

status={
    "script_version":SCRIPT_VERSION,
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "stage9_dressed_review_passed":stage9_pass,
    "stage9_review_frames":STAGE9_FRAMES,
    "stage9_metrics":stage9_metrics,
    "stage9_weight_checks":weight_checks,
    "stage9_corrections_applied":stage9_corrections,
    "stage9_corrections_applied_count":len(stage9_corrections),
    "control_bones":CONTROL_BONES,
    "control_bone_count":len(CONTROL_BONES),
    "total_bone_count_after":len(arm.data.bones),
    "control_constraints":constraint_names,
    "control_constraint_count":len(constraint_names),
    "pelvis_control_mode":"DIRECT_BONE_PARENT_ORDERED_RESTORE",
    "pelvis_edit_reparent_geometry_error":pelvis_edit_geometry_error,
    "allowed_original_hierarchy_changes":allowed_hierarchy_changes,
    "allowed_original_hierarchy_change_count":len(allowed_hierarchy_changes),
    "pelvis_parent_checks":pelvis_parent_checks,
    "pelvis_parent_checks_passed":pelvis_parent_checks_passed,
    "pelvis_parent_probe_movement":pelvis_probe_movement,
    "pelvis_parent_probe_restore_error":pelvis_probe_restore_error,
    "ik_switch_properties":IK_SWITCHES,
    "ik_switch_property_count":len(IK_SWITCHES),
    "constraint_drivers":driver_names,
    "constraint_driver_count":len(driver_names),
    "default_ik_switch_values":{name:float(arm[name]) for name in IK_SWITCHES},
    "pole_angle_results":pole_results,
    "control_rest_visual_errors":rest_errors,
    "control_rest_visual_max_error":rest_visual_max,
    "control_rest_visual_check_passed":rest_check,
    "original_bone_change_count":len(original_bone_changes),
    "original_bone_changes":original_bone_changes,
    "preserved_deformation_action":OLD_ACTION,
    "active_validation_action":NEW_ACTION,
    "stage11_test_frames":{str(k):v for k,v in TEST_FRAMES.items()},
    "stage11_pose_metrics":pose_metrics,
    "stage11_control_checks":control_checks,
    "stage11_automatic_checks_passed":automatic_checks,
    "stage11_measurements":stage11_diagnostic["measurements"],
    "mesh_binding_snapshot_type":"POSE_INDEPENDENT_BINDING_SNAPSHOT",
    "mesh_binding_change_count":len(mesh_binding_changes),
    "mesh_binding_changes":mesh_binding_changes,
    "mesh_binding_change_details":mesh_binding_change_details,
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "scene_frame_start_before":frame_start_before,
    "scene_frame_start_after":scene.frame_start,
    "scene_frame_end_before":frame_end_before,
    "scene_frame_end_after":scene.frame_end,
    "scene_frame_range_changed":frame_range_changed,
    "original_frame_restored":scene.frame_current==original_frame,
    "created_backup_blend_files":0,
}

with open(os.path.join(OUT,"DressedRigControlsV1_8_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"DressedRigControlsV1_8_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY DRESSED RIG REVIEW + CONTROLS V1.8\n")
    f.write(f"stage9_passed={stage9_pass}\n")
    f.write(f"stage9_corrections={len(stage9_corrections)}\n")
    f.write(f"control_bones={len(CONTROL_BONES)}\n")
    f.write(f"control_constraints={len(constraint_names)}\n")
    f.write("pelvis_control_mode=DIRECT_BONE_PARENT_ORDERED_RESTORE\n")
    f.write(f"pelvis_edit_reparent_geometry_error={pelvis_edit_geometry_error}\n")
    f.write(f"pelvis_parent_probe_movement={pelvis_probe_movement}\n")
    f.write(f"pelvis_parent_probe_restore_error={pelvis_probe_restore_error}\n")
    f.write(f"allowed_hierarchy_changes={allowed_hierarchy_changes}\n")
    f.write(f"ik_switch_properties={len(IK_SWITCHES)}\n")
    f.write(f"constraint_drivers={len(driver_names)}\n")
    f.write(f"total_bones={len(arm.data.bones)}\n")
    f.write(f"rest_visual_error={rest_visual_max:.12f}\n")
    f.write(f"stage11_checks={automatic_checks}\n")
    f.write(f"control_checks={control_checks}\n")
    f.write(f"measurements={status['stage11_measurements']}\n")
    f.write(f"original_bone_changes={len(original_bone_changes)}\n")
    f.write(f"mesh_binding_changes={len(mesh_binding_changes)}\n")
    f.write(f"protected_changes={len(protected_changes)}\n")
with open(os.path.join(OUT,"Dressed_Rig_Controls_V1_8.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy Dressed Rig Review + Controls v1\n\n")
    f.write(f"- Stage 9 dressed review: **{stage9_pass}**\n")
    f.write(f"- Stage 9 corrections applied: **{len(stage9_corrections)}**\n")
    f.write(f"- New non-deforming control bones: **{len(CONTROL_BONES)}**\n")
    f.write(f"- New control constraints: **{len(constraint_names)}**\n")
    f.write("- Pelvis control mode: **direct parent with ordered disconnect/reparent/restore**\n")
    f.write(f"- Edit-mode pelvis geometry error: **{pelvis_edit_geometry_error:.12f}**\n")
    f.write(f"- Pelvis hierarchy propagation probe: **{pelvis_parent_checks_passed}**\n")
    f.write(f"- Allowed original hierarchy changes: **{len(allowed_hierarchy_changes)}**\n")
    f.write(f"- IK/FK switch properties: **{len(IK_SWITCHES)}**\n")
    f.write(f"- Constraint influence drivers: **{len(driver_names)}**\n")
    f.write(f"- Total bones: **{len(arm.data.bones)}**\n")
    f.write(f"- Rest visual error: **{rest_visual_max:.12f}**\n")
    f.write(f"- Stage 11 automatic checks: **{automatic_checks}**\n")
    f.write(f"- Original rest-bone changes: **{len(original_bone_changes)}**\n")
    f.write(f"- Mesh binding changes: **{len(mesh_binding_changes)}**\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**\n\n")
    f.write("Manual Stage 11 review is required at frames 300-390 before motion extraction begins.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"DressedRigControlsV1_8_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print(f"[version] dressed rig controls v{SCRIPT_VERSION}")
print(f"[stage9] passed={stage9_pass} corrections={len(stage9_corrections)}")
print(f"[stage10] controls={len(CONTROL_BONES)} constraints={len(constraint_names)} pelvis_mode=DIRECT_BONE_PARENT_ORDERED_RESTORE switches={len(IK_SWITCHES)} drivers={len(driver_names)} total_bones={len(arm.data.bones)}")
print(f"[rest] visual_error={rest_visual_max:.12f}")
print(f"[stage11] automatic_checks={automatic_checks} control_checks={control_checks}")
print(f"[safety] original_bone_changes={len(original_bone_changes)} mesh_binding_changes={len(mesh_binding_changes)} protected_changes={len(protected_changes)} frame_range_changed={frame_range_changed}")
print("[save] blend saved")
