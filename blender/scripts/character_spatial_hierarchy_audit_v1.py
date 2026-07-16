
import bpy, os, json, csv, math
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
OUT=os.path.join(ROOT,"reports","character_spatial_hierarchy_audit_v1")
CSV_DIR=os.path.join(OUT,"csv")
os.makedirs(CSV_DIR,exist_ok=True)

def safe(v):
    if isinstance(v,(str,int,float,bool)) or v is None:
        return v
    if hasattr(v,"to_list"):
        try:return v.to_list()
        except:pass
    try:return list(v)
    except:return str(v)

def csv_write(name, rows, fallback):
    path=os.path.join(CSV_DIR,name)
    header=list(rows[0].keys()) if rows else fallback
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=header,extrasaction="ignore")
        w.writeheader()
        for r in rows:w.writerow(r)

def bounds_world(obj):
    pts=[obj.matrix_world@Vector(corner) for corner in obj.bound_box]
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx,(mn+mx)*0.5,mx-mn

def category(obj):
    blob=" ".join([obj.name,getattr(obj.data,"name","")," ".join(c.name for c in obj.users_collection)]).lower()
    protected=any(k in blob for k in ("lightning","bolt","cloud","fog","storm","volume"))
    if protected:return "PROTECTED_EFFECT"
    if any(k in blob for k in ("hoodie","hood","shirt","sweater","cargo","pant","cloth","clothing","sleeve","collar")):
        return "CLOTHING"
    if any(k in blob for k in ("f2","sackboy","eye","mouth","hand","arm","leg","foot","shoe","boot","sock","head","body","face")):
        return "CHARACTER"
    return "OTHER"

all_rows=[]
char_rows=[]
axis_rows=[]
shape_rows=[]
hierarchy_rows=[]
protected_rows=[]
near_empties=[]
landmarks={}
shape_cleanup_scope=[]

f2=bpy.data.objects.get("F2")
if f2 and f2.type=="MESH":
    f2_mn,f2_mx,f2_center,f2_dim=bounds_world(f2)
else:
    f2_mn=f2_mx=f2_center=f2_dim=None

for obj in bpy.data.objects:
    cat=category(obj)
    collections=[c.name for c in obj.users_collection]
    row={
        "name":obj.name,
        "type":obj.type,
        "category":cat,
        "data_name":getattr(obj.data,"name",""),
        "data_users":getattr(obj.data,"users",0) if getattr(obj,"data",None) else 0,
        "collections":" | ".join(collections),
        "parent":obj.parent.name if obj.parent else "",
        "parent_type":obj.parent_type,
        "children":" | ".join(child.name for child in obj.children),
        "hide_viewport":obj.hide_viewport,
        "hide_render":obj.hide_render,
        "visible":obj.visible_get(),
        "location":safe(obj.location),
        "rotation_euler":safe(obj.rotation_euler),
        "scale":safe(obj.scale),
        "matrix_world_translation":safe(obj.matrix_world.translation),
        "matrix_parent_inverse_translation":safe(obj.matrix_parent_inverse.translation),
        "modifier_count":len(obj.modifiers),
        "constraint_count":len(obj.constraints),
        "animation_action":obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else "",
        "driver_count":len(obj.animation_data.drivers) if obj.animation_data else 0,
        "nla_track_count":len(obj.animation_data.nla_tracks) if obj.animation_data else 0,
    }
    if obj.type in {"MESH","CURVE","SURFACE","META","FONT"}:
        mn,mx,ctr,dim=bounds_world(obj)
        origin=obj.matrix_world.translation
        dist=(origin-ctr).length
        row.update({
            "bounds_min":safe(mn),"bounds_max":safe(mx),"bounds_center":safe(ctr),"dimensions_world":safe(dim),
            "origin_to_bounds_center":dist,
            "origin_detached_candidate":dist>max(dim.length*0.35,0.25),
        })
        if row["origin_detached_candidate"]:
            axis_rows.append({
                "object":obj.name,"category":cat,"origin_world":safe(origin),"bounds_center":safe(ctr),
                "distance":dist,"dimensions_world":safe(dim),
                "parent":row["parent"],"data_users":row["data_users"],
            })
    else:
        row.update({
            "bounds_min":"","bounds_max":"","bounds_center":"","dimensions_world":"",
            "origin_to_bounds_center":"","origin_detached_candidate":False,
        })
    all_rows.append(row)

    if cat in {"CHARACTER","CLOTHING"}:
        char_rows.append(row)

    if cat=="PROTECTED_EFFECT":
        protected_rows.append({
            "name":obj.name,"type":obj.type,"data_name":getattr(obj.data,"name",""),
            "collections":" | ".join(collections),"parent":row["parent"],
            "action":row["animation_action"],"driver_count":row["driver_count"],
            "modifier_count":row["modifier_count"],"visible":row["visible"],
            "location":safe(obj.location),"scale":safe(obj.scale),
        })

    if obj.parent or obj.children:
        hierarchy_rows.append({
            "object":obj.name,"category":cat,"parent":row["parent"],
            "parent_type":obj.parent_type,"children":row["children"],
            "matrix_parent_inverse_translation":row["matrix_parent_inverse_translation"],
        })

    if obj.type=="EMPTY" and f2_center is not None:
        d=(obj.matrix_world.translation-f2_center).length
        if d<=max(f2_dim.length*1.5,5.0):
            near_empties.append({
                "name":obj.name,"empty_display_type":obj.empty_display_type,
                "empty_display_size":obj.empty_display_size,
                "location_world":safe(obj.matrix_world.translation),
                "distance_to_F2_center":d,
                "parent":row["parent"],"children":row["children"],
                "category":cat,
            })

    if obj.type=="MESH" and obj.data.shape_keys:
        keys=[]
        for kb in obj.data.shape_keys.key_blocks:
            keys.append(kb.name)
            shape_rows.append({
                "object":obj.name,"category":cat,"shape_key":kb.name,
                "value":kb.value,"mute":kb.mute,
                "slider_min":kb.slider_min,"slider_max":kb.slider_max,
                "relative_key":kb.relative_key.name if kb.relative_key else "",
            })
        if cat in {"CHARACTER","CLOTHING","OTHER"}:
            shape_cleanup_scope.append({
                "object":obj.name,"category":cat,
                "shape_keys":" | ".join(keys),
                "current_values":" | ".join(f"{kb.name}={kb.value}" for kb in obj.data.shape_keys.key_blocks),
                "protected":cat=="PROTECTED_EFFECT",
                "visible":obj.visible_get() and not obj.hide_render,
            })

