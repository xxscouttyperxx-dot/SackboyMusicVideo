import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "restore_character_baseline_v1"
REP = ROOT / "reports" / "restore_character_baseline_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)
BODYFIT_PREFIXES = ("BODYFIT_",)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "RestoreCharacterBaseline_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "RestoreCharacterBaseline_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center_from_bounds(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def restore_underglow():
    o = bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log("[lock] underglow missing")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after}

def disable_bodyfit_shape_keys(obj):
    disabled = []
    kept = []
    if obj.type != "MESH" or not obj.data.shape_keys:
        return {"disabled": disabled, "kept": kept, "active_shape_key": None}

    for kb in obj.data.shape_keys.key_blocks:
        before = float(kb.value)
        if kb.name.startswith(BODYFIT_PREFIXES):
            kb.value = 0.0
            disabled.append({"name": kb.name, "before": round(before,4), "after": 0.0})
        else:
            kept.append({"name": kb.name, "value": round(before,4)})

    obj["body_fit_pass"] = "RestoreCharacterBaseline_v1"
    obj["body_fit_shape_key"] = "Basis/restored visual baseline; BODYFIT keys disabled"
    log(f"[restore] disabled {len(disabled)} BODYFIT shape key(s); F2 returns to Basis visual state")
    return {"disabled": disabled, "kept": kept, "active_shape_key": obj.active_shape_key.name if obj.active_shape_key else None}

