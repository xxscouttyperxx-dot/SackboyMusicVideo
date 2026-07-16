
import bpy, os, json
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","unweighted_armature_placement_v1")
os.makedirs(OUT,exist_ok=True)

RIG_NAME="SACKBOY_RIG_PLACEMENT_V1"
COLLECTION_NAME="RIGGING_PREVIEW"
TARGETS=["F2","Lowerpoly hoodie","Cargo pants","L.Eye","R.Eye","Plane.001","Plane.022"]

def mat_list(m):
    return [[float(m[r][c]) for c in range(4)] for r in range(4)]

def mesh_signature(obj):
    me=obj.data
    return {
        "mesh":me.name,
        "vertices":len(me.vertices),
        "edges":len(me.edges),
        "polygons":len(me.polygons),
        "shape_keys":len(me.shape_keys.key_blocks) if me.shape_keys else 0,
        "matrix_world":mat_list(obj.matrix_world),
        "parent":obj.parent.name if obj.parent else "",
        "modifier_types":[m.type for m in obj.modifiers],
    }

def protected_snapshot(obj):
    ad=obj.animation_data
    return {
        "type":obj.type,
        "data":getattr(obj.data,"name",""),
        "parent":obj.parent.name if obj.parent else "",
        "matrix_world":mat_list(obj.matrix_world),
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "action":ad.action.name if ad and ad.action else "",
        "drivers":len(ad.drivers) if ad else 0,
        "nla":len(ad.nla_tracks) if ad else 0,
        "modifiers":[m.name for m in obj.modifiers],
        "constraints":[c.name for c in obj.constraints],
    }

missing=[n for n in TARGETS if bpy.data.objects.get(n) is None]
if missing:
    raise RuntimeError("Missing rig targets: "+", ".join(missing))
if bpy.data.objects.get(RIG_NAME):
    raise RuntimeError(f"Safety stop: {RIG_NAME} already exists")
if any(o.type=="ARMATURE" for o in bpy.data.objects):
    raise RuntimeError("Safety stop: an armature already exists in the scene")

f2=bpy.data.objects["F2"]
if f2.type!="MESH":
    raise RuntimeError("F2 is not a mesh")
if f2.data.shape_keys:
    raise RuntimeError("Safety stop: F2 still has shape keys; clean baseline not confirmed")

target_before={n:mesh_signature(bpy.data.objects[n]) for n in TARGETS}
mutable=set(TARGETS)
protected_before={o.name:protected_snapshot(o) for o in bpy.data.objects if o.name not in mutable}

# World-space character bounds from F2.
corners=[f2.matrix_world @ Vector(c) for c in f2.bound_box]
mn=Vector((min(p.x for p in corners),min(p.y for p in corners),min(p.z for p in corners)))
mx=Vector((max(p.x for p in corners),max(p.y for p in corners),max(p.z for p in corners)))
ctr=(mn+mx)*0.5
dim=mx-mn
x0,y0=ctr.x,ctr.y
z0,z1=mn.z,mx.z
sx,sy,sz=dim.x,dim.y,dim.z

# Stylized neutral-placement landmarks.
P={}
P["root_h"]=Vector((x0,y0,z0-0.06*sz)); P["root_t"]=Vector((x0,y0,z0+0.12*sz))
P["pelvis_h"]=P["root_t"]; P["pelvis_t"]=Vector((x0,y0,z0+0.37*sz))
P["spine_h"]=P["pelvis_t"]; P["spine_t"]=Vector((x0,y0,z0+0.54*sz))
P["chest_h"]=P["spine_t"]; P["chest_t"]=Vector((x0,y0,z0+0.70*sz))
P["neck_h"]=P["chest_t"]; P["neck_t"]=Vector((x0,y0,z0+0.79*sz))
P["head_h"]=P["neck_t"]; P["head_t"]=Vector((x0,y0,z0+0.98*sz))

