
import bpy, os, json, csv
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath), ".."))
OUT = os.path.join(ROOT, "reports", "rigging_readiness_audit_v1")
CSV_DIR = os.path.join(OUT, "csv")
os.makedirs(CSV_DIR, exist_ok=True)

def safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_list"):
        try:
            return value.to_list()
        except Exception:
            pass
    try:
        return list(value)
    except Exception:
        return str(value)

def write_csv(filename, rows, fallback_header):
    path = os.path.join(CSV_DIR, filename)
    header = list(rows[0].keys()) if rows else fallback_header
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

scene = bpy.context.scene
objects, meshes, armatures = [], [], []
modifiers, constraints = [], []
vertex_groups, shape_keys = [], []
materials, collections, actions = [], [], []
cameras, lights, external_files = [], [], []
rigging_candidates = []

character_terms = ("f2","sackboy","body","head","face","eye","mouth","hand","arm","leg","foot","shoe","boot","sock")
clothing_terms = ("hoodie","shirt","sweater","pant","cargo","cloth","clothing","sleeve","hood","collar")
environment_terms = ("lightning","bolt","storm","fog","cloud","volume","car","audi","parking","storefront","asphalt","lamp","light")

def object_category(obj):
    blob = " ".join([
        obj.name,
        getattr(obj.data, "name", ""),
        " ".join(c.name for c in obj.users_collection),
    ]).lower()
    if any(term in blob for term in character_terms):
        return "CHARACTER"
    if any(term in blob for term in clothing_terms):
        return "CLOTHING"
    if any(term in blob for term in environment_terms):
        return "ENVIRONMENT_EFFECT"
    return "OTHER"

for c in bpy.data.collections:
    collections.append({
        "name": c.name,
        "object_count": len(c.objects),
        "child_collection_count": len(c.children),
        "hide_viewport": getattr(c, "hide_viewport", False),
        "hide_render": getattr(c, "hide_render", False),
        "users": c.users,
    })

for action in bpy.data.actions:
    try:
        fcurve_count = len(action.fcurves)
    except Exception:
        fcurve_count = 0
    actions.append({
        "name": action.name,
        "users": action.users,
        "fcurve_count": fcurve_count,
        "frame_range_start": action.frame_range[0],
        "frame_range_end": action.frame_range[1],
    })

for mat in bpy.data.materials:
    nt = mat.node_tree if mat.use_nodes else None
    materials.append({
        "name": mat.name,
        "users": mat.users,
        "use_nodes": mat.use_nodes,
        "node_count": len(nt.nodes) if nt else 0,
        "diffuse_color": safe(mat.diffuse_color),
        "surface_render_method": getattr(mat, "surface_render_method", ""),
        "blend_method": getattr(mat, "blend_method", ""),
        "has_emission_node": any("Emission" in n.bl_idname for n in nt.nodes) if nt else False,
        "has_volume_node": any("Volume" in n.bl_idname for n in nt.nodes) if nt else False,
    })

