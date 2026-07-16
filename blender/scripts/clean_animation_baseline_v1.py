
import bpy, os, json, csv, hashlib
from mathutils import Vector, Matrix
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","clean_animation_baseline_v1")
os.makedirs(OUT,exist_ok=True)

TARGET_MESHES=["F2","Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]
SHOE_MESHES=["Plane.001","Plane.022"]
SHOES_EMPTY="Shoes"
TOL=1.0e-5

def matrix_list(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def obj_snapshot(obj):
    ad=obj.animation_data
    return {
        "type":obj.type,
        "data_name":getattr(obj.data,"name",""),
        "parent":obj.parent.name if obj.parent else "",
        "matrix_world":matrix_list(obj.matrix_world),
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "driver_count":len(ad.drivers) if ad else 0,
        "nla_count":len(ad.nla_tracks) if ad else 0,
        "modifier_names":[m.name for m in obj.modifiers],
        "constraint_names":[c.name for c in obj.constraints],
    }

def evaluated_world_vertices(obj, depsgraph):
    ev=obj.evaluated_get(depsgraph)
    mesh=ev.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        mw=ev.matrix_world.copy()
        return [mw @ v.co for v in mesh.vertices]
    finally:
        ev.to_mesh_clear()

def max_point_error(a,b):
    if len(a)!=len(b):
        raise RuntimeError(f"Vertex count changed: {len(a)} -> {len(b)}")
    return max(((x-y).length for x,y in zip(a,b)), default=0.0)

def clear_animation(obj):
    had=False
    if obj.animation_data:
        had=bool(obj.animation_data.action or len(obj.animation_data.drivers) or len(obj.animation_data.nla_tracks))
        obj.animation_data_clear()
    return had

def normalize_origin_preserve_geometry(obj):
    if obj.type!="MESH":
        raise RuntimeError(f"{obj.name} is not a mesh")
    mesh=obj.data
    if len(mesh.vertices)==0:
        raise RuntimeError(f"{obj.name} has no vertices")
    center=sum((v.co for v in mesh.vertices),Vector())/len(mesh.vertices)
    old_world=obj.matrix_world.copy()
    for v in mesh.vertices:
        v.co-=center
    mesh.update()
    obj.matrix_world=old_world @ Matrix.Translation(center)
    return center

# Exact required-object preflight.
missing=[name for name in TARGET_MESHES+[SHOES_EMPTY] if bpy.data.objects.get(name) is None]
if missing:
    raise RuntimeError("Missing required objects: "+", ".join(missing))

f2=bpy.data.objects["F2"]
if f2.type!="MESH":
    raise RuntimeError("F2 is not a mesh")
if len(f2.modifiers)!=0:
    raise RuntimeError("Safety stop: F2 has modifiers; baking method requires zero F2 modifiers")

shoes_empty=bpy.data.objects[SHOES_EMPTY]
if shoes_empty.type!="EMPTY":
    raise RuntimeError("Safety stop: Shoes is not an Empty")
child_names=sorted(c.name for c in shoes_empty.children)
if child_names!=sorted(SHOE_MESHES):
    raise RuntimeError(f"Safety stop: Shoes Empty children are {child_names}, expected {SHOE_MESHES}")

# Preserve every non-target object by exact snapshot.
mutable=set(TARGET_MESHES+[SHOES_EMPTY])
protected_before={o.name:obj_snapshot(o) for o in bpy.data.objects if o.name not in mutable}
protected_names_before=set(protected_before)

scene=bpy.context.scene
original_frame=scene.frame_current
depsgraph=bpy.context.evaluated_depsgraph_get()

visual_before={name:evaluated_world_vertices(bpy.data.objects[name],depsgraph) for name in TARGET_MESHES}
origin_before={name:list(bpy.data.objects[name].matrix_world.translation) for name in TARGET_MESHES}
animation_before={}
for name in TARGET_MESHES+[SHOES_EMPTY]:
    o=bpy.data.objects[name]
    ad=o.animation_data
    animation_before[name]={
        "action":ad.action.name if ad and ad.action else "",
        "drivers":len(ad.drivers) if ad else 0,
        "nla":len(ad.nla_tracks) if ad else 0,
    }

# Freeze current transforms by clearing target animation data only.
cleared=[]
for name in TARGET_MESHES+[SHOES_EMPTY]:
    if clear_animation(bpy.data.objects[name]):
        cleared.append(name)

# Bake current F2 evaluated shape to a new permanent mesh with no shape keys.
shape_keys_before=len(f2.data.shape_keys.key_blocks) if f2.data.shape_keys else 0
old_mesh=f2.data
old_mesh_name=old_mesh.name
ev=f2.evaluated_get(depsgraph)
new_mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=depsgraph)
if len(new_mesh.vertices)!=len(old_mesh.vertices):
    bpy.data.meshes.remove(new_mesh)
    raise RuntimeError("Safety stop: F2 evaluated vertex count differs from source")
old_mesh.name=old_mesh_name+"_PreBake_Orphan"
new_mesh.name=old_mesh_name
f2.data=new_mesh
if old_mesh.users==0:
    bpy.data.meshes.remove(old_mesh)

if f2.data.shape_keys is not None:
    raise RuntimeError("Safety stop: baked F2 mesh still contains shape keys")

# Unparent shoe meshes with exact world-transform preservation.
shoe_world_before={name:bpy.data.objects[name].matrix_world.copy() for name in SHOE_MESHES}
for name in SHOE_MESHES:
    obj=bpy.data.objects[name]
    world=obj.matrix_world.copy()
    obj.parent=None
    obj.matrix_parent_inverse=Matrix.Identity(4)
    obj.matrix_world=world

# Remove exact Shoes Empty only.
bpy.data.objects.remove(shoes_empty,do_unlink=True)

# Normalize approved origins only.
origin_offsets={}
for name in TARGET_MESHES:
    origin_offsets[name]=list(normalize_origin_preserve_geometry(bpy.data.objects[name]))

bpy.context.view_layer.update()
depsgraph=bpy.context.evaluated_depsgraph_get()

visual_after={name:evaluated_world_vertices(bpy.data.objects[name],depsgraph) for name in TARGET_MESHES}
errors={name:max_point_error(visual_before[name],visual_after[name]) for name in TARGET_MESHES}
max_error=max(errors.values(),default=0.0)
if max_error>TOL:
    raise RuntimeError(f"Safety stop: evaluated world geometry changed; max error={max_error}")

# Verify shoe world matrices remained stable through unparenting before origin normalization
# by relying on the stronger evaluated-geometry comparison above.

# Verify all non-target objects remain byte-for-byte equivalent at the audited property level.
protected_after={o.name:obj_snapshot(o) for o in bpy.data.objects if o.name not in set(TARGET_MESHES)}
protected_names_after=set(protected_after)
protected_changes=[]

if protected_names_before!=protected_names_after:
    protected_changes.append({
        "kind":"object_set",
        "before_only":sorted(protected_names_before-protected_names_after),
        "after_only":sorted(protected_names_after-protected_names_before),
    })

for name in sorted(protected_names_before & protected_names_after):
    if protected_before[name]!=protected_after[name]:
        protected_changes.append({
            "kind":"object_changed",
            "object":name,
            "before":protected_before[name],
            "after":protected_after[name],
        })

if protected_changes:
    raise RuntimeError(f"Safety stop: {len(protected_changes)} protected object changes detected")

# Verify target animation data is fully clean.
target_animation_after=0
for name in TARGET_MESHES:
    ad=bpy.data.objects[name].animation_data
    if ad and (ad.action or len(ad.drivers) or len(ad.nla_tracks)):
        target_animation_after+=1

if target_animation_after:
    raise RuntimeError("Safety stop: target animation data remains")

shape_keys_after=len(f2.data.shape_keys.key_blocks) if f2.data.shape_keys else 0
armatures_after=sum(1 for o in bpy.data.objects if o.type=="ARMATURE")
if armatures_after!=0:
    raise RuntimeError("Safety stop: armature unexpectedly exists")

scene.frame_set(original_frame)
bpy.context.view_layer.update()

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "approved_targets":TARGET_MESHES,
    "f2_shape_keys_before":shape_keys_before,
    "f2_shape_keys_after":shape_keys_after,
    "origins_normalized_count":len(origin_offsets),
    "origin_offsets_local":origin_offsets,
    "origin_world_before":origin_before,
    "origin_world_after":{name:list(bpy.data.objects[name].matrix_world.translation) for name in TARGET_MESHES},
    "shoes_empty_removed":bpy.data.objects.get(SHOES_EMPTY) is None,
    "shoe_parents_after":{name:(bpy.data.objects[name].parent.name if bpy.data.objects[name].parent else "") for name in SHOE_MESHES},
    "target_animation_before":animation_before,
    "target_animation_data_cleared":cleared,
    "target_animation_data_after":target_animation_after,
    "visual_world_error_by_object":errors,
    "max_visual_world_error":max_error,
    "protected_object_count":len(protected_before),
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "armatures_after":armatures_after,
    "scene_frame_preserved":scene.frame_current==original_frame,
    "created_backup_blend_files":0,
}

