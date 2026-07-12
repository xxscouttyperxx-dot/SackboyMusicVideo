import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "current_review"
REP = ROOT / "reports" / "restore_imported_hoodie_baseline_v1"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    REP.mkdir(parents=True, exist_ok=True)
    with (REP / "RestoreImportedHoodieBaseline_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_outputs():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()
    (REP / "RestoreImportedHoodieBaseline_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {
        "min_x": min(xs), "max_x": max(xs),
        "min_y": min(ys), "max_y": max(ys),
        "min_z": min(zs), "max_z": max(zs),
        "dim_x": max(xs)-min(xs),
        "dim_y": max(ys)-min(ys),
        "dim_z": max(zs)-min(zs),
    }

def center_from_bounds(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def find_hoodie():
    for name in HOODIE_NAMES:
        o = bpy.data.objects.get(name)
        if o and o.type == "MESH":
            if o.name != "SACKBOY_Hoodie_Main":
                old = o.name
                o.name = "SACKBOY_Hoodie_Main"
                o.data.name = "SACKBOY_Hoodie_Main_Mesh"
                log(f"[rename] hoodie renamed {old} -> {o.name}")
            return o
    matches = [o for o in bpy.data.objects if o.type == "MESH" and ("hoodie" in o.name.lower() or "pullover" in o.name.lower() or "apricot" in o.name.lower())]
    if not matches:
        raise RuntimeError("Could not find hoodie mesh.")
    o = sorted(matches, key=lambda x: (not visible(x), -len(x.data.vertices), x.name))[0]
    old = o.name
    o.name = "SACKBOY_Hoodie_Main"
    o.data.name = "SACKBOY_Hoodie_Main_Mesh"
    log(f"[rename] hoodie renamed {old} -> {o.name}")
    return o

def restore_underglow():
    o = bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log("[lock] underglow missing")
        return {"status": "missing"}
    before = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"before": before, "after": after}

def keep_character_baseline():
    hero = bpy.data.objects.get(HERO_NAME)
    disabled = []
    if hero and hero.type == "MESH" and hero.data.shape_keys:
        for kb in hero.data.shape_keys.key_blocks:
            if kb.name.startswith("BODYFIT_"):
                before = float(kb.value)
                kb.value = 0.0
                disabled.append({"name": kb.name, "before": before, "after": 0.0})
    log("[character] F2 baseline preserved; BODYFIT keys kept disabled")
    return disabled

def restore_hoodie_basis(hoodie):
    shape_key_rows = []
    restored = []
    active_before = None
    active_after = None

    if hoodie.data.shape_keys:
        if 0 <= hoodie.active_shape_key_index < len(hoodie.data.shape_keys.key_blocks):
            active_before = hoodie.data.shape_keys.key_blocks[hoodie.active_shape_key_index].name
        for kb in hoodie.data.shape_keys.key_blocks:
            before = float(kb.value)
            if kb.name != "Basis":
                kb.value = 0.0
                if before != 0.0 or kb.name.startswith("HOODIEFIT_"):
                    restored.append({"name": kb.name, "before": before, "after": 0.0})
            shape_key_rows.append({"name": kb.name, "before": before, "after": float(kb.value)})
        hoodie.active_shape_key_index = 0
        active_after = hoodie.data.shape_keys.key_blocks[0].name
    hoodie["hoodie_fit_pass"] = "RestoredImportedHoodieBaseline_v1"
    hoodie["hoodie_fit_shape_key"] = "Basis"
    log(f"[hoodie] restored imported baseline by setting non-Basis shape key values to 0; restored_keys={len(restored)}; active_before={active_before}; active_after={active_after}")
    return {
        "active_shape_key_before": active_before,
        "active_shape_key_after": active_after,
        "restored_keys": restored,
        "shape_keys": shape_key_rows,
        "vertex_count": len(hoodie.data.vertices),
        "face_count": len(hoodie.data.polygons),
    }

def camera_data(name):
    old = bpy.data.objects.get(name)
    if old and old.type == "CAMERA":
        return old
    data = bpy.data.cameras.new(name + "_Data")
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj

def look_at(obj, target):
    direction = target - obj.location
    if direction.length:
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def set_cam(name, loc, target, lens, hidden=False):
    cam = camera_data(name)
    cam.location = Vector(loc)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    cam.hide_viewport = hidden
    cam.hide_render = hidden
    return cam

def reset_cameras(hoodie):
    for cam in list(bpy.data.objects):
        if cam.type == "CAMERA":
            bpy.data.objects.remove(cam, do_unlink=True)

    hb = bounds_world(hoodie)
    hc = center_from_bounds(hb)
    hood_mid = Vector((hc.x, hc.y, hb["min_z"] + hb["dim_z"]*0.66))
    hero = bpy.data.objects.get(HERO_NAME)
    fb = bounds_world(hero) if hero else hb
    fc = center_from_bounds(fb)
    fmid = Vector((fc.x, fc.y, fb["min_z"] + fb["dim_z"]*0.52))

    set_cam("CAM_F2_Front", (fmid.x, fmid.y-6.0, fmid.z+0.65), fmid+Vector((0,0,0.10)), 55, False)
    set_cam("CAM_F2_Profile", (fmid.x+5.5, fmid.y-0.6, fmid.z+0.65), fmid+Vector((0,0,0.10)), 60, False)
    set_cam("CAM_F2_ThreeQuarter", (fmid.x+3.8, fmid.y-5.8, fmid.z+0.85), fmid+Vector((0,0,0.10)), 52, False)
    set_cam("CAM_StorefrontReflection", (hc.x+7.8, hc.y-10.0, hc.z+1.65), (hc.x, hc.y+4.2, hc.z+0.85), 48, False)
    set_cam("CAM_SceneWide", (hc.x+8.5, hc.y-10.5, hc.z+4.6), (hc.x, hc.y+1.0, hc.z+0.55), 35, False)

    set_cam("CAM_Hood_Front", (hood_mid.x+0.18, hood_mid.y-4.0, hood_mid.z+0.50), hood_mid+Vector((0,0,0.30)), 54, False)
    set_cam("CAM_Hood_LeftSide", (hood_mid.x-3.6, hood_mid.y, hood_mid.z+0.95), hood_mid+Vector((0,0,0.35)), 56, False)
    set_cam("CAM_Hood_RightSide", (hood_mid.x+3.6, hood_mid.y, hood_mid.z+0.95), hood_mid+Vector((0,0,0.35)), 56, False)
    set_cam("CAM_Hood_Top", (hood_mid.x+0.05, hood_mid.y-0.22, hood_mid.z+3.55), hood_mid+Vector((0,0,0.55)), 72, False)

    set_cam("CAM_ANIM_Wide", (hc.x+9.0, hc.y-11.5, hc.z+4.2), (hc.x, hc.y+0.8, hc.z+0.5), 32, True)
    set_cam("CAM_ANIM_Medium", (hc.x+5.0, hc.y-7.0, hc.z+2.5), (hc.x, hc.y+0.4, hc.z+0.5), 42, True)
    set_cam("CAM_ANIM_Close", (hc.x+2.2, hc.y-4.0, hc.z+1.7), (hc.x, hc.y+0.1, hc.z+0.55), 60, True)

    cams = sorted([o for o in bpy.data.objects if o.type == "CAMERA"], key=lambda o:o.name)
    visible_count = sum(1 for c in cams if not c.hide_viewport and not c.hide_render)
    log(f"[camera] total={len(cams)} visible={visible_count} hidden={len(cams)-visible_count}; names={[c.name for c in cams]}")
    return {"total": len(cams), "visible": visible_count, "hidden": len(cams)-visible_count, "names": [c.name for c in cams]}

def set_workbench(scene, color_type):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = color_type
    scene.display.shading.show_xray = False
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = True

def setup_render_settings():
    scene = bpy.context.scene
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

def save_visibility_state():
    return {obj.name: (obj.hide_viewport, obj.hide_render) for obj in bpy.data.objects}

def restore_visibility_state(state):
    for name, flags in state.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_viewport, obj.hide_render = flags

def isolate_hoodie(hoodie):
    state = save_visibility_state()
    for obj in bpy.data.objects:
        if obj.type != "CAMERA" and obj != hoodie:
            obj.hide_render = True
    hoodie.hide_render = False
    return state

def render_review(hoodie):
    scene = bpy.context.scene
    old = (scene.render.engine, scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage, scene.camera, scene.render.filepath)
    setup_render_settings()
    renders = []
    state = None
    try:
        specs = [
            ("CAM_Hood_Front", "01_RestoredHoodieFront.png", "MATERIAL", True),
            ("CAM_Hood_LeftSide", "02_RestoredHoodieLeftSideGray.png", "SINGLE", True),
            ("CAM_Hood_RightSide", "03_RestoredHoodieRightSideGray.png", "SINGLE", True),
            ("CAM_Hood_Top", "04_RestoredHoodieTopGray.png", "SINGLE", True),
            ("CAM_SceneWide", "05_ScenePreserved.png", "MATERIAL", False),
        ]
        for cam_name, filename, color_type, isolate in specs:
            cam = bpy.data.objects.get(cam_name)
            if not cam:
                continue
            if isolate:
                state = isolate_hoodie(hoodie)
            set_workbench(scene, color_type)
            scene.camera = cam
            scene.render.filepath = str(OUT / filename)
            bpy.ops.render.render(write_still=True)
            renders.append({"camera": cam.name, "render": filename, "mode": "WORKBENCH_" + color_type})
            log("[render] " + filename)
            if state:
                restore_visibility_state(state)
                state = None
    finally:
        if state:
            restore_visibility_state(state)
        scene.render.engine, scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage, scene.camera, scene.render.filepath = old
    return renders

def object_report(name):
    obj = bpy.data.objects.get(name)
    if not obj:
        return {"name": name, "status": "missing"}
    b = bounds_world(obj)
    return {
        "name": name,
        "type": obj.type,
        "visible": visible(obj),
        "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
        "vertices": len(obj.data.vertices) if obj.type == "MESH" else 0,
        "faces": len(obj.data.polygons) if obj.type == "MESH" else 0,
    }

def write_reports(hoodie_restore, camera_report, disabled_bodyfit, underglow, renders):
    payload = {
        "pass": "restore_imported_hoodie_baseline_v1",
        "method": "Set all non-Basis hoodie shape key values to 0 and set active hoodie key to Basis. This restores the imported mesh baseline without further deformation.",
        "hoodie_restore": hoodie_restore,
        "camera_report": camera_report,
        "disabled_bodyfit_keys": disabled_bodyfit,
        "underglow_lock": underglow,
        "renders": renders,
        "key_objects": [object_report(n) for n in [HERO_NAME, "SACKBOY_Hoodie_Main", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
    }
    (REP / "restore_imported_hoodie_baseline_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    status = {
        "ok": True,
        "hoodie_active_shape_key_after": hoodie_restore["active_shape_key_after"],
        "restored_shape_key_count": len(hoodie_restore["restored_keys"]),
        "vertex_count": hoodie_restore["vertex_count"],
        "face_count": hoodie_restore["face_count"],
        "current_review_images": [r["render"] for r in renders],
    }
    (REP / "RestoreImportedHoodieBaseline_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    md = [
        "# Restore Imported Hoodie Baseline v1",
        "",
        "## Result",
        "- The hoodie was restored to its imported/Basis geometry by setting every non-Basis shape key value to 0.",
        "- No new hoodie deformation was applied.",
        "- F2/Sackboy BODYFIT keys remain disabled.",
        "",
        "## Hoodie counts",
        f"- Vertex count: {hoodie_restore['vertex_count']}",
        f"- Face count: {hoodie_restore['face_count']}",
        f"- Active shape key before: {hoodie_restore['active_shape_key_before']}",
        f"- Active shape key after: {hoodie_restore['active_shape_key_after']}",
        f"- Restored non-Basis shape keys: {len(hoodie_restore['restored_keys'])}",
        "",
        "## Note",
        "The HOODIEFIT shape keys remain in the file for evidence/rollback, but they are inactive. The visible hoodie is the imported Basis mesh.",
    ]
    (REP / "Restore_Imported_Hoodie_Baseline_v1.md").write_text("\n".join(md), encoding="utf-8")
    (REP / "RestoreImportedHoodieBaseline_report.txt").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": []}
    for obj in sorted(bpy.data.objects, key=lambda x:x.name):
        b = bounds_world(obj)
        item = {
            "name": obj.name,
            "type": obj.type,
            "visible": visible(obj),
            "hidden": bool(obj.hide_viewport or obj.hide_render),
            "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
        }
        if obj.type == "MESH":
            item["vertices"] = len(obj.data.vertices)
            item["faces"] = len(obj.data.polygons)
            if obj.data.shape_keys:
                item["shape_keys"] = [{"name": kb.name, "value": round(float(kb.value), 4)} for kb in obj.data.shape_keys.key_blocks]
        if obj.type == "CAMERA":
            item["camera"] = True
        data["objects"].append(item)
    (ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\nUpdated by Restore Imported Hoodie Baseline v1.\n\n"
        "- Hoodie restored to imported/Basis geometry by disabling all non-Basis hoodie shape keys.\n"
        "- No new hoodie deformation applied.\n"
        "- Current review remains image-only; text/json reports go under reports.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "restore_imported_hoodie_baseline_v1", "reports": str(REP), "current_review": str(OUT)}, indent=2), encoding="utf-8")

def main():
    reset_outputs()
    log("[pass] restore imported hoodie baseline v1")
    hoodie = find_hoodie()
    under = restore_underglow()
    disabled = keep_character_baseline()
    hoodie_restore = restore_hoodie_basis(hoodie)
    camera_report = reset_cameras(hoodie)
    renders = render_review(hoodie)
    write_reports(hoodie_restore, camera_report, disabled, under, renders)
    manifest()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "RestoreImportedHoodieBaseline_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
