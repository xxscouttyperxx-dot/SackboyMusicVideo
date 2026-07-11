import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "renders" / "decimate_preview_paint_snap_v1B"
REPORT_DIR = PROJECT_ROOT / "reports" / "decimate_preview_paint_snap_v1B"
CURRENT_REVIEW = PROJECT_ROOT / "renders" / "current_review"
AUDIT_DIR = PROJECT_ROOT / "reports" / "project_workflow_audit"

DECIMATE_TARGETS = {
    "Apricot Pullover Hoodie": 0.25,
    "Utility Box (Photoscanned)": 0.70,
    "Lid.001": 0.70,
}

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "DecimatePreviewPaintSnap_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "DecimatePreviewPaintSnap_report.txt").write_text("", encoding="utf-8")

def visible(obj):
    return (not obj.hide_viewport) and (not obj.hide_render)

def bounds(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [c.x for c in coords]; ys = [c.y for c in coords]; zs = [c.z for c in coords]
        return {
            "min_x": min(xs), "max_x": max(xs),
            "min_y": min(ys), "max_y": max(ys),
            "min_z": min(zs), "max_z": max(zs),
            "dim_x": max(xs) - min(xs),
            "dim_y": max(ys) - min(ys),
            "dim_z": max(zs) - min(zs),
        }
    except Exception:
        return None

def center(b):
    return Vector(((b["min_x"] + b["max_x"]) * 0.5, (b["min_y"] + b["max_y"]) * 0.5, (b["min_z"] + b["max_z"]) * 0.5))

def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = False
    col.hide_render = False
    return col

def unlink_from_collections(obj):
    for col in list(obj.users_collection):
        try:
            col.objects.unlink(obj)
        except Exception:
            pass

def link_to_collection(obj, col):
    if obj.name not in col.objects:
        try:
            col.objects.link(obj)
        except Exception:
            pass

def mesh_counts(obj):
    if obj.type != "MESH":
        return {"vertices": 0, "faces": 0}
    return {"vertices": len(obj.data.vertices), "faces": len(obj.data.polygons)}

def setup_decimate_previews():
    backup_col = ensure_collection("OPTIMIZATION_PREVIEW_BACKUP_LINKED_ORIGINALS")
    backup_col.hide_viewport = True
    backup_col.hide_render = True
    preview_col = ensure_collection("OPTIMIZATION_PREVIEW_DECIMATE_TARGETS")

    results = []
    for name, ratio in DECIMATE_TARGETS.items():
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            results.append({"name": name, "status": "missing", "ratio": ratio})
            log(f"[decimate] target missing: {name}")
            continue

        before = mesh_counts(obj)

        backup_name = "OPT_BACKUP_ORIGINAL_" + name.replace(" ", "_").replace("(", "").replace(")", "")
        backup = bpy.data.objects.get(backup_name)
        if not backup:
            backup = bpy.data.objects.new(backup_name, obj.data)
            backup.matrix_world = obj.matrix_world.copy()
            backup.hide_viewport = True
            backup.hide_render = True
            link_to_collection(backup, backup_col)
        backup["optimization_backup_for"] = obj.name
        backup["backup_type"] = "linked original mesh data, hidden"

        # Keep object in its current collection too. Also link to preview collection for easy finding.
        link_to_collection(obj, preview_col)

        # Use a non-destructive modifier only.
        mod = obj.modifiers.get("OPT_PREVIEW_DECIMATE")
        if not mod:
            mod = obj.modifiers.new("OPT_PREVIEW_DECIMATE", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.show_viewport = True
        mod.show_render = True

        obj["optimization_preview_ratio"] = ratio
        obj["optimization_preview_modifier"] = "OPT_PREVIEW_DECIMATE"
        obj["optimization_original_faces"] = before["faces"]
        obj["optimization_original_vertices"] = before["vertices"]

        est_faces = int(before["faces"] * ratio)
        results.append({
            "name": name,
            "status": "preview_modifier_added",
            "ratio": ratio,
            "original_vertices": before["vertices"],
            "original_faces": before["faces"],
            "estimated_preview_faces": est_faces,
            "backup_object": backup_name,
        })
        log(f"[decimate] {name}: faces {before['faces']} -> estimated {est_faces} using preview ratio {ratio}")

    return results

def asphalt_candidates():
    cands = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        text = (obj.name + " " + " ".join(c.name for c in obj.users_collection)).lower()
        if any(k in text for k in ["asphalt", "ground", "parkinglot", "parking lot"]):
            b = bounds(obj)
            if b:
                cands.append((obj, b))
    return cands

def parking_paint_objects():
    objs = []
    seen = set()
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        text = (obj.name + " " + " ".join(c.name for c in obj.users_collection)).lower()

        # Exclude ground/asphalt target meshes so a paint strip can never shrinkwrap to itself.
        if any(bad in text for bad in ["asphalt", "ground", "env_asphalt", "parkinglot", "parking lot"]):
            continue

        # Include only the intentionally thin parking-line objects.
        if any(k in text for k in ["hparking", "stripe", "strip", "paint", "line", "divider", "spine"]):
            if any(bad in text for bad in ["lamp", "sign", "sidewalk", "curb", "storefront", "camera", "collection"]):
                continue
            if obj.name not in seen:
                objs.append(obj)
                seen.add(obj.name)
    return objs

def pick_asphalt_for_paint(paint_objs):
    cands = asphalt_candidates()
    if not cands:
        return None, None
    # Prefer a flat intentional asphalt plane over imported scenic ground if it overlaps the paint.
    scored = []
    for obj, b in cands:
        contained = 0
        top_close_score = 0.0
        for p in paint_objs:
            pb = bounds(p)
            if not pb:
                continue
            pcx = (pb["min_x"] + pb["max_x"]) * 0.5
            pcy = (pb["min_y"] + pb["max_y"]) * 0.5
            if b["min_x"] - 0.1 <= pcx <= b["max_x"] + 0.1 and b["min_y"] - 0.1 <= pcy <= b["max_y"] + 0.1:
                contained += 1
                top_close_score += abs(pb["min_z"] - b["max_z"])
        name_bonus = 0
        lname = obj.name.lower()
        if lname == "env_asphalt":
            name_bonus = 100
        elif "asphalt ground" in lname:
            name_bonus = 40
        elif "asphalt" in lname:
            name_bonus = 20
        score = contained * 10 + name_bonus - top_close_score
        scored.append((score, obj, b, contained))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1], scored[0][2]

def improve_paint_snap():
    paints = parking_paint_objects()
    target, tb = pick_asphalt_for_paint(paints)
    results = []
    if not paints:
        log("[paint] no parking paint strip objects found")
        return {"target": None, "count": 0, "objects": [], "note": "no paint objects found"}
    if not target:
        log("[paint] no asphalt target found")
        return {"target": None, "count": 0, "objects": [], "note": "no asphalt target found"}

    offset = 0.006
    target_top = tb["max_z"]

    for obj in paints:
        pb = bounds(obj)
        if not pb:
            continue

        old_z = obj.location.z
        # First make the preview visually obvious by placing the mesh bottom slightly above target top.
        desired_bottom = target_top + offset
        dz = desired_bottom - pb["min_z"]
        if abs(dz) > 0.0005:
            obj.location.z += dz

        # Never assign a shrinkwrap target to itself.
        if obj.name == target.name:
            continue

        # Then keep a non-destructive shrinkwrap preview modifier on it so it stays associated with the asphalt target.
        mod = obj.modifiers.get("PARKING_TO_ASPHALT_PREVIEW")
        if not mod:
            mod = obj.modifiers.new("PARKING_TO_ASPHALT_PREVIEW", "SHRINKWRAP")
        mod.target = target
        try:
            mod.wrap_method = "PROJECT"
            if hasattr(mod, "use_project_z"):
                mod.use_project_z = True
            if hasattr(mod, "use_negative_direction"):
                mod.use_negative_direction = True
            if hasattr(mod, "use_positive_direction"):
                mod.use_positive_direction = False
        except Exception:
            try:
                mod.wrap_method = "NEAREST_SURFACEPOINT"
            except Exception:
                pass
        mod.offset = offset
        mod.show_viewport = True
        mod.show_render = True

        nb = bounds(obj)
        results.append({
            "name": obj.name,
            "old_location_z": round(old_z, 6),
            "new_location_z": round(obj.location.z, 6),
            "target_top_z": round(target_top, 6),
            "modifier": "PARKING_TO_ASPHALT_PREVIEW",
            "new_min_z": None if not nb else round(nb["min_z"], 6),
        })

    log(f"[paint] moved/snap-previewed {len(results)} parking paint object(s) to {target.name} top z {target_top:.6f}")
    return {"target": target.name, "target_top_z": target_top, "count": len(results), "objects": results}

def write_reports(decimate, paint):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "decimate_preview": decimate,
        "paint_snap_preview": paint,
        "locked": {
            "lights": "not edited",
            "car": "not edited",
            "storefront": "not edited",
            "sky_world_hdri": "not edited",
            "camera_layout": "no permanent camera-layout changes",
            "no_parking_sign": "not decimated",
            "traffic_cone_cargo_pants_shoes": "not decimated",
        }
    }
    (REPORT_DIR / "decimate_preview_paint_snap_v1B.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Decimate Preview / Paint Snap v1B", ""]
    lines.append("This pass adds non-destructive decimate preview modifiers to selected heavy meshes and improves parking paint snapping.")
    lines.append("")
    lines.append("## Decimate Preview Targets")
    for r in decimate:
        lines.append(f"- **{r['name']}** | status={r['status']} | ratio={r.get('ratio')} | original_faces={r.get('original_faces')} | estimated_preview_faces={r.get('estimated_preview_faces')} | backup={r.get('backup_object')}")
    lines.append("")
    lines.append("## Parking Paint Snap")
    lines.append(f"- Target asphalt: **{paint.get('target')}**")
    lines.append(f"- Paint objects adjusted: **{paint.get('count')}**")
    lines.append("- Paint objects were moved down/up to sit slightly above the asphalt top and kept linked with a non-destructive shrinkwrap preview modifier.")
    lines.append("")
    lines.append("## Locked Items")
    lines.append("- No lights, car, storefront, sky/world/HDRI, or camera layout changes were made.")
    lines.append("- No Parking Sign was not decimated in this pass.")
    lines.append("- Traffic cone, cargo pants, and shoes were not decimated in this pass.")
    (REPORT_DIR / "Decimate_Preview_Paint_Snap_v1.md").write_text("\n".join(lines), encoding="utf-8")

    (OUT_DIR / "DecimatePreviewPaintSnap_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def write_scene_manifest():
    data = {
        "blend_file": bpy.data.filepath,
        "collections": [],
        "objects": [],
    }
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({
            "name": col.name,
            "hide_viewport": bool(col.hide_viewport),
            "hide_render": bool(col.hide_render),
            "object_count": len(col.objects),
            "child_count": len(col.children),
        })
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        b = bounds(obj)
        entry = {
            "name": obj.name,
            "type": obj.type,
            "collections": [c.name for c in obj.users_collection],
            "visible": visible(obj),
            "location": [round(obj.location.x, 6), round(obj.location.y, 6), round(obj.location.z, 6)],
            "rotation": [round(v, 6) for v in obj.rotation_euler],
            "scale": [round(obj.scale.x, 6), round(obj.scale.y, 6), round(obj.scale.z, 6)],
            "dimensions": None if not b else [round(b["dim_x"], 6), round(b["dim_y"], 6), round(b["dim_z"], 6)],
            "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers],
        }
        if obj.type == "MESH":
            c = mesh_counts(obj)
            entry["vertices"] = c["vertices"]
            entry["faces"] = c["faces"]
        if obj.type == "LIGHT":
            entry["light_type"] = obj.data.type
            entry["energy"] = getattr(obj.data, "energy", None)
            entry["color"] = list(getattr(obj.data, "color", [])) if hasattr(obj.data, "color") else None
        data["objects"].append(entry)

    (PROJECT_ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUDIT_DIR / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\n"
        "Updated by Decimate Preview / Paint Snap v1B.\n\n"
        "- Heavy mesh decimation is preview-only through modifiers.\n"
        "- Parking paint snap was improved and remains preview/modifier based.\n"
        "- Locked lights, car, storefront, and world/HDRI were not edited.\n",
        encoding="utf-8"
    )
    (AUDIT_DIR / "project_file_layout.json").write_text(json.dumps({
        "generated_by": "decimate_preview_paint_snap_v1B",
        "reports": str(REPORT_DIR),
        "renders": str(OUT_DIR),
        "current_review": str(CURRENT_REVIEW)
    }, indent=2), encoding="utf-8")

def render_review():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    cams = [
        bpy.data.objects.get("HERO_CAM_MeshAuditOverview"),
        bpy.data.objects.get("HERO_CAM_ImportedAssetsAudit"),
        bpy.data.objects.get("HERO_CAM_ParkingPaintSnap"),
        bpy.data.objects.get("HERO_CAM_ImportedClothingCandidates"),
        bpy.data.objects.get("HERO_CAM_WardrobeCleanupFront"),
    ]
    cams = [c for c in cams if c and c.type == "CAMERA"]
    if not cams:
        cams = sorted([o for o in bpy.data.objects if o.type == "CAMERA"], key=lambda o: o.name)[:3]
    original_camera = scene.camera
    names = ["01_DecimatePreviewOverview.png", "02_SelectedMeshesPreview.png", "03_ParkingPaintSnapImproved.png"]
    for idx, cam in enumerate(cams[:3]):
        scene.camera = cam
        scene.render.filepath = str(OUT_DIR / names[idx])
        bpy.ops.render.render(write_still=True)
        log(f"[render] {names[idx]}")
    scene.camera = original_camera

    CURRENT_REVIEW.mkdir(parents=True, exist_ok=True)
    for p in CURRENT_REVIEW.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (CURRENT_REVIEW / p.name).write_bytes(p.read_bytes())

def main():
    reset_log()
    log("[lock] preserving lights, car, storefront, sky/world/HDRI, no-parking sign, traffic cone, cargo pants, and shoes")
    decimate = setup_decimate_previews()
    paint = improve_paint_snap()
    write_reports(decimate, paint)
    write_scene_manifest()
    render_review()
    out = PROJECT_ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUT_DIR / "DecimatePreviewPaintSnap_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