# Save report before blend save; then update status saved_blend and save once.
with open(os.path.join(OUT,"CleanAnimationBaselineV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

with open(os.path.join(OUT,"CleanAnimationBaselineV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("CLEAN ANIMATION BASELINE V1\n")
    f.write(f"F2 shape keys: {shape_keys_before} -> {shape_keys_after}\n")
    f.write(f"Origins normalized: {len(origin_offsets)}\n")
    f.write(f"Shoes Empty removed: {status['shoes_empty_removed']}\n")
    f.write(f"Target animation data cleared: {', '.join(cleared) if cleared else 'none'}\n")
    f.write(f"Maximum evaluated world-space error: {max_error:.12f}\n")
    f.write(f"Protected object changes: {len(protected_changes)}\n")
    f.write(f"Armatures after: {armatures_after}\n")
    f.write("\nPER-OBJECT VISUAL ERRORS\n")
    for name in TARGET_MESHES:
        f.write(f"{name}: {errors[name]:.12f}\n")

with open(os.path.join(OUT,"Clean_Animation_Baseline_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Clean Animation Baseline v1\n\n")
    f.write(f"- F2 shape keys: **{shape_keys_before} → {shape_keys_after}**\n")
    f.write(f"- Origins normalized: **{len(origin_offsets)}**\n")
    f.write(f"- Shoes Empty removed: **{status['shoes_empty_removed']}**\n")
    f.write(f"- Maximum visual world error: **{max_error:.12f}**\n")
    f.write(f"- Protected changes: **{len(protected_changes)}**\n")
    f.write(f"- Armatures: **{armatures_after}**\n\n")
    f.write("## Approved targets\n\n")
    for name in TARGET_MESHES:
        f.write(f"- `{name}` — visual error `{errors[name]:.12f}`\n")
    f.write("\nNo lightning, fog, cloud, lamp, camera, car or environment object was changed.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

status["saved_blend"]=True
with open(os.path.join(OUT,"CleanAnimationBaselineV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print("[baseline] clean animation baseline complete")
print(f"[shape_keys] F2 {shape_keys_before}->{shape_keys_after}")
print(f"[origins] normalized={len(origin_offsets)} max_visual_error={max_error:.12f}")
print(f"[shoes] empty_removed={status['shoes_empty_removed']} parents={status['shoe_parents_after']}")
print(f"[animation] cleared_targets={len(cleared)} remaining={target_animation_after}")
print(f"[protected] objects={len(protected_before)} changes={len(protected_changes)}")
print(f"[armatures] after={armatures_after}")
print("[save] blend saved")