# Heuristic joint landmarks from F2 world bounds, only as later placement references.
if f2_center is not None:
    x0,y0,z0=f2_center
    sx,sy,sz=f2_dim
    landmarks={
        "character_center":safe(f2_center),
        "root":safe(Vector((x0,y0,f2_mn.z+sz*0.12))),
        "pelvis":safe(Vector((x0,y0,f2_mn.z+sz*0.38))),
        "spine":safe(Vector((x0,y0,f2_mn.z+sz*0.52))),
        "chest":safe(Vector((x0,y0,f2_mn.z+sz*0.66))),
        "neck":safe(Vector((x0,y0,f2_mn.z+sz*0.78))),
        "head":safe(Vector((x0,y0,f2_mn.z+sz*0.90))),
        "shoulder_L":safe(Vector((x0-sx*0.26,y0,f2_mn.z+sz*0.70))),
        "shoulder_R":safe(Vector((x0+sx*0.26,y0,f2_mn.z+sz*0.70))),
        "elbow_L":safe(Vector((x0-sx*0.42,y0,f2_mn.z+sz*0.57))),
        "elbow_R":safe(Vector((x0+sx*0.42,y0,f2_mn.z+sz*0.57))),
        "wrist_L":safe(Vector((x0-sx*0.49,y0,f2_mn.z+sz*0.45))),
        "wrist_R":safe(Vector((x0+sx*0.49,y0,f2_mn.z+sz*0.45))),
        "hip_L":safe(Vector((x0-sx*0.14,y0,f2_mn.z+sz*0.38))),
        "hip_R":safe(Vector((x0+sx*0.14,y0,f2_mn.z+sz*0.38))),
        "knee_L":safe(Vector((x0-sx*0.14,y0,f2_mn.z+sz*0.21))),
        "knee_R":safe(Vector((x0+sx*0.14,y0,f2_mn.z+sz*0.21))),
        "ankle_L":safe(Vector((x0-sx*0.14,y0,f2_mn.z+sz*0.05))),
        "ankle_R":safe(Vector((x0+sx*0.14,y0,f2_mn.z+sz*0.05))),
    }