for obj in bpy.data.objects:
    category = object_category(obj)
    collection_names = [c.name for c in obj.users_collection]
    material_names = []
    if getattr(obj, "data", None) is not None and hasattr(obj.data, "materials"):
        material_names = [m.name for m in obj.data.materials if m]

    action_name = ""
    driver_count = 0
    nla_track_count = 0
    if obj.animation_data:
        if obj.animation_data.action:
            action_name = obj.animation_data.action.name
        driver_count = len(obj.animation_data.drivers)
        nla_track_count = len(obj.animation_data.nla_tracks)

    objects.append({
        "name": obj.name,
        "type": obj.type,
        "category": category,
        "data_name": getattr(obj.data, "name", ""),
        "collections": " | ".join(collection_names),
        "parent": obj.parent.name if obj.parent else "",
        "parent_type": obj.parent_type,
        "hide_viewport": obj.hide_viewport,
        "hide_render": obj.hide_render,
        "visible_get": obj.visible_get(),
        "location": safe(obj.location),
        "rotation_euler": safe(obj.rotation_euler),
        "scale": safe(obj.scale),
        "modifier_count": len(obj.modifiers),
        "constraint_count": len(obj.constraints),
        "vertex_group_count": len(obj.vertex_groups),
        "material_slots": " | ".join(material_names),
        "action": action_name,
        "driver_count": driver_count,
        "nla_track_count": nla_track_count,
    })

    for mod in obj.modifiers:
        modifiers.append({
            "object": obj.name,
            "category": category,
            "modifier": mod.name,
            "type": mod.type,
            "show_viewport": mod.show_viewport,
            "show_render": mod.show_render,
            "target_object": getattr(getattr(mod, "object", None), "name", ""),
            "vertex_group": getattr(mod, "vertex_group", ""),
            "use_deform_preserve_volume": getattr(mod, "use_deform_preserve_volume", ""),
        })

    for con in obj.constraints:
        constraints.append({
            "object": obj.name,
            "category": category,
            "constraint": con.name,
            "type": con.type,
            "target": getattr(getattr(con, "target", None), "name", ""),
            "subtarget": getattr(con, "subtarget", ""),
            "influence": getattr(con, "influence", ""),
            "mute": getattr(con, "mute", False),
        })

    for vg in obj.vertex_groups:
        vertex_groups.append({
            "object": obj.name,
            "category": category,
            "group": vg.name,
            "index": vg.index,
            "lock_weight": vg.lock_weight,
        })

    if obj.type == "MESH":
        mesh = obj.data
        sk_count = 0
        active_sk = ""
        sk_names = []
        if mesh.shape_keys:
            for kb in mesh.shape_keys.key_blocks:
                sk_count += 1
                sk_names.append(kb.name)
                shape_keys.append({
                    "object": obj.name,
                    "category": category,
                    "shape_key": kb.name,
                    "value": kb.value,
                    "slider_min": kb.slider_min,
                    "slider_max": kb.slider_max,
                    "mute": kb.mute,
                    "relative_key": kb.relative_key.name if kb.relative_key else "",
                })
            if obj.active_shape_key:
                active_sk = obj.active_shape_key.name

        edge_use = {}
        for poly in mesh.polygons:
            verts = list(poly.vertices)
            for i in range(len(verts)):
                key = tuple(sorted((verts[i], verts[(i+1) % len(verts)])))
                edge_use[key] = edge_use.get(key, 0) + 1
        boundary_edges = 0
        nonmanifold_edges = 0
        for edge in mesh.edges:
            key = tuple(sorted(edge.vertices[:]))
            count = edge_use.get(key, 0)
            if count == 1:
                boundary_edges += 1
            if count != 2:
                nonmanifold_edges += 1

        meshes.append({
            "object": obj.name,
            "category": category,
            "mesh": mesh.name,
            "data_users": mesh.users,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "boundary_edges": boundary_edges,
            "nonmanifold_edges": nonmanifold_edges,
            "shape_key_count": sk_count,
            "active_shape_key": active_sk,
            "shape_keys": " | ".join(sk_names),
            "vertex_group_count": len(obj.vertex_groups),
            "armature_modifier_count": sum(1 for m in obj.modifiers if m.type == "ARMATURE"),
            "parent": obj.parent.name if obj.parent else "",
            "materials": " | ".join(material_names),
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render,
        })

        if category in {"CHARACTER", "CLOTHING"}:
            rigging_candidates.append({
                "object": obj.name,
                "category": category,
                "mesh": mesh.name,
                "vertices": len(mesh.vertices),
                "polygons": len(mesh.polygons),
                "boundary_edges": boundary_edges,
                "nonmanifold_edges": nonmanifold_edges,
                "vertex_groups": len(obj.vertex_groups),
                "shape_keys": sk_count,
                "armature_modifiers": sum(1 for m in obj.modifiers if m.type == "ARMATURE"),
                "parent": obj.parent.name if obj.parent else "",
                "data_users": mesh.users,
                "visible": obj.visible_get() and not obj.hide_render,
                "likely_rig_ready": bool(obj.visible_get() and not obj.hide_render and len(mesh.vertices) > 0),
            })

    elif obj.type == "ARMATURE":
        armatures.append({
            "object": obj.name,
            "data_name": obj.data.name,
            "bone_count": len(obj.data.bones),
            "pose_bone_count": len(obj.pose.bones) if obj.pose else 0,
            "display_type": obj.display_type,
            "show_in_front": obj.show_in_front,
            "parent": obj.parent.name if obj.parent else "",
            "action": action_name,
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render,
        })

    elif obj.type == "CAMERA":
        cameras.append({
            "name": obj.name,
            "data_name": obj.data.name,
            "lens": obj.data.lens,
            "clip_start": obj.data.clip_start,
            "clip_end": obj.data.clip_end,
            "location": safe(obj.location),
            "rotation_euler": safe(obj.rotation_euler),
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render,
            "collections": " | ".join(collection_names),
        })

    elif obj.type == "LIGHT":
        lights.append({
            "name": obj.name,
            "type": obj.data.type,
            "energy": obj.data.energy,
            "color": safe(obj.data.color),
            "location": safe(obj.location),
            "rotation_euler": safe(obj.rotation_euler),
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render,
            "collections": " | ".join(collection_names),
        })

