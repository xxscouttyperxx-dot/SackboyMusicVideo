
import bpy, os, json, statistics
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","lower_body_foot_alignment_v1")
os.makedirs(OUT,exist_ok=True)

RIG="SACKBOY_RIG_PLACEMENT_V1"
TARGETS=["F2","Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
LEG_BONES=[
    "thigh.L","shin.L","foot.L","toe.L",
    "thigh.R","shin.R","foot.R","toe.R"
]
SHOES={"L":"Plane.001","R":"Plane.022"}

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

def eval_points(obj, dg):
    ev=obj.evaluated_get(dg)
    me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        return [ev.matrix_world@v.co for v in me.vertices]
    finally:
        ev.to_mesh_clear()

def quantile(values, q):
    vals=sorted(values)
    if not vals:
        raise RuntimeError("Empty quantile input")
    pos=(len(vals)-1)*q
    lo=int(pos)
    hi=min(lo+1,len(vals)-1)
    t=pos-lo
    return vals[lo]*(1.0-t)+vals[hi]*t

def median_vec(points):
    if not points:
        raise RuntimeError("No points for median")
    return Vector((
        statistics.median(p.x for p in points),
        statistics.median(p.y for p in points),
        statistics.median(p.z for p in points),
    ))

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
for n in LEG_BONES:
    if arm.data.bones.get(n) is None:
        raise RuntimeError(f"Missing lower-body bone: {n}")

target_before={n:mesh_sig(bpy.data.objects[n]) for n in TARGETS}
protected_before={o.name:obj_sig(o) for o in bpy.data.objects if o.name not in set(TARGETS+[RIG])}

dg=bpy.context.evaluated_depsgraph_get()
f2_pts=eval_points(bpy.data.objects["F2"],dg)
pants_pts=eval_points(bpy.data.objects["Cargo pants"],dg)
shoe_pts={side:eval_points(bpy.data.objects[name],dg) for side,name in SHOES.items()}

f2_xcenter=statistics.median(p.x for p in f2_pts)
f2_ycenter=statistics.median(p.y for p in f2_pts)

shoe_stats={}
for side,pts in shoe_pts.items():
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    shoe_stats[side]={
        "xmin":min(xs),"xmax":max(xs),
        "ymin":min(ys),"ymax":max(ys),
        "zmin":min(zs),"zmax":max(zs),
        "xmed":statistics.median(xs),
        "ymed":statistics.median(ys),
        "zmed":statistics.median(zs),
    }

# Verify naming/side convention before changing bones.
if not (shoe_stats["L"]["xmed"] < f2_xcenter < shoe_stats["R"]["xmed"]):
    raise RuntimeError("Safety stop: shoe side assignment does not match the rig")

pants_zmin=min(p.z for p in pants_pts)
pants_zmax=max(p.z for p in pants_pts)
pants_span=pants_zmax-pants_zmin
if pants_span<=0.4:
    raise RuntimeError("Safety stop: unexpected cargo-pants height")

def side_pants(side):
    return [p for p in pants_pts if (p.x<f2_xcenter if side=="L" else p.x>f2_xcenter)]

def band_center(side, zlo, zhi):
    pts=side_pants(side)
    selected=[
        p for p in pts
        if pants_zmin+pants_span*zlo <= p.z <= pants_zmin+pants_span*zhi
    ]
    if len(selected)<50:
        raise RuntimeError(f"Safety stop: insufficient {side} pants samples in band {zlo}-{zhi}: {len(selected)}")
    return median_vec(selected),len(selected)

world_landmarks={}
sample_counts={}
for side in ("L","R"):
    upper,c_upper=band_center(side,0.68,0.86)
    middle,c_middle=band_center(side,0.31,0.50)
    lower,c_lower=band_center(side,0.04,0.18)
    st=shoe_stats[side]

    # Lower the entire chain slightly within the visible pants/shoe geometry.
    hip_z=pants_zmin+pants_span*0.76
    knee_z=pants_zmin+pants_span*0.38

    # Put the ankle/foot plane below the shoe midpoint, but safely above the sole.
    shoe_h=st["zmax"]-st["zmin"]
    foot_z=st["zmin"]+shoe_h*0.40

    # Keep X centered through each visible leg and shoe.
    hip_x=upper.x
    knee_x=middle.x
    ankle_x=st["xmed"]

    # Smooth depth from pants into shoe. Negative Y is forward in this scene.
    hip_y=upper.y
    ankle_y=quantile([p.y for p in shoe_pts[side]],0.58)
    knee_linear=(hip_y+ankle_y)*0.5
    knee_y=knee_linear-0.018  # subtle forward bend for later IK stability

    # Run foot bones through the interior of the shoe.
    y_back=st["ymax"]
    y_front=st["ymin"]
    ankle_foot_y=y_back+(y_front-y_back)*0.34
    ball_y=y_back+(y_front-y_back)*0.67
    toe_y=y_back+(y_front-y_back)*0.94

    world_landmarks[side]={
        "hip":Vector((hip_x,hip_y,hip_z)),
        "knee":Vector((knee_x,knee_y,knee_z)),
        "ankle":Vector((ankle_x,ankle_foot_y,foot_z)),
        "ball":Vector((ankle_x,ball_y,foot_z)),
        "toe":Vector((ankle_x,toe_y,foot_z)),
    }
    sample_counts[side]={"upper":c_upper,"middle":c_middle,"lower":c_lower}

inv=arm.matrix_world.inverted()
local_landmarks={
    side:{key:inv@p for key,p in marks.items()}
    for side,marks in world_landmarks.items()
}

before={}
for n in LEG_BONES:
    b=arm.data.bones[n]
    before[n]={"head":list(b.head_local),"tail":list(b.tail_local),"length":b.length}

bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb=arm.data.edit_bones

for side in ("L","R"):
    lm=local_landmarks[side]
    thigh=eb[f"thigh.{side}"]
    shin=eb[f"shin.{side}"]
    foot=eb[f"foot.{side}"]
    toe=eb[f"toe.{side}"]

    thigh.head=lm["hip"]
    thigh.tail=lm["knee"]
    shin.head=lm["knee"]
    shin.tail=lm["ankle"]
    foot.head=lm["ankle"]
    foot.tail=lm["ball"]
    toe.head=lm["ball"]
    toe.tail=lm["toe"]

    shin.parent=thigh
    shin.use_connect=True
    foot.parent=shin
    foot.use_connect=True
    toe.parent=foot
    toe.use_connect=True

bpy.ops.object.mode_set(mode="OBJECT")
arm.select_set(False)
bpy.context.view_layer.update()

checks=[]
for side in ("L","R"):
    thigh=arm.data.bones[f"thigh.{side}"]
    shin=arm.data.bones[f"shin.{side}"]
    foot=arm.data.bones[f"foot.{side}"]
    toe=arm.data.bones[f"toe.{side}"]
    st=shoe_stats[side]

    hip=arm.matrix_world@thigh.head_local
    knee=arm.matrix_world@thigh.tail_local
    ankle=arm.matrix_world@shin.tail_local
    ball=arm.matrix_world@foot.tail_local
    toe_tip=arm.matrix_world@toe.tail_local

    connected=(
        (thigh.tail_local-shin.head_local).length<1e-7 and
        (shin.tail_local-foot.head_local).length<1e-7 and
        (foot.tail_local-toe.head_local).length<1e-7
    )
    descending=hip.z>knee.z>ankle.z
    foot_level=abs(ankle.z-ball.z)<1e-7 and abs(ball.z-toe_tip.z)<1e-7
    forward=ankle.y>ball.y>toe_tip.y
    foot_inside_z=st["zmin"]+0.25*(st["zmax"]-st["zmin"]) <= ankle.z <= st["zmin"]+0.55*(st["zmax"]-st["zmin"])
    toe_inside=st["ymin"] <= toe_tip.y <= st["ymin"]+0.10*(st["ymax"]-st["ymin"])
    x_inside=st["xmin"]<=ankle.x<=st["xmax"]
    lengths=[thigh.length,shin.length,foot.length,toe.length]
    lengths_ok=(0.22<=thigh.length<=0.65 and 0.20<=shin.length<=0.60 and 0.12<=foot.length<=0.40 and 0.08<=toe.length<=0.30)
    knee_forward=knee.y < (hip.y+ankle.y)*0.5

    passed=all([connected,descending,foot_level,forward,foot_inside_z,toe_inside,x_inside,lengths_ok,knee_forward])
    checks.append({
        "side":side,
        "connected":connected,
        "descending":descending,
        "foot_level":foot_level,
        "forward":forward,
        "foot_inside_z":foot_inside_z,
        "toe_inside":toe_inside,
        "x_inside":x_inside,
        "lengths":lengths,
        "lengths_ok":lengths_ok,
        "knee_forward_bias":knee_forward,
        "passed":passed,
    })

checks_passed=all(c["passed"] for c in checks)
if not checks_passed:
    raise RuntimeError("Safety stop: lower-body geometry validation failed")

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
for n in LEG_BONES:
    b=arm.data.bones[n]
    after[n]={"head":list(b.head_local),"tail":list(b.tail_local),"length":b.length}

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "armature_name":RIG,
    "armature_count_after":sum(1 for o in bpy.data.objects if o.type=="ARMATURE"),
    "bone_count_after":len(arm.data.bones),
    "changed_bone_count":len(LEG_BONES),
    "changed_bones":LEG_BONES,
    "pants_bounds":{"zmin":pants_zmin,"zmax":pants_zmax},
    "shoe_stats":shoe_stats,
    "sample_counts":sample_counts,
    "world_landmarks":{
        side:{key:{"x":p.x,"y":p.y,"z":p.z} for key,p in marks.items()}
        for side,marks in world_landmarks.items()
    },
    "bones_before":before,
    "bones_after":after,
    "lower_body_checks":checks,
    "lower_body_geometry_checks_passed":checks_passed,
    "mesh_change_count":len(mesh_changes),
    "mesh_changes":mesh_changes,
    "armature_modifier_count_after":arm_mod_count,
    "parented_target_count_after":parented_count,
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "created_backup_blend_files":0,
}

