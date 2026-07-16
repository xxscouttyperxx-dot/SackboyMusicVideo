
import bpy, os, json, statistics
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","arm_alignment_finalization_v2")
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
        "mods":[(m.name,m.type) for m in o.modifiers],
        "vertex_groups":[g.name for g in o.vertex_groups],
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
if f2.data.shape_keys:
    raise RuntimeError("Safety stop: F2 shape keys unexpectedly returned")

target_before={n:mesh_sig(bpy.data.objects[n]) for n in TARGETS}
protected_before={o.name:obj_sig(o) for o in bpy.data.objects if o.name not in set(TARGETS+[RIG])}

# Read evaluated F2 geometry in world space.
dg=bpy.context.evaluated_depsgraph_get()
ev=f2.evaluated_get(dg)
me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
try:
    pts=[ev.matrix_world @ v.co for v in me.vertices]
finally:
    ev.to_mesh_clear()

xs=[p.x for p in pts]
ys=[p.y for p in pts]
zs=[p.z for p in pts]
xmin,xmax=min(xs),max(xs)
zmin,zmax=min(zs),max(zs)
xcenter=statistics.median(xs)
zspan=zmax-zmin
left_extent=xcenter-xmin
right_extent=xmax-xcenter

if left_extent<=0.5 or right_extent<=0.5 or zspan<=1.0:
    raise RuntimeError("Safety stop: unexpected F2 dimensions")

# T-pose arm band. Use outer-side vertices and a narrow vertical range around
# the visible arm/sleeve center. This deliberately excludes torso and legs.
def arm_band(side):
    extent=left_extent if side=="L" else right_extent
    candidates=[]
    for p in pts:
        dx=(xcenter-p.x) if side=="L" else (p.x-xcenter)
        xf=dx/extent
        zf=(p.z-zmin)/zspan
        if 0.30<=xf<=0.97 and 0.56<=zf<=0.72:
            candidates.append(p)
    if len(candidates)<100:
        raise RuntimeError(f"Safety stop: insufficient {side} arm samples: {len(candidates)}")
    return candidates

left_band=arm_band("L")
right_band=arm_band("R")

# Surface points occur on both front/back and top/bottom. Their medians define
# the interior center plane. Average the two sides to prevent a crooked rig.
left_y=statistics.median(p.y for p in left_band)
right_y=statistics.median(p.y for p in right_band)
left_z=statistics.median(p.z for p in left_band)
right_z=statistics.median(p.z for p in right_band)
arm_y=(left_y+right_y)*0.5
arm_z=(left_z+right_z)*0.5

arm_z_fraction=(arm_z-zmin)/zspan
if not (0.56<=arm_z_fraction<=0.72):
    raise RuntimeError(f"Safety stop: derived arm height is implausible: {arm_z_fraction}")

# Straight stylized T-pose proportions. These positions track F2's actual
# left/right extents and end just inside each hand tip.
fractions={"shoulder":0.29,"elbow":0.56,"wrist":0.80,"hand":0.975}

def world_point(side, key):
    extent=left_extent if side=="L" else right_extent
    sign=-1.0 if side=="L" else 1.0
    return Vector((xcenter+sign*fractions[key]*extent,arm_y,arm_z))

world_landmarks={}
for side in ("L","R"):
    world_landmarks[side]={
        "chest":Vector((xcenter,arm_y,arm_z)),
        "shoulder":world_point(side,"shoulder"),
        "elbow":world_point(side,"elbow"),
        "wrist":world_point(side,"wrist"),
        "hand":world_point(side,"hand"),
    }

# Convert world points to armature-local points.
inv=arm.matrix_world.inverted()
local_landmarks={
    side:{key:inv@point for key,point in marks.items()}
    for side,marks in world_landmarks.items()
}

before={}
for n in ARM_BONES:
    b=arm.data.bones[n]
    before[n]={"head":list(b.head_local),"tail":list(b.tail_local),"length":b.length}

bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb=arm.data.edit_bones

for side in ("L","R"):
    lm=local_landmarks[side]
    clav=eb[f"clavicle.{side}"]
    upper=eb[f"upper_arm.{side}"]
    fore=eb[f"forearm.{side}"]
    hand=eb[f"hand.{side}"]

    # Remove the M shape: clavicle and arm chain share the same horizontal plane.
    clav.head=lm["chest"]
    clav.tail=lm["shoulder"]
    upper.head=lm["shoulder"]
    upper.tail=lm["elbow"]
    fore.head=lm["elbow"]
    fore.tail=lm["wrist"]
    hand.head=lm["wrist"]
    hand.tail=lm["hand"]

    upper.parent=clav
    upper.use_connect=True
    fore.parent=upper
    fore.use_connect=True
    hand.parent=fore
    hand.use_connect=True

bpy.ops.object.mode_set(mode="OBJECT")
arm.select_set(False)
bpy.context.view_layer.update()

