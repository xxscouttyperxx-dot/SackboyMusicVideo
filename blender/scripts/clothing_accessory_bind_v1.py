
import bpy, os, json, math, statistics
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from datetime import datetime, timezone

SCRIPT_VERSION="1.0"
ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","clothing_accessory_bind_v1")
os.makedirs(OUT,exist_ok=True)

RIG="SACKBOY_RIG_PLACEMENT_V1"
F2="F2"
ACTION="F2_DEFORMATION_TEST_V1_2"
CLOTHING=["Lowerpoly hoodie","Cargo pants"]
EYES=["L.Eye","R.Eye"]
SHOES={"Plane.001":"foot.L","Plane.022":"foot.R"}
RIGID_ATTACH={"L.Eye":"head","R.Eye":"head",**SHOES}
ALL_TARGETS=[F2]+CLOTHING+EYES+list(SHOES)
REST_FRAME=1
MOTION_FRAMES={
    "Lowerpoly hoodie":205,
    "Cargo pants":235,
    "L.Eye":265,
    "R.Eye":265,
    "Plane.001":245,
    "Plane.022":255,
}
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
        "parent_type":obj.parent_type,
        "parent_bone":obj.parent_bone,
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "drivers":len(ad.drivers) if ad else 0,
        "nla":len(ad.nla_tracks) if ad else 0,
        "modifiers":[(m.name,m.type,getattr(m,"object",None).name if getattr(m,"object",None) else "") for m in obj.modifiers],
        "constraints":[c.name for c in obj.constraints],
        "vertex_groups":[g.name for g in obj.vertex_groups] if hasattr(obj,"vertex_groups") else [],
    }