summary={
    "object_count":len(all_rows),
    "character_object_count":len(char_rows),
    "visible_character_object_count":sum(1 for r in char_rows if r["visible"] and not r["hide_render"]),
    "shape_key_object_count":len({r["object"] for r in shape_rows}),
    "shape_key_count":len(shape_rows),
    "animated_object_count":sum(1 for r in all_rows if r["animation_action"] or r["driver_count"] or r["nla_track_count"]),
    "parented_object_count":sum(1 for r in all_rows if r["parent"]),
    "detached_origin_candidate_count":len(axis_rows),
    "character_near_empty_count":len(near_empties),
    "protected_effect_object_count":len(protected_rows),
}

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "blend_file":bpy.data.filepath,
    "saved_blend":False,
    "created_backup_blend_files":0,
    "summary":summary,
    "character_objects":char_rows,
    "origin_and_axis_audit":{
        "detached_origin_candidates":axis_rows,
        "character_near_empties":near_empties,
        "note":"Visible axes may be object origins or Empty objects. This audit does not remove or move them."
    },
    "shape_keys":shape_rows,
    "shape_key_cleanup_scope":shape_cleanup_scope,
    "hierarchy":hierarchy_rows,
    "protected_effect_objects":protected_rows,
    "candidate_joint_landmarks":landmarks,
}

with open(os.path.join(OUT,"CharacterSpatialHierarchyAuditV1_status.json"),"w",encoding="utf-8") as f:
    json.dump(status,f,indent=2)

with open(os.path.join(OUT,"CharacterSpatialHierarchyAuditV1_report.txt"),"w",encoding="utf-8") as f:
    f.write("CHARACTER SPATIAL / HIERARCHY AUDIT V1\n")
    for k,v in summary.items():f.write(f"{k}={v}\n")
    f.write("\nSHAPE KEY CLEANUP SCOPE\n")
    for r in shape_cleanup_scope:
        f.write(f"{r['object']} | category={r['category']} | visible={r['visible']} | protected={r['protected']} | {r['current_values']}\n")
    f.write("\nDETACHED ORIGIN CANDIDATES\n")
    for r in axis_rows:
        f.write(f"{r['object']} | category={r['category']} | distance={r['distance']:.6f} | parent={r['parent']}\n")
    f.write("\nPROTECTED EFFECT OBJECTS\n")
    for r in protected_rows:
        f.write(f"{r['name']} | type={r['type']} | action={r['action']} | drivers={r['driver_count']} | modifiers={r['modifier_count']}\n")

with open(os.path.join(OUT,"Character_Spatial_Hierarchy_Audit_V1.md"),"w",encoding="utf-8") as f:
    f.write("# Character Spatial / Hierarchy Audit v1\n\n")
    f.write(f"- Character/clothing candidates: **{summary['character_object_count']}**\n")
    f.write(f"- Shape-key objects: **{summary['shape_key_object_count']}**\n")
    f.write(f"- Potential detached origins: **{summary['detached_origin_candidate_count']}**\n")
    f.write(f"- Nearby Empty/axis objects: **{summary['character_near_empty_count']}**\n")
    f.write(f"- Protected lightning/cloud/fog objects: **{summary['protected_effect_object_count']}**\n\n")
    f.write("## Shape-key cleanup scope\n\n")
    for r in shape_cleanup_scope:
        f.write(f"- `{r['object']}` — {r['category']}; visible={r['visible']}; protected={r['protected']}; `{r['current_values']}`\n")
    f.write("\n## Detached-origin candidates\n\n")
    if axis_rows:
        for r in axis_rows:
            f.write(f"- `{r['object']}` — origin-to-geometry-center distance `{r['distance']:.6f}`\n")
    else:
        f.write("- None detected by the current threshold.\n")
    f.write("\n## Protected effects\n\n")
    for r in protected_rows:
        f.write(f"- `{r['name']}` ({r['type']})\n")
    f.write("\nThis audit did not save or modify the blend.\n")

csv_write("all_objects.csv",all_rows,["name"])
csv_write("character_objects.csv",char_rows,["name"])
csv_write("origin_detached_candidates.csv",axis_rows,["object"])
csv_write("nearby_empties_axes.csv",near_empties,["name"])
csv_write("shape_keys.csv",shape_rows,["object"])
csv_write("shape_key_cleanup_scope.csv",shape_cleanup_scope,["object"])
csv_write("hierarchy.csv",hierarchy_rows,["object"])
csv_write("protected_effect_objects.csv",protected_rows,["name"])

print("[audit] character spatial/hierarchy complete")
print(f"[character] candidates={summary['character_object_count']} visible={summary['visible_character_object_count']}")
print(f"[shape_keys] objects={summary['shape_key_object_count']} keys={summary['shape_key_count']}")
print(f"[origins] detached_candidates={summary['detached_origin_candidate_count']} nearby_empties={summary['character_near_empty_count']}")
print(f"[protected] lightning_cloud_fog_objects={summary['protected_effect_object_count']}")
print("[safety] saved_blend=False created_backup_blend_files=0")