# Strong geometric validation: monotonic outward chains, straight height/depth,
# connected joints, plausible lengths, and endpoints near F2's side extents.
checks=[]
for side in ("L","R"):
    sign=-1 if side=="L" else 1
    names=[f"clavicle.{side}",f"upper_arm.{side}",f"forearm.{side}",f"hand.{side}"]
    bones=[arm.data.bones[n] for n in names]
    points=[bones[0].head_local,bones[0].tail_local,bones[1].tail_local,bones[2].tail_local,bones[3].tail_local]

    outward=[sign*(p.x-points[0].x) for p in points]
    monotonic=all(outward[i+1]>outward[i] for i in range(len(outward)-1))
    zspread=max(p.z for p in points)-min(p.z for p in points)
    yspread=max(p.y for p in points)-min(p.y for p in points)
    connected=(
        (bones[0].tail_local-bones[1].head_local).length<1e-7 and
        (bones[1].tail_local-bones[2].head_local).length<1e-7 and
        (bones[2].tail_local-bones[3].head_local).length<1e-7
    )
    lengths=[b.length for b in bones]
    plausible_lengths=all(0.12<=v<=0.45 for v in lengths)
    endpoint_fraction=outward[-1]/(left_extent if side=="L" else right_extent)
    endpoint_ok=0.95<=endpoint_fraction<=0.99

    checks.append({
        "side":side,
        "monotonic_outward":monotonic,
        "z_spread":zspread,
        "y_spread":yspread,
        "connected":connected,
        "lengths":lengths,
        "plausible_lengths":plausible_lengths,
        "endpoint_fraction":endpoint_fraction,
        "endpoint_ok":endpoint_ok,
        "passed":monotonic and zspread<1e-6 and yspread<1e-6 and connected and plausible_lengths and endpoint_ok,
    })

checks_passed=all(c["passed"] for c in checks)
if not checks_passed:
    raise RuntimeError("Safety stop: final arm-chain geometry validation failed")

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

after={}
for n in ARM_BONES:
    b=arm.data.bones[n]
    after[n]={"head":list(b.head_local),"tail":list(b.tail_local),"length":b.length}

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "armature_name":RIG,
    "armature_count_after":sum(1 for o in bpy.data.objects if o.type=="ARMATURE"),
    "bone_count_after":len(arm.data.bones),
    "changed_bone_count":len(ARM_BONES),
    "changed_bones":ARM_BONES,
    "f2_bounds_world":{"xmin":xmin,"xmax":xmax,"zmin":zmin,"zmax":zmax,"xcenter":xcenter},
    "sample_counts":{"L":len(left_band),"R":len(right_band)},
    "arm_center_world":{"x":xcenter,"y":arm_y,"z":arm_z,"z_fraction":arm_z_fraction},
    "placement_fractions":fractions,
    "world_landmarks":{s:{k:list(v) for k,v in marks.items()} for s,marks in world_landmarks.items()},
    "bones_before":before,
    "bones_after":after,
    "arm_chain_checks":checks,
    "arm_chain_geometry_checks_passed":checks_passed,
    "mesh_change_count":len(mesh_changes),
    "mesh_changes":mesh_changes,
    "armature_modifier_count_after":arm_mod_count,
    "parented_target_count_after":parented_count,
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "created_backup_blend_files":0,
}

with open(os.path.join(OUT,"ArmAlignmentFinalizationV2_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"ArmAlignmentFinalizationV2_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY ARM ALIGNMENT FINALIZATION V2\n")
    f.write(f"arm_center_world=({xcenter}, {arm_y}, {arm_z})\n")
    f.write(f"arm_z_fraction={arm_z_fraction}\n")
    f.write(f"sample_counts=L:{len(left_band)} R:{len(right_band)}\n")
    f.write(f"geometry_checks_passed={checks_passed}\n")
    f.write(f"mesh_changes={len(mesh_changes)}\narmature_modifiers={arm_mod_count}\n")
    f.write(f"parented_targets={parented_count}\nprotected_changes={len(protected_changes)}\n")
    for c in checks:
        f.write(f"{c['side']} checks={c}\n")
with open(os.path.join(OUT,"Arm_Alignment_Finalization_V2.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy Arm Alignment Finalization v2\n\n")
    f.write("- Replaced the raised-clavicle M shape and downward hand bones.\n")
    f.write(f"- Geometry samples: left **{len(left_band)}**, right **{len(right_band)}**.\n")
    f.write(f"- Arm center height: **{arm_z:.6f}**.\n")
    f.write(f"- Straight/connected geometry checks: **{checks_passed}**.\n")
    f.write(f"- Character mesh changes: **{len(mesh_changes)}**.\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**.\n\n")
    f.write("This remains an unweighted placement rig. The next stage is F2-only binding and deformation testing.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"ArmAlignmentFinalizationV2_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print("[rig] final straight arm alignment complete")
print(f"[samples] L={len(left_band)} R={len(right_band)}")
print(f"[center] y={arm_y:.6f} z={arm_z:.6f} z_fraction={arm_z_fraction:.6f}")
print(f"[checks] passed={checks_passed} details={checks}")
print(f"[safety] mesh_changes={len(mesh_changes)} armature_modifiers={arm_mod_count} parented={parented_count} protected_changes={len(protected_changes)}")
print("[save] blend saved")