with open(os.path.join(OUT,"LowerBodyFootAlignmentV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"LowerBodyFootAlignmentV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY LOWER-BODY / FOOT ALIGNMENT V1\n")
    f.write(f"geometry_checks_passed={checks_passed}\n")
    f.write(f"mesh_changes={len(mesh_changes)}\narmature_modifiers={arm_mod_count}\n")
    f.write(f"parented_targets={parented_count}\nprotected_changes={len(protected_changes)}\n")
    for side in ("L","R"):
        f.write(f"\n{side} landmarks={world_landmarks[side]}\n")
        f.write(f"{side} checks={checks[0 if side=='L' else 1]}\n")
with open(os.path.join(OUT,"Lower_Body_Foot_Alignment_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy Lower-Body / Foot Alignment v1\n\n")
    f.write("- Lowered and recentered both leg chains using the pants and shoes.\n")
    f.write("- Centered foot/toe bones inside each visible shoe.\n")
    f.write("- Added a subtle forward knee bias for future jumpstyle IK stability.\n")
    f.write(f"- Geometry checks: **{checks_passed}**.\n")
    f.write(f"- Character mesh changes: **{len(mesh_changes)}**.\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**.\n\n")
    f.write("This remains unweighted. The next stage is F2-only binding and deformation testing.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"LowerBodyFootAlignmentV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print("[rig] lower-body / foot alignment complete")
print(f"[samples] {sample_counts}")
print(f"[checks] passed={checks_passed} details={checks}")
print(f"[safety] mesh_changes={len(mesh_changes)} armature_modifiers={arm_mod_count} parented={parented_count} protected_changes={len(protected_changes)}")
print("[save] blend saved")
