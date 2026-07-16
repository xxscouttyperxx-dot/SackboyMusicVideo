
import bpy, os, json, math
from mathutils import Vector, Matrix
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","f2_bind_weights_v1")
os.makedirs(OUT,exist_ok=True)

RIG_NAME="SACKBOY_RIG_PLACEMENT_V1"
F2_NAME="F2"
OTHER_TARGETS=["Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
REST_TOL=1.0e-5
WEIGHT_TOL=2.0e-4

def mlist(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def object_snapshot(obj):
    ad=obj.animation_data
    return {
        "type":obj.type,
        "data":getattr(obj.data,"name",""),
        "matrix_world":mlist(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "driver_count":len(ad.drivers) if ad else 0,
        "nla_count":len(ad.nla_tracks) if ad else 0,
        "modifiers":[(m.name,m.type) for m in obj.modifiers],
        "constraints":[c.name for c in obj.constraints],
        "vertex_groups":[g.name for g in obj.vertex_groups] if hasattr(obj,"vertex_groups") else [],
    }

def rest_bone_snapshot(arm):
    return {
        b.name:{
            "head":list(b.head_local),
            "tail":list(b.tail_local),
            "roll":float(getattr(b,"roll",0.0)),
            "parent":b.parent.name if b.parent else "",
            "use_connect":bool(b.use_connect),
            "use_deform":bool(b.use_deform),
        }
        for b in arm.data.bones
    }

def evaluated_world_vertices(obj,dg):
    ev=obj.evaluated_get(dg)
    me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        mw=ev.matrix_world.copy()
        return [mw@v.co for v in me.vertices]
    finally:
        ev.to_mesh_clear()

def max_error(a,b):
    if len(a)!=len(b):
        raise RuntimeError(f"Vertex count changed: {len(a)} -> {len(b)}")
    return max(((p-q).length for p,q in zip(a,b)),default=0.0)

def pose_is_rest(arm):
    for pb in arm.pose.bones:
        if pb.matrix_basis != Matrix.Identity(4):
            # Matrix exact comparisons can be noisy.
            vals=[abs(pb.matrix_basis[r][c]-(1.0 if r==c else 0.0)) for r in range(4) for c in range(4)]
            if max(vals)>1.0e-7:
                return False,pb.name,max(vals)
    return True,"",0.0

def clear_binding(obj):
    for m in list(obj.modifiers):
        if m.type=="ARMATURE":
            obj.modifiers.remove(m)
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)

def weight_metrics(obj,deform_names):
    deform_indices={obj.vertex_groups[n].index for n in deform_names if obj.vertex_groups.get(n)}
    unweighted=[]
    invalid=[]
    maximum=0
    influence_hist={}
    group_counts={n:0 for n in deform_names}
    group_weight_sums={n:0.0 for n in deform_names}

    index_to_name={g.index:g.name for g in obj.vertex_groups}
    for v in obj.data.vertices:
        entries=[g for g in v.groups if g.group in deform_indices and g.weight>1.0e-8]
        total=sum(g.weight for g in entries)
        count=len(entries)
        maximum=max(maximum,count)
        influence_hist[str(count)]=influence_hist.get(str(count),0)+1
        if count==0:
            unweighted.append(v.index)
        elif abs(total-1.0)>WEIGHT_TOL:
            invalid.append((v.index,total))
        for g in entries:
            name=index_to_name[g.group]
            group_counts[name]+=1
            group_weight_sums[name]+=g.weight
    return {
        "unweighted":unweighted,
        "invalid":invalid,
        "maximum":maximum,
        "histogram":influence_hist,
        "group_vertex_counts":group_counts,
        "group_weight_sums":group_weight_sums,
    }

def normalize_weights(obj,deform_names):
    valid_indices={obj.vertex_groups[n].index for n in deform_names if obj.vertex_groups.get(n)}
    groups_by_index={g.index:g for g in obj.vertex_groups}
    for v in obj.data.vertices:
        entries=[(g.group,g.weight) for g in v.groups if g.group in valid_indices and g.weight>1.0e-12]
        total=sum(w for _,w in entries)
        if total<=0:
            continue
        if abs(total-1.0)>1.0e-7:
            for idx,wgt in entries:
                groups_by_index[idx].add([v.index],wgt/total,"REPLACE")

def segment_distance(point,a,b):
    ab=b-a
    denom=ab.length_squared
    if denom<=1.0e-12:
        return (point-a).length
    t=max(0.0,min(1.0,(point-a).dot(ab)/denom))
    closest=a+t*ab
    return (point-closest).length

def fallback_weights(obj,arm,deform_names):
    clear_binding(obj)
    mod=obj.modifiers.new(name="SACKBOY_RIG_DEFORM",type="ARMATURE")
    mod.object=arm
    mod.use_deform_preserve_volume=True

    groups={name:obj.vertex_groups.new(name=name) for name in deform_names}
    bones={}
    for name in deform_names:
        b=arm.data.bones[name]
        bones[name]=(arm.matrix_world@b.head_local,arm.matrix_world@b.tail_local)

    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    center_x=sum(p.x for p in points)/len(points)

    leg_prefix=("thigh.","shin.","foot.","toe.")
    arm_prefix=("clavicle.","upper_arm.","forearm.","hand.")

    for v,p in zip(obj.data.vertices,points):
        scored=[]
        for name,(a,b) in bones.items():
            d=segment_distance(p,a,b)

            # Strongly discourage opposite-side limb crossover.
            if name.endswith(".L") and p.x>center_x+0.025:
                d+=abs(p.x-center_x)*4.0+0.35
            elif name.endswith(".R") and p.x<center_x-0.025:
                d+=abs(p.x-center_x)*4.0+0.35

            # Region penalties keep distant limb families out of torso/head.
            if name.startswith(leg_prefix):
                if p.z>1.30:
                    d+=(p.z-1.30)*3.0
            elif name.startswith(arm_prefix):
                if p.z<1.22:
                    d+=(1.22-p.z)*3.0
                if p.z>2.05:
                    d+=(p.z-2.05)*3.0
            elif name in {"head","neck"}:
                if p.z<1.62:
                    d+=(1.62-p.z)*3.0
            elif name in {"pelvis","spine","chest"}:
                pass

            scored.append((d,name))

        scored.sort(key=lambda x:x[0])
        chosen=scored[:4]
        raw=[1.0/((d+0.035)**4) for d,_ in chosen]
        total=sum(raw)
        for (_,name),rw in zip(chosen,raw):
            groups[name].add([v.index],rw/total,"REPLACE")

    normalize_weights(obj,deform_names)
    return mod

# ---------- preflight ----------
f2=bpy.data.objects.get(F2_NAME)
arm=bpy.data.objects.get(RIG_NAME)
if f2 is None or f2.type!="MESH":
    raise RuntimeError("Missing mesh object F2")
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG_NAME}")
for n in OTHER_TARGETS:
    if bpy.data.objects.get(n) is None:
        raise RuntimeError(f"Missing protected character target: {n}")
if sum(1 for o in bpy.data.objects if o.type=="ARMATURE")!=1:
    raise RuntimeError("Safety stop: expected exactly one armature")
if len(arm.data.bones)!=22:
    raise RuntimeError("Safety stop: expected the approved 22-bone rig")
if f2.data.shape_keys:
    raise RuntimeError("Safety stop: F2 unexpectedly has shape keys")
if len(f2.vertex_groups)!=0:
    raise RuntimeError("Safety stop: F2 already has vertex groups")
if any(m.type=="ARMATURE" for m in f2.modifiers):
    raise RuntimeError("Safety stop: F2 already has an Armature modifier")
if f2.parent is not None:
    raise RuntimeError("Safety stop: F2 already has a parent")
if arm.animation_data and (arm.animation_data.action or len(arm.animation_data.drivers) or len(arm.animation_data.nla_tracks)):
    raise RuntimeError("Safety stop: rig already contains animation data")

rest_ok,bad_pose,bad_delta=pose_is_rest(arm)
if not rest_ok:
    raise RuntimeError(f"Safety stop: pose bone {bad_pose} is not in rest pose ({bad_delta})")

deform_names=[b.name for b in arm.data.bones if b.use_deform]
if len(deform_names)!=21:
    raise RuntimeError(f"Safety stop: expected 21 deform bones, found {len(deform_names)}")

mutable={F2_NAME,RIG_NAME}
protected_before={o.name:object_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
other_before={n:object_snapshot(bpy.data.objects[n]) for n in OTHER_TARGETS}
rest_before=rest_bone_snapshot(arm)
rig_action_before=arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else ""

scene=bpy.context.scene
original_frame=scene.frame_current
dg=bpy.context.evaluated_depsgraph_get()
visual_before=evaluated_world_vertices(f2,dg)
f2_matrix_before=f2.matrix_world.copy()
f2_parent_before=f2.parent

# ---------- automatic weights ----------
weighting_method="AUTOMATIC_BONE_HEAT"
auto_error=""
try:
    bpy.ops.object.select_all(action="DESELECT")
    f2.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    # Keep the generated groups/modifier, but leave F2 unparented.
    world=f2.matrix_world.copy()
    f2.parent=None
    f2.matrix_parent_inverse=Matrix.Identity(4)
    f2.matrix_world=world

    arm_mods=[m for m in f2.modifiers if m.type=="ARMATURE"]
    if len(arm_mods)!=1:
        raise RuntimeError(f"automatic weighting created {len(arm_mods)} Armature modifiers")
    arm_mod=arm_mods[0]
    arm_mod.name="SACKBOY_RIG_DEFORM"
    arm_mod.object=arm
    arm_mod.use_deform_preserve_volume=True

    for name in deform_names:
        if f2.vertex_groups.get(name) is None:
            f2.vertex_groups.new(name=name)

    normalize_weights(f2,deform_names)
    metrics=weight_metrics(f2,deform_names)
    if metrics["unweighted"] or metrics["invalid"]:
        raise RuntimeError(
            f"automatic result invalid: unweighted={len(metrics['unweighted'])}, "
            f"invalid_sums={len(metrics['invalid'])}"
        )
except Exception as exc:
    auto_error=str(exc)
    weighting_method="DETERMINISTIC_NEAREST_BONE_FALLBACK"
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode!="OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    f2.parent=None
    f2.matrix_parent_inverse=Matrix.Identity(4)
    f2.matrix_world=f2_matrix_before
    arm_mod=fallback_weights(f2,arm,deform_names)
    metrics=weight_metrics(f2,deform_names)
    if metrics["unweighted"] or metrics["invalid"]:
        raise RuntimeError(
            f"fallback weighting invalid: unweighted={len(metrics['unweighted'])}, "
            f"invalid_sums={len(metrics['invalid'])}"
        )

bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
visual_after=evaluated_world_vertices(f2,dg)
rest_error=max_error(visual_before,visual_after)
if rest_error>REST_TOL:
    raise RuntimeError(f"Safety stop: F2 moved in rest pose; error={rest_error}")

# ---------- post-validation ----------
arm_mods=[m for m in f2.modifiers if m.type=="ARMATURE"]
if len(arm_mods)!=1 or arm_mods[0].object!=arm:
    raise RuntimeError("Safety stop: invalid F2 Armature modifier state")
if f2.parent is not None:
    raise RuntimeError("Safety stop: F2 was left parented")
if f2.matrix_world!=f2_matrix_before:
    vals=[abs(f2.matrix_world[r][c]-f2_matrix_before[r][c]) for r in range(4) for c in range(4)]
    if max(vals)>1.0e-7:
        raise RuntimeError("Safety stop: F2 object transform changed")

other_arm_mods=sum(
    1 for n in OTHER_TARGETS
    for m in bpy.data.objects[n].modifiers if m.type=="ARMATURE"
)
if other_arm_mods:
    raise RuntimeError("Safety stop: non-F2 character targets were bound")

rest_after=rest_bone_snapshot(arm)
rest_changes=[n for n in rest_before if rest_before[n]!=rest_after.get(n)]
if rest_changes:
    raise RuntimeError("Safety stop: armature rest bones changed: "+", ".join(rest_changes))

rig_action_after=arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else ""
rig_action_created=bool(rig_action_after and rig_action_after!=rig_action_before)
if rig_action_created:
    raise RuntimeError("Safety stop: a rig action was created")

protected_after={o.name:object_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
protected_changes=[]
if set(protected_before)!=set(protected_after):
    protected_changes.append("object_set_changed")
for n in sorted(set(protected_before)&set(protected_after)):
    if protected_before[n]!=protected_after[n]:
        protected_changes.append(n)
if protected_changes:
    raise RuntimeError("Safety stop: protected object changes: "+", ".join(protected_changes[:10]))

metrics=weight_metrics(f2,deform_names)
empty_groups=[n for n,c in metrics["group_vertex_counts"].items() if c==0]

scene.frame_set(original_frame)
bpy.context.view_layer.update()

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "rig_name":RIG_NAME,
    "armature_count_after":sum(1 for o in bpy.data.objects if o.type=="ARMATURE"),
    "bone_count":len(arm.data.bones),
    "deform_group_count":len(deform_names),
    "deform_groups":deform_names,
    "weighting_method":weighting_method,
    "automatic_weighting_error":auto_error,
    "f2_vertex_count":len(f2.data.vertices),
    "f2_armature_modifier_count_after":len(arm_mods),
    "f2_armature_modifier_name":arm_mods[0].name,
    "f2_parent_after":f2.parent.name if f2.parent else "",
    "other_target_armature_modifier_count_after":other_arm_mods,
    "unweighted_vertex_count":len(metrics["unweighted"]),
    "unweighted_vertices_preview":metrics["unweighted"][:50],
    "invalid_weight_sum_vertex_count":len(metrics["invalid"]),
    "invalid_weight_sums_preview":metrics["invalid"][:50],
    "maximum_influences_per_vertex":metrics["maximum"],
    "influence_histogram":metrics["histogram"],
    "group_vertex_counts":metrics["group_vertex_counts"],
    "group_weight_sums":metrics["group_weight_sums"],
    "empty_deform_groups":empty_groups,
    "rest_visual_world_error":rest_error,
    "armature_rest_change_count":len(rest_changes),
    "armature_rest_changes":rest_changes,
    "rig_action_created":rig_action_created,
    "rig_action_after":rig_action_after,
    "protected_object_count":len(protected_before),
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "scene_frame_preserved":scene.frame_current==original_frame,
    "created_backup_blend_files":0,
}

with open(os.path.join(OUT,"F2BindWeightsV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"F2BindWeightsV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY F2-ONLY BIND / WEIGHTS V1\n")
    f.write(f"weighting_method={weighting_method}\n")
    f.write(f"automatic_weighting_error={auto_error}\n")
    f.write(f"vertices={len(f2.data.vertices)}\n")
    f.write(f"deform_groups={len(deform_names)}\n")
    f.write(f"unweighted_vertices={len(metrics['unweighted'])}\n")
    f.write(f"invalid_weight_sums={len(metrics['invalid'])}\n")
    f.write(f"maximum_influences={metrics['maximum']}\n")
    f.write(f"rest_visual_error={rest_error:.12f}\n")
    f.write(f"other_targets_bound={other_arm_mods}\n")
    f.write(f"protected_changes={len(protected_changes)}\n")
    f.write(f"empty_deform_groups={empty_groups}\n")
    f.write(f"influence_histogram={metrics['histogram']}\n")
with open(os.path.join(OUT,"F2_Bind_Weights_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy F2-Only Bind / Weights v1\n\n")
    f.write(f"- Weighting method: **{weighting_method}**\n")
    f.write(f"- F2 vertices: **{len(f2.data.vertices)}**\n")
    f.write(f"- Deform groups: **{len(deform_names)}**\n")
    f.write(f"- Unweighted vertices: **{len(metrics['unweighted'])}**\n")
    f.write(f"- Invalid normalized sums: **{len(metrics['invalid'])}**\n")
    f.write(f"- Maximum influences per vertex: **{metrics['maximum']}**\n")
    f.write(f"- Rest-pose visual error: **{rest_error:.12f}**\n")
    f.write(f"- Other character targets bound: **{other_arm_mods}**\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**\n\n")
    f.write("No deformation-test action was created. The next stage creates controlled preview poses for F2 only.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"F2BindWeightsV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print("[bind] F2-only binding complete")
print(f"[method] {weighting_method}")
if auto_error:
    print(f"[automatic_error] {auto_error}")
print(f"[weights] vertices={len(f2.data.vertices)} groups={len(deform_names)} unweighted={len(metrics['unweighted'])} invalid_sums={len(metrics['invalid'])} max_influences={metrics['maximum']}")
print(f"[rest] visual_error={rest_error:.12f}")
print(f"[safety] other_targets_bound={other_arm_mods} rest_bone_changes={len(rest_changes)} protected_changes={len(protected_changes)} action_created={rig_action_created}")
print("[save] blend saved")