def mesh_binding_snapshot(obj):
    return {
        "mesh":obj.data.name,
        "vertices":len(obj.data.vertices),
        "edges":len(obj.data.edges),
        "polygons":len(obj.data.polygons),
        "matrix_world":mlist(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "modifiers":[(m.name,m.type,getattr(m,"object",None).name if getattr(m,"object",None) else "") for m in obj.modifiers],
        "vertex_groups":[g.name for g in obj.vertex_groups],
    }

def rest_bone_snapshot(arm):
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

def evaluated_world_vertices(obj,dg):
    ev=obj.evaluated_get(dg)
    me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    try:
        mw=ev.matrix_world.copy()
        return [mw@v.co for v in me.vertices]
    finally:
        ev.to_mesh_clear()

def max_point_error(a,b):
    if len(a)!=len(b):
        raise RuntimeError(f"Evaluated vertex count changed: {len(a)} -> {len(b)}")
    return max(((p-q).length for p,q in zip(a,b)),default=0.0)

def barycentric(p,a,b,c):
    v0=b-a
    v1=c-a
    v2=p-a
    d00=v0.dot(v0)
    d01=v0.dot(v1)
    d11=v1.dot(v1)
    d20=v2.dot(v0)
    d21=v2.dot(v1)
    denom=d00*d11-d01*d01
    if abs(denom)<1.0e-16:
        return (1.0,0.0,0.0)
    v=(d11*d20-d01*d21)/denom
    w=(d00*d21-d01*d20)/denom
    u=1.0-v-w
    # Nearest point should be on triangle, but clamp tiny numerical drift.
    u=max(0.0,min(1.0,u))
    v=max(0.0,min(1.0,v))
    w=max(0.0,min(1.0,w))
    total=u+v+w
    if total<=1.0e-12:
        return (1.0,0.0,0.0)
    return (u/total,v/total,w/total)

def source_weight_table(source,deform_names):
    idx_to_name={g.index:g.name for g in source.vertex_groups}
    table=[]
    allowed=set(deform_names)
    for v in source.data.vertices:
        weights={}
        for e in v.groups:
            name=idx_to_name.get(e.group)
            if name in allowed and e.weight>1.0e-10:
                weights[name]=float(e.weight)
        table.append(weights)
    return table

def build_source_surface(source):
    mesh=source.data
    mesh.calc_loop_triangles()
    world_vertices=[source.matrix_world@v.co for v in mesh.vertices]
    triangles=[tuple(tri.vertices) for tri in mesh.loop_triangles]
    if not triangles:
        raise RuntimeError("F2 has no loop triangles")
    bvh=BVHTree.FromPolygons(world_vertices,triangles,all_triangles=True)
    return world_vertices,triangles,bvh

def transfer_weights(source,target,deform_names,source_weights,src_world,triangles,bvh):
    if len(target.vertex_groups)!=0:
        raise RuntimeError(f"{target.name} already has vertex groups")
    groups={name:target.vertex_groups.new(name=name) for name in deform_names}
    distances=[]
    empty=0

    for v in target.data.vertices:
        p=target.matrix_world@v.co
        location,normal,tri_index,distance=bvh.find_nearest(p)
        if location is None or tri_index is None:
            raise RuntimeError(f"Nearest-surface lookup failed for {target.name} vertex {v.index}")
        i0,i1,i2=triangles[tri_index]
        u,vb,w=barycentric(location,src_world[i0],src_world[i1],src_world[i2])

        combined={}
        for coef,idx in ((u,i0),(vb,i1),(w,i2)):
            for name,weight in source_weights[idx].items():
                combined[name]=combined.get(name,0.0)+coef*weight

        strongest=sorted(
            ((weight,name) for name,weight in combined.items() if weight>1.0e-8),
            reverse=True
        )[:4]
        total=sum(weight for weight,name in strongest)
        if total<=1.0e-12:
            empty+=1
            raise RuntimeError(f"Transferred no weight to {target.name} vertex {v.index}")
        for weight,name in strongest:
            groups[name].add([v.index],weight/total,"REPLACE")
        distances.append(float(distance))

    modifier=target.modifiers.new(name="SACKBOY_RIG_DEFORM",type="ARMATURE")
    modifier.object=bpy.data.objects[RIG]
    modifier.use_deform_preserve_volume=True
    target.modifiers.move(len(target.modifiers)-1,0)

    return {
        "vertex_count":len(target.data.vertices),
        "nearest_distance_min":min(distances),
        "nearest_distance_median":statistics.median(distances),
        "nearest_distance_max":max(distances),
        "empty_transfer_count":empty,
    }

def weight_metrics(obj,deform_names):
    deform_indices={obj.vertex_groups[n].index for n in deform_names if obj.vertex_groups.get(n)}
    unweighted=[]
    invalid=[]
    maximum=0
    histogram={}
    group_counts={n:0 for n in deform_names}
    idx_to_name={g.index:g.name for g in obj.vertex_groups}

    for v in obj.data.vertices:
        entries=[e for e in v.groups if e.group in deform_indices and e.weight>1.0e-8]
        total=sum(e.weight for e in entries)
        count=len(entries)
        maximum=max(maximum,count)
        histogram[str(count)]=histogram.get(str(count),0)+1
        if count==0:
            unweighted.append(v.index)
        elif abs(total-1.0)>WEIGHT_TOL:
            invalid.append((v.index,total))
        for e in entries:
            group_counts[idx_to_name[e.group]]+=1

    return {
        "unweighted":unweighted,
        "invalid":invalid,
        "maximum_influences":maximum,
        "influence_histogram":histogram,
        "group_vertex_counts":group_counts,
    }

def rigid_bone_parent(obj,arm,bone_name):
    world=obj.matrix_world.copy()
    obj.parent=arm
    obj.parent_type="BONE"
    obj.parent_bone=bone_name
    obj.matrix_world=world

def finite(points):
    return all(math.isfinite(n) for p in points for n in (p.x,p.y,p.z))

# ---------- preflight ----------
arm=bpy.data.objects.get(RIG)
f2=bpy.data.objects.get(F2)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG}")
if f2 is None or f2.type!="MESH":
    raise RuntimeError("Missing F2")