for image in bpy.data.images:
    raw = image.filepath
    abs_path = bpy.path.abspath(raw) if raw else ""
    external_files.append({
        "kind": "IMAGE",
        "name": image.name,
        "filepath": raw,
        "absolute_path": abs_path,
        "exists": os.path.exists(abs_path) if abs_path else False,
        "packed": bool(image.packed_file),
        "source": image.source,
    })

for sound in bpy.data.sounds:
    raw = sound.filepath
    abs_path = bpy.path.abspath(raw) if raw else ""
    external_files.append({
        "kind": "SOUND",
        "name": sound.name,
        "filepath": raw,
        "absolute_path": abs_path,
        "exists": os.path.exists(abs_path) if abs_path else False,
        "packed": bool(sound.packed_file),
        "source": "",
    })

missing_external = [
    row for row in external_files
    if row["absolute_path"] and not row["packed"] and not row["exists"]
]

character_candidates = [r for r in rigging_candidates if r["category"] == "CHARACTER"]
clothing_candidates = [r for r in rigging_candidates if r["category"] == "CLOTHING"]
rig_ready = [r for r in rigging_candidates if r["likely_rig_ready"]]

world_snapshot = {}
if scene.world:
    nt = scene.world.node_tree if scene.world.use_nodes else None
    world_snapshot = {
        "name": scene.world.name,
        "use_nodes": scene.world.use_nodes,
        "color": safe(scene.world.color),
        "nodes": [{"name": n.name, "type": n.bl_idname, "mute": n.mute} for n in nt.nodes] if nt else [],
    }

compositor_nodes = []
compositor_tree = None

# Blender 5.x may expose compositor nodes through a compositor node group
# instead of Scene.node_tree. Probe both APIs without changing the scene.
try:
    compositor_tree = getattr(scene, "node_tree", None)
except Exception:
    compositor_tree = None

if compositor_tree is None:
    try:
        compositor_tree = getattr(scene, "compositing_node_group", None)
    except Exception:
        compositor_tree = None

if compositor_tree is not None:
    try:
        compositor_nodes = [
            {
                "name": n.name,
                "type": n.bl_idname,
                "mute": getattr(n, "mute", False),
            }
            for n in compositor_tree.nodes
        ]
    except Exception:
        compositor_nodes = []

summary = {
    "object_count": len(objects),
    "mesh_count": len(meshes),
    "armature_count": len(armatures),
    "camera_count": len(cameras),
    "light_count": len(lights),
    "material_count": len(materials),
    "collection_count": len(collections),
    "action_count": len(actions),
    "modifier_count": len(modifiers),
    "constraint_count": len(constraints),
    "vertex_group_count": len(vertex_groups),
    "shape_key_count": len(shape_keys),
    "armature_modifier_count": sum(1 for m in modifiers if m["type"] == "ARMATURE"),
    "character_candidate_count": len(character_candidates),
    "clothing_candidate_count": len(clothing_candidates),
    "rig_ready_candidate_count": len(rig_ready),
    "external_file_count": len(external_files),
    "missing_external_file_count": len(missing_external),
}

scene_snapshot = {
    "scene_name": scene.name,
    "active_camera": scene.camera.name if scene.camera else None,
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "frame_current": scene.frame_current,
    "fps": scene.render.fps,
    "fps_base": scene.render.fps_base,
    "render_engine": scene.render.engine,
    "resolution_x": scene.render.resolution_x,
    "resolution_y": scene.render.resolution_y,
    "resolution_percentage": scene.render.resolution_percentage,
    "use_multiview": scene.render.use_multiview,
    "views_format": scene.render.views_format,
    "unit_system": scene.unit_settings.system,
    "unit_scale_length": scene.unit_settings.scale_length,
    "world": world_snapshot,
    "compositor_use_nodes": bool(compositor_tree is not None),
    "compositor_nodes": compositor_nodes,
    "color_management": {
        "display_device": scene.display_settings.display_device,
        "view_transform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "exposure": scene.view_settings.exposure,
        "gamma": scene.view_settings.gamma,
    },
}

status = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "blend_file": bpy.data.filepath,
    "saved_blend": False,
    "created_backup_blend_files": 0,
    "summary": summary,
    "scene_snapshot": scene_snapshot,
    "rigging_candidates": rigging_candidates,
    "armatures": armatures,
    "meshes": meshes,
    "objects": objects,
    "modifiers": modifiers,
    "constraints": constraints,
    "shape_keys": shape_keys,
    "materials": materials,
    "collections": collections,
    "actions": actions,
    "cameras": cameras,
    "lights": lights,
    "external_files": external_files,
    "missing_external_files": missing_external,
}