shoulder_z=z0+0.68*sz
elbow_z=z0+0.50*sz
wrist_z=z0+0.36*sz
for side,sgn in (("L",-1.0),("R",1.0)):
    P[f"clavicle.{side}_h"]=Vector((x0,y0,shoulder_z))
    P[f"clavicle.{side}_t"]=Vector((x0+sgn*0.20*sx,y0,shoulder_z))
    P[f"upper_arm.{side}_h"]=P[f"clavicle.{side}_t"]
    P[f"upper_arm.{side}_t"]=Vector((x0+sgn*0.34*sx,y0,elbow_z))
    P[f"forearm.{side}_h"]=P[f"upper_arm.{side}_t"]
    P[f"forearm.{side}_t"]=Vector((x0+sgn*0.44*sx,y0,wrist_z))
    P[f"hand.{side}_h"]=P[f"forearm.{side}_t"]
    P[f"hand.{side}_t"]=Vector((x0+sgn*0.50*sx,y0,z0+0.31*sz))

hip_z=z0+0.38*sz
knee_z=z0+0.19*sz
ankle_z=z0+0.045*sz
foot_y_front=mn.y-0.10*sy
toe_y_front=mn.y-0.24*sy
for side,sgn in (("L",-1.0),("R",1.0)):
    xhip=x0+sgn*0.12*sx
    P[f"thigh.{side}_h"]=Vector((xhip,y0,hip_z))
    P[f"thigh.{side}_t"]=Vector((xhip,y0,knee_z))
    P[f"shin.{side}_h"]=P[f"thigh.{side}_t"]
    P[f"shin.{side}_t"]=Vector((xhip,y0,ankle_z))
    P[f"foot.{side}_h"]=P[f"shin.{side}_t"]
    P[f"foot.{side}_t"]=Vector((xhip,foot_y_front,z0+0.04*sz))
    P[f"toe.{side}_h"]=P[f"foot.{side}_t"]
    P[f"toe.{side}_t"]=Vector((xhip,toe_y_front,z0+0.035*sz))

# Collection.
collection=bpy.data.collections.get(COLLECTION_NAME)
if collection is None:
    collection=bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

arm_data=bpy.data.armatures.new(RIG_NAME+"_Data")
arm_obj=bpy.data.objects.new(RIG_NAME,arm_data)
collection.objects.link(arm_obj)
arm_obj.show_in_front=True
# Object display_type controls viewport shading and does not accept bone styles.
# Bone style belongs to the Armature datablock in Blender 5.1.
arm_obj.display_type="SOLID"
arm_data.display_type="OCTAHEDRAL"

bpy.context.view_layer.objects.active=arm_obj
arm_obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")

def add_bone(name,head,tail,parent=None,connected=False,deform=True):
    b=arm_data.edit_bones.new(name)
    b.head=head
    b.tail=tail
    b.use_deform=deform
    if parent:
        b.parent=arm_data.edit_bones.get(parent)
        b.use_connect=connected
    return b

add_bone("root",P["root_h"],P["root_t"],deform=False)
add_bone("pelvis",P["pelvis_h"],P["pelvis_t"],"root",True)
add_bone("spine",P["spine_h"],P["spine_t"],"pelvis",True)
add_bone("chest",P["chest_h"],P["chest_t"],"spine",True)
add_bone("neck",P["neck_h"],P["neck_t"],"chest",True)
add_bone("head",P["head_h"],P["head_t"],"neck",True)

for side in ("L","R"):
    add_bone(f"clavicle.{side}",P[f"clavicle.{side}_h"],P[f"clavicle.{side}_t"],"chest",False)
    add_bone(f"upper_arm.{side}",P[f"upper_arm.{side}_h"],P[f"upper_arm.{side}_t"],f"clavicle.{side}",True)
    add_bone(f"forearm.{side}",P[f"forearm.{side}_h"],P[f"forearm.{side}_t"],f"upper_arm.{side}",True)
    add_bone(f"hand.{side}",P[f"hand.{side}_h"],P[f"hand.{side}_t"],f"forearm.{side}",True)
    add_bone(f"thigh.{side}",P[f"thigh.{side}_h"],P[f"thigh.{side}_t"],"pelvis",False)
    add_bone(f"shin.{side}",P[f"shin.{side}_h"],P[f"shin.{side}_t"],f"thigh.{side}",True)
    add_bone(f"foot.{side}",P[f"foot.{side}_h"],P[f"foot.{side}_t"],f"shin.{side}",True)
    add_bone(f"toe.{side}",P[f"toe.{side}_h"],P[f"toe.{side}_t"],f"foot.{side}",True)