for name in CLOTHING+EYES+list(SHOES):
    if bpy.data.objects.get(name) is None:
        raise RuntimeError(f"Missing target {name}")
if len(arm.data.bones)!=22:
    raise RuntimeError("Safety stop: expected approved 22-bone rig")
if not arm.animation_data or not arm.animation_data.action or arm.animation_data.action.name!=ACTION:
    raise RuntimeError(f"Safety stop: expected active action {ACTION}")

f2_mods=[m for m in f2.modifiers if m.type=="ARMATURE" and m.object==arm]
if len(f2_mods)!=1:
    raise RuntimeError("Safety stop: F2 approved binding is missing")
deform_names=[b.name for b in arm.data.bones if b.use_deform]
if len(deform_names)!=21:
    raise RuntimeError("Safety stop: expected 21 deform bones")
for name in deform_names:
    if f2.vertex_groups.get(name) is None:
        raise RuntimeError(f"Safety stop: F2 is missing deform group {name}")

for name in CLOTHING:
    obj=bpy.data.objects[name]
    if obj.type!="MESH":
        raise RuntimeError(f"{name} is not a mesh")
    if len(obj.vertex_groups)!=0:
        raise RuntimeError(f"Safety stop: {name} already has vertex groups")
    if any(m.type=="ARMATURE" for m in obj.modifiers):
        raise RuntimeError(f"Safety stop: {name} already has an Armature modifier")
    if obj.parent is not None:
        raise RuntimeError(f"Safety stop: {name} is already parented")

for name in EYES+list(SHOES):
    obj=bpy.data.objects[name]
    if obj.type!="MESH":
        raise RuntimeError(f"{name} is not a mesh")
    if obj.parent is not None:
        raise RuntimeError(f"Safety stop: {name} is already parented")
    if any(m.type=="ARMATURE" for m in obj.modifiers):
        raise RuntimeError(f"Safety stop: rigid target {name} already has an Armature modifier")

# Confirm shoe side mapping from world-space centers.
left_center=(bpy.data.objects["Plane.001"].matrix_world.translation.x)
right_center=(bpy.data.objects["Plane.022"].matrix_world.translation.x)
if not left_center<right_center:
    raise RuntimeError("Safety stop: shoe side mapping is inconsistent")