with open(os.path.join(OUT, "RiggingReadinessAuditV1_status.json"), "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)

with open(os.path.join(OUT, "RiggingReadinessAuditV1_report.txt"), "w", encoding="utf-8") as f:
    f.write("RIGGING READINESS AUDIT V1\n")
    f.write(f"blend_file={bpy.data.filepath}\n")
    for key, value in summary.items():
        f.write(f"{key}={value}\n")
    f.write(f"render_engine={scene.render.engine}\n")
    f.write(f"active_camera={scene_snapshot['active_camera']}\n")
    f.write(f"frame_range={scene.frame_start}-{scene.frame_end}\n")
    f.write(f"fps={scene.render.fps}/{scene.render.fps_base}\n")
    f.write("\nRIGGING CANDIDATES\n")
    for row in rigging_candidates:
        f.write(
            f"{row['category']} | {row['object']} | verts={row['vertices']} | "
            f"polys={row['polygons']} | boundary={row['boundary_edges']} | "
            f"nonmanifold={row['nonmanifold_edges']} | vgroups={row['vertex_groups']} | "
            f"shape_keys={row['shape_keys']} | armature_modifiers={row['armature_modifiers']} | "
            f"visible={row['visible']}\n"
        )

with open(os.path.join(OUT, "Rigging_Readiness_Audit_V1.md"), "w", encoding="utf-8") as f:
    f.write("# Rigging Readiness Audit v1\n\n")
    f.write(f"- Blend: `{bpy.data.filepath}`\n")
    f.write(f"- Objects: **{summary['object_count']}**\n")
    f.write(f"- Meshes: **{summary['mesh_count']}**\n")
    f.write(f"- Existing armatures: **{summary['armature_count']}**\n")
    f.write(f"- Character candidates: **{summary['character_candidate_count']}**\n")
    f.write(f"- Clothing candidates: **{summary['clothing_candidate_count']}**\n")
    f.write(f"- Rig-ready candidates: **{summary['rig_ready_candidate_count']}**\n")
    f.write(f"- Existing armature modifiers: **{summary['armature_modifier_count']}**\n")
    f.write(f"- Shape keys: **{summary['shape_key_count']}**\n")
    f.write(f"- Missing external files: **{summary['missing_external_file_count']}**\n\n")
    f.write("## Rigging candidates\n\n")
    for row in rigging_candidates:
        f.write(
            f"- **{row['object']}** — {row['category']}; "
            f"{row['vertices']} verts, {row['polygons']} faces, "
            f"{row['boundary_edges']} boundary edges, "
            f"{row['vertex_groups']} vertex groups, "
            f"{row['shape_keys']} shape keys, "
            f"{row['armature_modifiers']} armature modifiers.\n"
        )
    f.write("\nThis audit did not save or modify the blend.\n")

write_csv("objects.csv", objects, ["name"])
write_csv("meshes.csv", meshes, ["object"])
write_csv("rigging_candidates.csv", rigging_candidates, ["object"])
write_csv("armatures.csv", armatures, ["object"])
write_csv("modifiers.csv", modifiers, ["object"])
write_csv("constraints.csv", constraints, ["object"])
write_csv("vertex_groups.csv", vertex_groups, ["object"])
write_csv("shape_keys.csv", shape_keys, ["object"])
write_csv("materials.csv", materials, ["name"])
write_csv("collections.csv", collections, ["name"])
write_csv("actions.csv", actions, ["name"])
write_csv("cameras.csv", cameras, ["name"])
write_csv("lights.csv", lights, ["name"])
write_csv("external_files.csv", external_files, ["kind"])

print("[audit] rigging readiness complete")
print(f"[counts] objects={summary['object_count']} meshes={summary['mesh_count']} armatures={summary['armature_count']} cameras={summary['camera_count']} lights={summary['light_count']}")
print(f"[rigging] character_candidates={summary['character_candidate_count']} clothing_candidates={summary['clothing_candidate_count']} rig_ready={summary['rig_ready_candidate_count']}")
print(f"[animation] actions={summary['action_count']} armature_modifiers={summary['armature_modifier_count']} constraints={summary['constraint_count']} shape_keys={summary['shape_key_count']}")
print(f"[external] files={summary['external_file_count']} missing={summary['missing_external_file_count']}")
print("[safety] saved_blend=False created_backup_blend_files=0")