bpy.ops.object.mode_set(mode="OBJECT")
arm_obj.select_set(False)
bpy.context.view_layer.update()

# Validate no target mesh changes, parents, or armature modifiers.
target_after={n:mesh_signature(bpy.data.objects[n]) for n in TARGETS}
mesh_changes=[n for n in TARGETS if target_before[n]!=target_after[n]]
arm_mod_count=sum(1 for n in TARGETS for m in bpy.data.objects[n].modifiers if m.type=="ARMATURE")
parented_count=sum(1 for n in TARGETS if bpy.data.objects[n].parent is not None)

protected_after={o.name:protected_snapshot(o) for o in bpy.data.objects if o.name not in mutable and o.name!=RIG_NAME}
protected_changes=[]
for name in sorted(set(protected_before)&set(protected_after)):
    if protected_before[name]!=protected_after[name]:
        protected_changes.append(name)
if set(protected_before)-set(protected_after):
    protected_changes.extend(sorted(set(protected_before)-set(protected_after)))

if mesh_changes:
    raise RuntimeError("Safety stop: target mesh changes detected: "+", ".join(mesh_changes))
if arm_mod_count:
    raise RuntimeError("Safety stop: Armature modifiers were added")
if parented_count:
    raise RuntimeError("Safety stop: character targets were parented")
if protected_changes:
    raise RuntimeError("Safety stop: protected object changes: "+", ".join(protected_changes[:10]))

bones=[]
for b in arm_data.bones:
    bones.append({
        "name":b.name,
        "parent":b.parent.name if b.parent else "",
        "use_deform":b.use_deform,
        "head_local":list(b.head_local),
        "tail_local":list(b.tail_local),
        "length":b.length,
    })

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "armature_name":RIG_NAME,
    "collection_name":COLLECTION_NAME,
    "armature_count_after":sum(1 for o in bpy.data.objects if o.type=="ARMATURE"),
    "bone_count":len(arm_data.bones),
    "bones":bones,
    "f2_bounds_min":list(mn),
    "f2_bounds_max":list(mx),
    "f2_dimensions_world":list(dim),
    "character_mesh_change_count":len(mesh_changes),
    "character_mesh_changes":mesh_changes,
    "armature_modifier_count_after":arm_mod_count,
    "parented_target_count_after":parented_count,
    "protected_change_count":len(protected_changes),
    "protected_changes":protected_changes,
    "created_backup_blend_files":0,
}

with open(os.path.join(OUT,"UnweightedArmaturePlacementV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)
with open(os.path.join(OUT,"UnweightedArmaturePlacementV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("UNWEIGHTED ARMATURE PLACEMENT V1\n")
    f.write(f"armature={RIG_NAME}\ncollection={COLLECTION_NAME}\nbones={len(bones)}\n")
    f.write(f"F2 bounds min={list(mn)}\nF2 bounds max={list(mx)}\nF2 dimensions={list(dim)}\n")
    f.write(f"mesh_changes={len(mesh_changes)}\narmature_modifiers={arm_mod_count}\nparented_targets={parented_count}\nprotected_changes={len(protected_changes)}\n")
    f.write("\nBONES\n")
    for b in bones:
        f.write(f"{b['name']} | parent={b['parent']} | deform={b['use_deform']} | head={b['head_local']} | tail={b['tail_local']}\n")
with open(os.path.join(OUT,"Unweighted_Armature_Placement_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Unweighted Armature Placement v1\n\n")
    f.write(f"- Armature: `{RIG_NAME}`\n- Collection: `{COLLECTION_NAME}`\n- Bones: **{len(bones)}**\n")
    f.write(f"- Character mesh changes: **{len(mesh_changes)}**\n- Armature modifiers: **{arm_mod_count}**\n- Parented targets: **{parented_count}**\n- Protected changes: **{len(protected_changes)}**\n\n")
    f.write("This is an unweighted placement rig for visual inspection only.\n")

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
status["saved_blend"]=True
with open(os.path.join(OUT,"UnweightedArmaturePlacementV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

print("[rig] unweighted armature placement complete")
print(f"[armature] name={RIG_NAME} bones={len(bones)}")
print(f"[safety] mesh_changes={len(mesh_changes)} armature_modifiers={arm_mod_count} parented_targets={parented_count} protected_changes={len(protected_changes)}")
print("[save] blend saved")