mutable=set(ALL_TARGETS+[RIG])
protected_before={o.name:object_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
f2_before=mesh_binding_snapshot(f2)
rest_before=rest_bone_snapshot(arm)
action_before=arm.animation_data.action.name
scene=bpy.context.scene
original_frame=scene.frame_current
frame_start_before=scene.frame_start
frame_end_before=scene.frame_end

scene.frame_set(REST_FRAME)
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
rest_before_points={name:evaluated_world_vertices(bpy.data.objects[name],dg) for name in CLOTHING+EYES+list(SHOES)}

# ---------- transfer clothing weights ----------
src_world,triangles,bvh=build_source_surface(f2)
src_weights=source_weight_table(f2,deform_names)
transfer_stats={}
clothing_metrics={}

for name in CLOTHING:
    obj=bpy.data.objects[name]
    transfer_stats[name]=transfer_weights(f2,obj,deform_names,src_weights,src_world,triangles,bvh)
    clothing_metrics[name]=weight_metrics(obj,deform_names)
    if clothing_metrics[name]["unweighted"]:
        raise RuntimeError(f"Safety stop: {name} has unweighted vertices")
    if clothing_metrics[name]["invalid"]:
        raise RuntimeError(f"Safety stop: {name} has invalid normalized weight sums")
    if clothing_metrics[name]["maximum_influences"]>4:
        raise RuntimeError(f"Safety stop: {name} exceeds four influences per vertex")

# ---------- attach rigid objects ----------
for name,bone in RIGID_ATTACH.items():
    rigid_bone_parent(bpy.data.objects[name],arm,bone)

bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
rest_after_points={name:evaluated_world_vertices(bpy.data.objects[name],dg) for name in CLOTHING+EYES+list(SHOES)}
rest_errors={name:max_point_error(rest_before_points[name],rest_after_points[name]) for name in rest_before_points}
rest_visual_max=max(rest_errors.values(),default=0.0)
if rest_visual_max>REST_TOL:
    raise RuntimeError(f"Safety stop: rest appearance changed; max error={rest_visual_max}")

# ---------- structural validation ----------
parent_checks={}
for name,bone in RIGID_ATTACH.items():
    obj=bpy.data.objects[name]
    parent_checks[name]=(
        obj.parent==arm and
        obj.parent_type=="BONE" and
        obj.parent_bone==bone
    )
attachment_checks=all(parent_checks.values())
if not attachment_checks:
    raise RuntimeError("Safety stop: rigid parent validation failed")

clothing_arm_mod_count=sum(
    1 for name in CLOTHING for m in bpy.data.objects[name].modifiers
    if m.type=="ARMATURE" and m.object==arm
)
if clothing_arm_mod_count!=2:
    raise RuntimeError("Safety stop: expected exactly two clothing Armature modifiers")

# ---------- motion-response validation ----------
scene.frame_set(REST_FRAME)
bpy.context.view_layer.update()
rest_motion_points={name:evaluated_world_vertices(bpy.data.objects[name],dg) for name in MOTION_FRAMES}
motion_metrics={}
motion_checks=True

for name,frame in MOTION_FRAMES.items():
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pts=evaluated_world_vertices(bpy.data.objects[name],dg)
    movement=max_point_error(rest_motion_points[name],pts)
    is_finite=finite(pts)
    passed=is_finite and movement>0.003 and movement<3.0
    motion_checks=motion_checks and passed
    motion_metrics[name]={
        "frame":frame,
        "max_vertex_movement":movement,
        "finite":is_finite,
        "passed":passed,
    }

if not motion_checks:
    failed=[name for name,v in motion_metrics.items() if not v["passed"]]
    raise RuntimeError("Safety stop: motion response failed for "+", ".join(failed))

# ---------- unchanged-resource validation ----------
scene.frame_set(original_frame)
bpy.context.view_layer.update()

f2_after=mesh_binding_snapshot(f2)
f2_changes=[]
if f2_before!=f2_after:
    f2_changes.append("F2 binding snapshot changed")
if arm.animation_data.action.name!=action_before:
    f2_changes.append("deformation action changed")
if f2_changes:
    raise RuntimeError("Safety stop: "+", ".join(f2_changes))

rest_after=rest_bone_snapshot(arm)
rest_changes=[name for name in rest_before if rest_before[name]!=rest_after.get(name)]
if rest_changes:
    raise RuntimeError("Safety stop: armature rest bones changed: "+", ".join(rest_changes))

protected_after={o.name:object_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
protected_changes=[]
if set(protected_before)!=set(protected_after):
    protected_changes.append("object_set_changed")
for name in sorted(set(protected_before)&set(protected_after)):
    if protected_before[name]!=protected_after[name]:
        protected_changes.append(name)
if protected_changes:
    raise RuntimeError("Safety stop: protected object changes: "+", ".join(protected_changes[:10]))

unweighted_total=sum(len(clothing_metrics[name]["unweighted"]) for name in CLOTHING)
invalid_total=sum(len(clothing_metrics[name]["invalid"]) for name in CLOTHING)
frame_range_changed=(scene.frame_start!=frame_start_before or scene.frame_end!=frame_end_before)

status={
    "script_version":SCRIPT_VERSION,
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "rig_name":RIG,
    "preserved_action":arm.animation_data.action.name,
    "deform_group_count":len(deform_names),
    "transfer_method":"NEAREST_F2_TRIANGLE_BARYCENTRIC_TOP4_NORMALIZED",
    "transfer_stats":transfer_stats,
    "clothing_metrics":{
        name:{
            "vertex_count":transfer_stats[name]["vertex_count"],
            "maximum_influences":clothing_metrics[name]["maximum_influences"],
            "influence_histogram":clothing_metrics[name]["influence_histogram"],
            "group_vertex_counts":clothing_metrics[name]["group_vertex_counts"],
            "unweighted_count":len(clothing_metrics[name]["unweighted"]),
            "invalid_weight_sum_count":len(clothing_metrics[name]["invalid"]),
        }
        for name in CLOTHING
    },
    "clothing_armature_modifier_count":clothing_arm_mod_count,
    "clothing_unweighted_vertex_count":unweighted_total,
    "clothing_invalid_weight_sum_count":invalid_total,
    "rigid_attachment_map":RIGID_ATTACH,
    "attachment_parent_checks":parent_checks,
    "attachment_parent_checks_passed":attachment_checks,
    "rest_visual_errors":rest_errors,
    "rest_visual_max_error":rest_visual_max,
    "motion_metrics":motion_metrics,
    "motion_response_checks_passed":motion_checks,
    "f2_change_count":len(f2_changes),
    "f2_changes":f2_changes,
    "armature_rest_change_count":len(rest_changes),
    "armature_rest_changes":rest_changes,
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

with open(os.path.join(OUT,"ClothingAccessoryBindV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"ClothingAccessoryBindV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("SACKBOY CLOTHING / ACCESSORY BIND V1\n")
    f.write(f"transfer_method={status['transfer_method']}\n")
    f.write(f"clothing_armature_modifiers={clothing_arm_mod_count}\n")
    f.write(f"unweighted_vertices={unweighted_total}\n")
    f.write(f"invalid_weight_sums={invalid_total}\n")
    f.write(f"rest_visual_max_error={rest_visual_max:.12f}\n")
    f.write(f"attachment_checks={attachment_checks}\n")
    f.write(f"motion_checks={motion_checks}\n")
    f.write(f"F2_changes={len(f2_changes)}\n")
    f.write(f"rest_bone_changes={len(rest_changes)}\n")
    f.write(f"protected_changes={len(protected_changes)}\n")
    for name in CLOTHING:
        f.write(f"{name}: transfer={transfer_stats[name]} weights={clothing_metrics[name]}\n")
    for name in motion_metrics:
        f.write(f"{name}: motion={motion_metrics[name]}\n")
with open(os.path.join(OUT,"Clothing_Accessory_Bind_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Sackboy Clothing / Accessory Bind v1\n\n")
    f.write(f"- Clothing Armature modifiers: **{clothing_arm_mod_count}**\n")
    f.write(f"- Unweighted clothing vertices: **{unweighted_total}**\n")
    f.write(f"- Invalid clothing weight sums: **{invalid_total}**\n")
    f.write(f"- Rest-pose maximum visual error: **{rest_visual_max:.12f}**\n")
    f.write(f"- Rigid attachment checks: **{attachment_checks}**\n")
    f.write(f"- Test-pose response checks: **{motion_checks}**\n")
    f.write(f"- F2 changes: **{len(f2_changes)}**\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**\n\n")
    f.write("The next stage is dressed-character deformation review and targeted clothing-weight correction.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"ClothingAccessoryBindV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print(f"[version] clothing/accessory bind v{SCRIPT_VERSION}")
print(f"[weights] method={status['transfer_method']} unweighted={unweighted_total} invalid={invalid_total}")
print(f"[rest] max_visual_error={rest_visual_max:.12f}")
print(f"[attachments] passed={attachment_checks} map={RIGID_ATTACH}")
print(f"[motion] passed={motion_checks} metrics={motion_metrics}")
print(f"[safety] F2_changes={len(f2_changes)} rest_bone_changes={len(rest_changes)} protected_changes={len(protected_changes)} frame_range_changed={frame_range_changed}")
print("[save] blend saved")