def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {"name": name, "status": "missing"}
    b = bounds_world(o)
    shape_keys = []
    if o.type == "MESH" and o.data.shape_keys:
        shape_keys = [{"name": kb.name, "value": round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
    return {"name": name, "status": "present", "type": o.type, "visible": visible(o),
            "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "vertices": len(o.data.vertices) if o.type == "MESH" else 0,
            "faces": len(o.data.polygons) if o.type == "MESH" else 0,
            "shape_keys": shape_keys,
            "collections": [c.name for c in o.users_collection]}

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type, "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def setup_render_settings():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.samples = 80
        scene.cycles.preview_samples = 12
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.glossy_bounces = 4
    except Exception:
        pass
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    log("[render] Cycles review renders retained; viewport preview samples remain low")

def look_at(o, target):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def make_or_update_cam(name, loc, target, lens):
    cam = bpy.data.objects.get(name)
    if not cam or cam.type != "CAMERA":
        data = bpy.data.cameras.new(name + "_Data")
        cam = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    return cam

def render_review():
    scene = bpy.context.scene
    hero = bpy.data.objects.get(HERO_NAME)
    hb = bounds_world(hero)
    target = center_from_bounds(hb) if hb else Vector((0,0,1.4))
    if hb:
        target.z = hb["min_z"] + hb["dim_z"] * 0.52

    setups = [
        ("CAM_REVIEW_RestoredCharacter_Front", (target.x, target.y - 6.0, target.z + 0.45), target, 58, "01_RestoredCharacterFront.png"),
        ("CAM_REVIEW_RestoredCharacter_Profile", (target.x + 5.1, target.y - 0.9, target.z + 0.45), target, 62, "02_RestoredCharacterProfile.png"),
        ("CAM_REVIEW_RestoredFaceHands", (target.x + 1.65, target.y - 3.3, target.z + 1.42), (target.x, target.y - 0.1, target.z + 1.05), 70, "03_RestoredFaceHands.png"),
        ("CAM_REVIEW_StorefrontReflection", (target.x + 7.8, target.y - 10.0, target.z + 1.4), (target.x, target.y + 4.2, target.z + 0.9), 48, "04_StorefrontReflectionPreserved.png"),
    ]
    cams = []
    old = scene.camera
    for name, loc, tgt, lens, fn in setups:
        cam = make_or_update_cam(name, loc, tgt, lens)
        cams.append({"name": name, "render": fn, "loc": [round(cam.location.x,6), round(cam.location.y,6), round(cam.location.z,6)], "lens": lens})
        scene.camera = cam
        scene.render.filepath = str(OUT / fn)
        bpy.ops.render.render(write_still=True)
        log("[render] " + fn)
    scene.camera = old
    return cams

def copy_current_review():
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR / p.name).write_bytes(p.read_bytes())

def write_reports(disabled, under, cams):
    payload = {
        "pass": "restore_character_baseline_v1",
        "shape_key_restore": disabled,
        "underglow_lock": under,
        "review_cameras": cams,
        "key_objects": [object_report(n) for n in ["F2", "Apricot Pullover Hoodie", "Cargo pants", "Plane.001", "Plane.022", "Asphalt ground", "Audi e-tron GT quattro Black"]],
        "lights_scan": scan_lights(),
        "notes": [
            "This pass intentionally restores the visual character to the mesh Basis state after the reflection passes.",
            "The bad BODYFIT shape keys are not deleted, but their values are set to 0 so they no longer affect F2.",
            "Reflection setup and scene look are preserved."
        ],
        "next_goals": [
            "Use gentler, isolated deformation after this reset.",
            "Avoid algorithmic face/leg/hand distortion until a safer approach is chosen.",
            "Prefer fitting hoodie/pants around the baseline body before further sculpting F2."
        ]
    }
    (REP / "restore_character_baseline_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "RestoreCharacterBaseline_status.json").write_text(json.dumps({"ok": True, "disabled_bodyfit_keys": len(disabled.get("disabled", [])), "review_cameras": [c["name"] for c in cams]}, indent=2), encoding="utf-8")
    md = [
        "# Restore Character Baseline v1",
        "",
        "## Changes",
        "- Disabled all `BODYFIT_*` shape key values on `F2`.",
        "- This visually restores the character to the mesh Basis state while preserving the current reflection/scene work.",
        "- Did not delete shape keys; they remain as disabled history for safety.",
        "- Kept the Cycles reflection setup, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting.",
        "",
        "## Why",
        "- The previous silhouette pass distorted the character into an unacceptable pitbull/four-leg/snouted shape.",
        "- This reset returns to the first usable character state after the reflection passes instead of trying to sculpt over the distortion.",
        "",
        "## Next goal",
        "- Resume with a safer method: fit clothing around the restored body first, then make only small, targeted body tweaks."
    ]
    (REP / "Restore_Character_Baseline_v1.md").write_text("\n".join(md), encoding="utf-8")

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render),
                                    "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(o)
        item = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection],
                "visible": visible(o), "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
        if o.type == "MESH":
            item["vertices"] = len(o.data.vertices)
            item["faces"] = len(o.data.polygons)
            if o.data.shape_keys:
                item["shape_keys"] = [{"name": kb.name, "value": round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
        if o.type == "LIGHT":
            item["energy"] = getattr(o.data, "energy", None)
            item["color"] = [round(v,6) for v in getattr(o.data, "color", [])] if hasattr(o.data, "color") else None
        if o.type == "CAMERA" and o.name.startswith("CAM_REVIEW_"):
            item["review_camera"] = True
        data["objects"].append(item)
    (ROOT / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD / "scene_layout_summary.md").write_text(
        "# Scene Layout Summary\n\nUpdated by Restore Character Baseline v1.\n\n"
        "- Disabled all BODYFIT shape key values on F2 to restore visual character baseline.\n"
        "- Preserved current reflection setup and scene lighting.\n", encoding="utf-8")
    (AUD / "project_file_layout.json").write_text(json.dumps({"generated_by": "restore_character_baseline_v1", "reports": str(REP), "renders": str(OUT), "current_review": str(CUR)}, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] restore character baseline v1")
    hero = bpy.data.objects.get(HERO_NAME)
    if not hero:
        raise RuntimeError("F2 character mesh was not found")
    under = restore_underglow()
    setup_render_settings()
    disabled = disable_bodyfit_shape_keys(hero)
    cams = render_review()
    write_reports(disabled, under, cams)
    copy_current_review()
    manifest()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / "RestoreCharacterBaseline_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
