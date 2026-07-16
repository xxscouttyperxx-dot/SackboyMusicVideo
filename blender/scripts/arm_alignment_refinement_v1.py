
import bpy, os, json, statistics
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","arm_alignment_refinement_v1")
os.makedirs(OUT,exist_ok=True)

RIG="SACKBOY_RIG_PLACEMENT_V1"
TARGETS=["F2","Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
ARM_BONES=[
    "clavicle.L","upper_arm.L","forearm.L","hand.L",
    "clavicle.R","upper_arm.R","forearm.R","hand.R"
]

def mlist(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def mesh_sig(o):
    me=o.data
    return {
        "data":me.name,"verts":len(me.vertices),"edges":len(me.edges),"polys":len(me.polygons),
        "matrix":mlist(o.matrix_world),"parent":o.parent.name if o.parent else "",
        "mods":[(m.name,m.type) for m in o.modifiers]
    }

def obj_sig(o):
    ad=o.animation_data
    return {
        "type":o.type,"data":getattr(o.data,"name",""),
        "matrix":mlist(o.matrix_world),"parent":o.parent.name if o.parent else "",
        "hide_viewport":o.hide_viewport,"hide_render":o.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "drivers":len(ad.drivers) if ad else 0,
        "nla":len(ad.nla_tracks) if ad else 0,
        "mods":[m.name for m in o.modifiers],
        "constraints":[c.name for c in o.constraints],
    }

def median_vec(points):
    return Vector((
        statistics.median(p.x for p in points),
        statistics.median(p.y for p in points),
        statistics.median(p.z for p in points),
    ))

def robust_center(points, fallback):
    if len(points)<12:
        return fallback.copy(), len(points)
    med=median_vec(points)
    dists=sorted((p-med).length for p in points)
    cutoff=dists[max(0,int(len(dists)*0.75)-1)]
    trimmed=[p for p in points if (p-med).length<=cutoff]
    if len(trimmed)<8:
        trimmed=points
    return median_vec(trimmed),len(points)

for n in TARGETS:
    if bpy.data.objects.get(n) is None:
        raise RuntimeError(f"Missing target: {n}")
arm=bpy.data.objects.get(RIG)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature: {RIG}")
if sum(1 for o in bpy.data.objects if o.type=="ARMATURE")!=1:
    raise RuntimeError("Safety stop: expected exactly one armature")
if len(arm.data.bones)!=22:
    raise RuntimeError("Safety stop: expected 22 bones")
for n in ARM_BONES:
    if arm.data.bones.get(n) is None:
        raise RuntimeError(f"Missing arm bone: {n}")

f2=bpy.data.objects["F2"]
target_before={n:mesh_sig(bpy.data.objects[n]) for n in TARGETS}
protected_before={o.name:obj_sig(o) for o in bpy.data.objects if o.name not in set(TARGETS+[RIG])}

dg=bpy.context.evaluated_depsgraph_get()
ev=f2.evaluated_get(dg)
mesh=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
try:
    pts=[ev.matrix_world@v.co for v in mesh.vertices]
finally:
    ev.to_mesh_clear()

xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
xmin,xmax=min(xs),max(xs)
zmin,zmax=min(zs),max(zs)
xcenter=statistics.median(xs)
zspan=zmax-zmin
left_extent=xcenter-xmin
right_extent=xmax-xcenter

old={}
for n in ARM_BONES:
    b=arm.data.bones[n]
    old[n]={"head":list(b.head_local),"tail":list(b.tail_local)}

# Current chain joints provide stable fallbacks.
fallback={}
for side in ("L","R"):
    fallback[f"shoulder.{side}"]=arm.data.bones[f"upper_arm.{side}"].head_local.copy()
    fallback[f"elbow.{side}"]=arm.data.bones[f"upper_arm.{side}"].tail_local.copy()
    fallback[f"wrist.{side}"]=arm.data.bones[f"forearm.{side}"].tail_local.copy()
    fallback[f"hand.{side}"]=arm.data.bones[f"hand.{side}"].tail_local.copy()

def side_landmarks(side):
    sgn=-1 if side=="L" else 1
    extent=left_extent if side=="L" else right_extent
    # Distances from center along the side. Windows are intentionally broad and
    # restricted to the upper/mid body height to avoid legs and torso.
    specs={
        "shoulder":(0.20,0.34,0.58,0.82),
        "elbow":(0.34,0.48,0.42,0.72),
        "wrist":(0.45,0.57,0.28,0.60),
        "hand":(0.53,0.64,0.20,0.55),
    }
    result={}
    counts={}
    for key,(a,b,za,zb) in specs.items():
        lo=a*extent; hi=b*extent
        candidates=[]
        for p in pts:
            dx=(xcenter-p.x) if side=="L" else (p.x-xcenter)
            zn=(p.z-zmin)/zspan if zspan else 0
            if lo<=dx<=hi and za<=zn<=zb:
                candidates.append(p)
        c,count=robust_center(candidates,fallback[f"{key}.{side}"])
        result[key]=c
        counts[key]=count
    return result,counts

landmarks={}
sample_counts={}
for side in ("L","R"):
    lm,cnts=side_landmarks(side)
    landmarks[side]=lm
    sample_counts[side]=cnts

# Keep clavicle roots anchored to chest center. Update only arm chain positions.
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb=arm.data.edit_bones

for side in ("L","R"):
    lm=landmarks[side]
    clav=eb[f"clavicle.{side}"]
    upper=eb[f"upper_arm.{side}"]
    fore=eb[f"forearm.{side}"]
    hand=eb[f"hand.{side}"]

    # Preserve clavicle head at torso. Place its tail at estimated shoulder.
    clav.tail=lm["shoulder"]
    upper.head=lm["shoulder"]
    upper.tail=lm["elbow"]
    fore.head=lm["elbow"]
    fore.tail=lm["wrist"]
    hand.head=lm["wrist"]
    hand.tail=lm["hand"]

    # Ensure nonzero lengths.
    for bone in (clav,upper,fore,hand):
        if bone.length<0.03:
            raise RuntimeError(f"Safety stop: {bone.name} became too short")

bpy.ops.object.mode_set(mode="OBJECT")
arm.select_set(False)
bpy.context.view_layer.update()

target_after={n:mesh_sig(bpy.data.objects[n]) for n in TARGETS}
mesh_changes=[n for n in TARGETS if target_before[n]!=target_after[n]]
arm_mod_count=sum(1 for n in TARGETS for m in bpy.data.objects[n].modifiers if m.type=="ARMATURE")
parented_count=sum(1 for n in TARGETS if bpy.data.objects[n].parent is not None)

protected_after={o.name:obj_sig(o) for o in bpy.data.objects if o.name not in set(TARGETS+[RIG])}
protected_changes=[]
if set(protected_before)!=set(protected_after):
    protected_changes.append("object_set_changed")
for n in sorted(set(protected_before)&set(protected_after)):
    if protected_before[n]!=protected_after[n]:
        protected_changes.append(n)

if mesh_changes:
    raise RuntimeError("Safety stop: character mesh changes: "+", ".join(mesh_changes))
if arm_mod_count:
    raise RuntimeError("Safety stop: Armature modifiers exist")
if parented_count:
    raise RuntimeError("Safety stop: target parenting changed")
if protected_changes:
    raise RuntimeError("Safety stop: protected changes: "+", ".join(protected_changes[:10]))

new={}
for n in ARM_BONES:
    b=arm.data.bones[n]
    new[n]={"head":list(b.head_local),"tail":list(b.tail_local),"length":b.length}

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "armature_name":RIG,
    "armature_count_after":sum(1 for o in bpy.data.objects if o.type=="ARMATURE"),
    "bone_count_after":len(arm.data.bones),
    "changed_bone_count":len(ARM_BONES),
    "changed_bones":ARM_BONES,
    "sample_counts":sample_counts,
    "landmarks":{s:{k:list(v) for k,v in landmarks[s].items()} for s in landmarks},
    "bones_before":old,
    "bones_after":new,
    "mesh_change_count":len(mesh_changes),
    "mesh_changes":mesh_changes,
    "armature_modifier_count_after":arm_mod_count,
    "parented_target_count_after":parented_count,
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "created_backup_blend_files":0,
}
with open(os.path.join(OUT,"ArmAlignmentRefinementV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"ArmAlignmentRefinementV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY ARM ALIGNMENT REFINEMENT V1\n")
    f.write(f"changed_bones={len(ARM_BONES)}\nmesh_changes={len(mesh_changes)}\n")
    f.write(f"armature_modifiers={arm_mod_count}\nparented_targets={parented_count}\nprotected_changes={len(protected_changes)}\n")
    for side in ("L","R"):
        f.write(f"\n{side} SAMPLE COUNTS\n")
        for k,v in sample_counts[side].items():f.write(f"{k}={v}\n")
        f.write(f"{side} LANDMARKS\n")
        for k,v in landmarks[side].items():f.write(f"{k}={list(v)}\n")
with open(os.path.join(OUT,"Arm_Alignment_Refinement_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy Arm Alignment Refinement v1\n\n")
    f.write(f"- Adjusted bones: **{len(ARM_BONES)}**\n- Mesh changes: **{len(mesh_changes)}**\n")
    f.write(f"- Armature modifiers: **{arm_mod_count}**\n- Parented targets: **{parented_count}**\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**\n\n")
    f.write("The refined arm chain remains unweighted and requires visual approval before binding.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"ArmAlignmentRefinementV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print("[rig] arm alignment refinement complete")
print(f"[bones] adjusted={len(ARM_BONES)} total={len(arm.data.bones)}")
print(f"[samples] L={sample_counts['L']} R={sample_counts['R']}")
print(f"[safety] mesh_changes={len(mesh_changes)} armature_modifiers={arm_mod_count} parented={parented_count} protected_changes={len(protected_changes)}")
print("[save] blend saved")
