import json, math, traceback
from pathlib import Path
import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "renders" / "mesh_audit_optimization_preview_v1"
REPORT_DIR = PROJECT_ROOT / "reports" / "mesh_audit_optimization_preview"
CURRENT_REVIEW = PROJECT_ROOT / "renders" / "current_review"
AUDIT_DIR = PROJECT_ROOT / "reports" / "project_workflow_audit"


def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "MeshAuditOptimizationPreview_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "MeshAuditOptimizationPreview_report.txt").write_text("", encoding="utf-8")


def visible(obj):
    try:
        return (not obj.hide_viewport) and (not obj.hide_render)
    except Exception:
        return True


def move_to_collection(obj, target_col):
    for col in list(obj.users_collection):
        if col != target_col:
            try:
                col.objects.unlink(obj)
            except Exception:
                pass
    if obj.name not in target_col.objects:
        try:
            target_col.objects.link(obj)
        except Exception:
            pass


def world_bounds(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [c.x for c in coords]
        ys = [c.y for c in coords]
        zs = [c.z for c in coords]
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


def center_from_bounds(bounds):
    return Vector(((bounds["min_x"] + bounds["max_x"]) * 0.5,
                   (bounds["min_y"] + bounds["max_y"]) * 0.5,
                   (bounds["min_z"] + bounds["max_z"]) * 0.5))


def union_bounds(objs):
    boxes = [world_bounds(o) for o in objs if world_bounds(o)]
    if not boxes:
        return None
    return {
        "min_x": min(b["min_x"] for b in boxes), "max_x": max(b["max_x"] for b in boxes),
        "min_y": min(b["min_y"] for b in boxes), "max_y": max(b["max_y"] for b in boxes),
        "min_z": min(b["min_z"] for b in boxes), "max_z": max(b["max_z"] for b in boxes),
        "dim_x": max(b["max_x"] for b in boxes) - min(b["min_x"] for b in boxes),
        "dim_y": max(b["max_y"] for b in boxes) - min(b["min_y"] for b in boxes),
        "dim_z": max(b["max_z"] for b in boxes) - min(b["min_z"] for b in boxes),
    }


def get_f2():
    obj = bpy.data.objects.get("F2")
    if obj and obj.type == 'MESH':
        return obj
    candidates = [o for o in bpy.data.objects if o.type == 'MESH' and visible(o)]
    if not candidates:
        raise RuntimeError("No visible mesh object found for hero character baseline.")
    candidates.sort(key=lambda o: (world_bounds(o) or {}).get("dim_z", 0), reverse=True)
    return candidates[0]


def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = False
    col.hide_render = False
    return col


def replace_collection(name):
    old = bpy.data.collections.get(name)
    if old:
        for child in list(old.children):
            pass
        for obj in list(old.objects):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass
        try:
            bpy.data.collections.remove(old)
        except Exception:
            pass
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def mesh_counts(obj):
    if obj.type != 'MESH' or obj.data is None:
        return {"vertices": 0, "edges": 0, "faces": 0}
    me = obj.data
    return {"vertices": len(me.vertices), "edges": len(me.edges), "faces": len(me.polygons)}


def recommend_ratio(face_count):
    if face_count >= 150000:
        return 0.20
    if face_count >= 80000:
        return 0.35
    if face_count >= 40000:
        return 0.50
    if face_count >= 20000:
        return 0.70
    if face_count >= 10000:
        return 0.85
    return 1.0


def likely_asset_objects():
    results = []
    imported_col = bpy.data.collections.get("HERO_IMPORTED_CLOTHING_CANDIDATES")
    seen = set()
    if imported_col:
        for obj in imported_col.all_objects:
            if obj.type == 'MESH' and obj.name not in seen:
                seen.add(obj.name)
                results.append(obj)
    keywords = ["hood", "jean", "pant", "shoe", "sneaker", "sign", "cone", "trash", "utility", "box", "asphalt", "sewer", "hatch", "cloth"]
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.name in seen:
            continue
        name = obj.name.lower()
        colnames = " ".join(c.name.lower() for c in obj.users_collection)
        if any(k in name or k in colnames for k in keywords):
            seen.add(obj.name)
            results.append(obj)
    return results


def classify_object(obj):
    name = obj.name.lower()
    cols = [c.name.lower() for c in obj.users_collection]
    all_txt = " ".join([name] + cols)
    if any(k in all_txt for k in ["hood", "jean", "pant", "shoe", "sneaker", "cloth", "wardrobe"]):
        return "clothing"
    if any(k in all_txt for k in ["asphalt", "parking", "curb", "sidewalk", "store", "storefront"]):
        return "environment"
    return "prop"


def audit_meshes():
    assets = likely_asset_objects()
    rows = []
    for obj in assets:
        counts = mesh_counts(obj)
        bounds = world_bounds(obj)
        rows.append({
            "name": obj.name,
            "category": classify_object(obj),
            "collections": [c.name for c in obj.users_collection],
            "visible": visible(obj),
            "location": [round(obj.location.x, 5), round(obj.location.y, 5), round(obj.location.z, 5)],
            "dimensions": None if not bounds else [round(bounds['dim_x'], 5), round(bounds['dim_y'], 5), round(bounds['dim_z'], 5)],
            "vertices": counts['vertices'],
            "edges": counts['edges'],
            "faces": counts['faces'],
            "recommended_decimate_ratio": recommend_ratio(counts['faces']),
            "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        })
    rows.sort(key=lambda r: r['faces'], reverse=True)
    return rows


def choose_asphalt():
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    candidates = []
    for obj in meshes:
        name = obj.name.lower()
        cols = " ".join(c.name.lower() for c in obj.users_collection)
        if any(k in name or k in cols for k in ["asphalt", "parking", "lot"]):
            b = world_bounds(obj)
            if b:
                area = b['dim_x'] * b['dim_y']
                candidates.append((area, obj))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


def choose_parking_strips(asphalt_obj=None):
    results = []
    seen = set()
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        if asphalt_obj and obj.name == asphalt_obj.name:
            continue
        name = obj.name.lower()
        cols = " ".join(c.name.lower() for c in obj.users_collection)
        if any(k in name or k in cols for k in ["parking", "stripe", "paint", "stall", "line"]):
            if any(bad in name for bad in ["lamp", "sign", "sidewalk", "curb", "store"]):
                continue
            if obj.name not in seen:
                seen.add(obj.name)
                results.append(obj)
    return results


def preview_snap_parking_strips():
    asphalt = choose_asphalt()
    strip_objs = choose_parking_strips(asphalt)
    applied = []
    if not asphalt:
        log("[parking] no asphalt target found; skipping parking paint snap preview")
        return {"asphalt": None, "strip_count": 0, "objects": []}
    for obj in strip_objs:
        mod = obj.modifiers.get("PARKING_TO_ASPHALT_PREVIEW")
        if not mod:
            mod = obj.modifiers.new("PARKING_TO_ASPHALT_PREVIEW", 'SHRINKWRAP')
        mod.target = asphalt
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        mod.wrap_mode = 'OUTSIDE'
        mod.offset = 0.0025
        mod.show_viewport = True
        mod.show_render = True
        applied.append(obj.name)
    log(f"[parking] added/updated preview snap modifier on {len(applied)} parking paint object(s) targeting {asphalt.name}")
    return {"asphalt": asphalt.name, "strip_count": len(applied), "objects": applied}


def write_reports(audit_rows, parking_info):
    payload = {
        "hero_object": get_f2().name,
        "asset_count": len(audit_rows),
        "high_poly_candidates": [r for r in audit_rows if r['faces'] >= 20000],
        "all_assets": audit_rows,
        "parking_snap_preview": parking_info,
        "notes": [
            "This is a preview/audit pass only. No decimation modifiers were applied.",
            "Parking paint strip snap was added as a non-destructive preview modifier.",
            "Use the recommended_decimate_ratio values as starting points for the later optimization pass."
        ]
    }
    (REPORT_DIR / "mesh_audit_optimization_preview.json").write_text(json.dumps(payload, indent=2), encoding='utf-8')

    md = []
    md.append("# Mesh Audit / Optimization Preview v1")
    md.append("")
    md.append("This pass preserves the current scene baseline, audits imported clothing/props, and adds a non-destructive parking-paint snap preview.")
    md.append("")
    md.append("## High-Poly Candidates")
    high = [r for r in audit_rows if r['faces'] >= 20000]
    if not high:
        md.append("- No objects exceeded the 20k-face preview threshold.")
    else:
        for r in high:
            md.append(f"- **{r['name']}** | category={r['category']} | faces={r['faces']} | verts={r['vertices']} | suggested decimate ratio={r['recommended_decimate_ratio']}")
    md.append("")
    md.append("## All Audited Assets")
    for r in audit_rows:
        md.append(f"- **{r['name']}** | {r['category']} | faces={r['faces']} | verts={r['vertices']} | dims={r['dimensions']} | collections={r['collections']}")
    md.append("")
    md.append("## Parking Paint Snap Preview")
    if parking_info['asphalt']:
        md.append(f"- Asphalt target: **{parking_info['asphalt']}**")
        md.append(f"- Parking paint objects updated: **{parking_info['strip_count']}**")
    else:
        md.append("- No asphalt target was found, so no snap preview was added.")
    md.append("")
    md.append("## Optimization Guidance")
    md.append("- Clothes and deforming meshes should be reduced carefully; use milder ratios first.")
    md.append("- Static props like signs, cones, hatch covers, and utility boxes are safer decimation candidates.")
    md.append("- Review the before/after shape once we do the later automatic decimation pass.")
    (REPORT_DIR / "Mesh_Audit_Optimization_Preview.md").write_text("\n".join(md), encoding='utf-8')

    status = {
        "lights": "LOCKED - untouched",
        "car": "LOCKED - untouched",
        "storefront": "LOCKED - untouched",
        "world_hdri": "LOCKED - untouched",
        "mesh_audit_asset_count": len(audit_rows),
        "high_poly_candidate_count": len(high),
        "parking_snap_preview": parking_info,
        "automatic_decimation": False,
    }
    (OUT_DIR / "MeshAuditOptimizationPreview_status.json").write_text(json.dumps(status, indent=2), encoding='utf-8')


def write_scene_manifest(audit_rows):
    manifest = {
        "blend_file": bpy.data.filepath,
        "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
        "render_engine": bpy.context.scene.render.engine,
        "world": bpy.context.scene.world.name if bpy.context.scene.world else None,
        "collections": [],
        "objects": []
    }
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        manifest['collections'].append({
            "name": col.name,
            "hide_viewport": bool(col.hide_viewport),
            "hide_render": bool(col.hide_render),
            "object_count": len(col.objects),
            "child_count": len(col.children),
        })
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        bounds = world_bounds(obj)
        entry = {
            "name": obj.name,
            "type": obj.type,
            "visible": visible(obj),
            "collections": [c.name for c in obj.users_collection],
            "location": [round(obj.location.x, 5), round(obj.location.y, 5), round(obj.location.z, 5)],
            "rotation": [round(v, 5) for v in obj.rotation_euler],
            "scale": [round(obj.scale.x, 5), round(obj.scale.y, 5), round(obj.scale.z, 5)],
            "parent": obj.parent.name if obj.parent else None,
            "dimensions": None if not bounds else [round(bounds['dim_x'], 5), round(bounds['dim_y'], 5), round(bounds['dim_z'], 5)],
            "modifiers": [m.name for m in obj.modifiers],
            "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        }
        if obj.type == 'LIGHT':
            entry['light_type'] = obj.data.type
            entry['energy'] = getattr(obj.data, 'energy', None)
            entry['color'] = list(getattr(obj.data, 'color', [])) if hasattr(obj.data, 'color') else None
        if obj.type == 'CAMERA':
            entry['lens'] = getattr(obj.data, 'lens', None)
        manifest['objects'].append(entry)
    (PROJECT_ROOT / "scene_manifest.json").write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (AUDIT_DIR / "scene_manifest.json").write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    layout = [
        "# Scene Layout Summary",
        "",
        f"- Blend file: `{bpy.data.filepath}`",
        f"- World: `{manifest['world']}`",
        f"- Render engine: `{manifest['render_engine']}`",
        f"- Collections: **{len(manifest['collections'])}**",
        f"- Objects: **{len(manifest['objects'])}**",
        f"- Audited imported/prop assets: **{len(audit_rows)}**",
        "",
        "## Notes",
        "- This summary was updated by Mesh Audit / Optimization Preview v1.",
        "- Manual scene edits are preserved; only parking paint received non-destructive shrinkwrap preview modifiers.",
    ]
    (AUDIT_DIR / "scene_layout_summary.md").write_text("\n".join(layout), encoding='utf-8')

    file_layout = {
        "generated_by": "mesh_audit_optimization_preview_v1",
        "project_root": str(PROJECT_ROOT),
        "key_outputs": {
            "renders": str(OUT_DIR),
            "current_review": str(CURRENT_REVIEW),
            "mesh_report": str(REPORT_DIR / 'Mesh_Audit_Optimization_Preview.md'),
            "mesh_json": str(REPORT_DIR / 'mesh_audit_optimization_preview.json'),
            "scene_manifest": str(PROJECT_ROOT / 'scene_manifest.json')
        }
    }
    (AUDIT_DIR / "project_file_layout.json").write_text(json.dumps(file_layout, indent=2), encoding='utf-8')


def look_at(cam, target):
    direction = target - cam.location
    rot = direction.to_track_quat('-Z', 'Y').to_euler()
    cam.rotation_euler = rot


def create_temp_cameras(hero_bounds, audited_objs, parking_info):
    col = replace_collection("HERO_REVIEW_CAMERAS_MESH_AUDIT")
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    center = center_from_bounds(hero_bounds)
    hx, hy, hz = hero_bounds['dim_x'], hero_bounds['dim_y'], hero_bounds['dim_z']

    asset_objs = []
    imported_col = bpy.data.collections.get("HERO_IMPORTED_CLOTHING_CANDIDATES")
    if imported_col:
        asset_objs = [o for o in imported_col.all_objects if o.type == 'MESH' and visible(o)]
    asset_bounds = union_bounds(asset_objs) if asset_objs else hero_bounds
    asset_center = center_from_bounds(asset_bounds)

    asphalt = bpy.data.objects.get(parking_info['asphalt']) if parking_info.get('asphalt') else None
    asphalt_bounds = world_bounds(asphalt) if asphalt else hero_bounds
    park_center = center_from_bounds(asphalt_bounds)

    specs = [
        ("HERO_CAM_MeshAuditOverview", Vector((center.x + hx*1.8, center.y - hy*3.4, center.z + hz*0.55)), Vector((center.x, center.y, center.z + hz*0.18)), 52, "01_MeshAuditOverview.png"),
        ("HERO_CAM_ImportedAssetsAudit", Vector((asset_center.x + max(hx, asset_bounds['dim_x'])*1.4, asset_center.y - max(hy, asset_bounds['dim_y'])*2.2, asset_center.z + max(hz, asset_bounds['dim_z'])*0.65)), Vector((asset_center.x, asset_center.y, asset_center.z + asset_bounds['dim_z']*0.2)), 50, "02_ImportedAssetsAudit.png"),
        ("HERO_CAM_ParkingPaintSnap", Vector((park_center.x + asphalt_bounds['dim_x']*0.12, park_center.y - asphalt_bounds['dim_y']*0.28, asphalt_bounds['min_z'] + max(1.2, hz*0.45))), Vector((park_center.x, park_center.y, asphalt_bounds['min_z'] + 0.05)), 42, "03_ParkingPaintSnap.png"),
    ]

    for name, loc, aim, lens, filename in specs:
        data = bpy.data.cameras.new(name + "_Data")
        cam = bpy.data.objects.new(name, data)
        cam.location = loc
        cam.data.lens = lens
        look_at(cam, aim)
        col.objects.link(cam)
        scene.camera = cam
        scene.render.filepath = str(OUT_DIR / filename)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {filename}")

    # clean and refresh current_review
    CURRENT_REVIEW.mkdir(parents=True, exist_ok=True)
    for p in CURRENT_REVIEW.glob('*'):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob('*'):
        if p.is_file():
            (CURRENT_REVIEW / p.name).write_bytes(p.read_bytes())


def preserve_notice():
    log("[lock] current scene baseline preserved; no light/car/storefront/world edits will be made")


def main():
    reset_log()
    preserve_notice()
    hero = get_f2()
    hero_bounds = world_bounds(hero)
    audit_rows = audit_meshes()
    parking_info = preview_snap_parking_strips()
    write_reports(audit_rows, parking_info)
    write_scene_manifest(audit_rows)
    create_temp_cameras(hero_bounds, audit_rows, parking_info)
    out = PROJECT_ROOT / 'blender' / 'sackboy_scene.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUT_DIR / 'MeshAuditOptimizationPreview_FATAL_ERROR.txt').open('w', encoding='utf-8') as f:
            traceback.print_exc(file=f)
        raise
