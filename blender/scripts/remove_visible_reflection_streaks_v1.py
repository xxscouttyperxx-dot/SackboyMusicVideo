import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "remove_visible_reflection_streaks_v1"
REP = ROOT / "reports" / "remove_visible_reflection_streaks_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "RemoveVisibleReflectionStreaks_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "RemoveVisibleReflectionStreaks_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def counts(o):
    if o and o.type == "MESH":
        return {"vertices": len(o.data.vertices), "faces": len(o.data.polygons)}
    return {"vertices": 0, "faces": 0}

def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {"name": name, "status": "missing"}
    b = bounds(o); c = counts(o)
    return {"name": name, "status": "present", "visible": visible(o),
            "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
            "faces": c["faces"], "collections": [c.name for c in o.users_collection]}

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

def remove_visible_streak_overlays():
    removed = []
    names = []
    for o in bpy.data.objects:
        if o.name.startswith("FX_GlassStreak_") or o.name.startswith("FX_WindowGlow_"):
            names.append(o.name)
    for name in names:
        o = bpy.data.objects.get(name)
        if o:
            removed.append({"name": name, "visible": visible(o), "collections": [c.name for c in o.users_collection]})
            bpy.data.objects.remove(o, do_unlink=True)
    log(f"[remove] removed {len(removed)} visible reflection streak/window-glow overlay object(s)")
    return removed

def harden_reflection_cards():
    rows = []
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        if not o.name.startswith("FX_ReflectCard_"):
            continue
        o.hide_viewport = False
        o.hide_render = False
        for attr, val in [("visible_camera", False), ("visible_shadow", False), ("visible_diffuse", False), ("visible_glossy", True)]:
            try:
                setattr(o, attr, val)
            except Exception:
                pass
        try:
            o.cycles_visibility.camera = False
            o.cycles_visibility.shadow = False
            o.cycles_visibility.diffuse = False
            o.cycles_visibility.glossy = True
            o.cycles_visibility.transmission = True
        except Exception:
            pass
        o["intent"] = "reflection-only emissive source; not a visible render prop"
        b = bounds(o)
        rows.append({"name": o.name, "visible_camera": getattr(o, "visible_camera", None), "visible_glossy": getattr(o, "visible_glossy", None),
                     "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]})
    log(f"[cards] preserved/hardened {len(rows)} reflection-only card(s)")
    return rows

def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x:x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type,
                     "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
    return rows

def scan_fx():
    rows = []
    for o in sorted(bpy.data.objects, key=lambda x:x.name):
        if o.name.startswith("FX_ReflectCard_") or o.name.startswith("FX_GlassStreak_") or o.name.startswith("FX_TrafficLight"):
            b = bounds(o)
            row = {"name": o.name, "type": o.type, "visible": visible(o),
                   "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                   "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)],
                   "intent": o.get("intent", ""), "collections": [c.name for c in o.users_collection]}
            if o.type == "LIGHT":
                row["energy"] = getattr(o.data, "energy", None)
                row["color"] = [round(v,6) for v in getattr(o.data, "color", [])]
            else:
                row["visible_camera"] = getattr(o, "visible_camera", None)
                row["visible_glossy"] = getattr(o, "visible_glossy", None)
            rows.append(row)
    return rows

def manifest():
    data = {"blend_file": bpy.data.filepath, "objects": [], "collections": []}
    for col in sorted(bpy.data.collections, key=lambda c:c.name):
        data["collections"].append({"name": col.name, "hide_viewport": bool(col.hide_viewport), "hide_render": bool(col.hide_render),
                                    "object_count": len(col.objects), "child_count": len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x:x.name):
        b = bounds(o)
        e = {"name": o.name, "type": o.type, "collections": [c.name for c in o.users_collection], "visible": visible(o),
             "location": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
             "dimensions": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
        if o.type == "MESH": e.update(counts(o))
        if o.type == "LIGHT":
            e["energy"] = getattr(o.data, "energy", None)
            e["color"] = [round(v,6) for v in getattr(o.data, "color", [])] if hasattr(o.data, "color") else None
        data["objects"].append(e)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Remove Visible Reflection Streaks v1.\n\n- Removed visible FX_GlassStreak/FX_WindowGlow overlay objects that were showing as floating lines in renders.\n- Preserved FX_ReflectCard reflection-only cards and red/yellow/green traffic lights.\n- Preserved car, asphalt, parking strips, approved lighting, sky/HDRI, character, and clothing.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"remove_visible_reflection_streaks_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

def look_at(o, target):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def temp_cam(name, loc, aim, lens):
    data = bpy.data.cameras.new(name+"_Data")
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    cam.data.lens = lens
    look_at(cam, aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def find_scene_target():
    # Focus storefront area if present, otherwise world center.
    bs = []
    for o in bpy.data.objects:
        text = (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()
        if any(k in text for k in ["storefront", "window", "glass", "door"]):
            b = bounds(o)
            if b: bs.append(b)
    if bs:
        return Vector(((min(b["min_x"] for b in bs)+max(b["max_x"] for b in bs))*0.5,
                       (min(b["min_y"] for b in bs)+max(b["max_y"] for b in bs))*0.5,
                       min(3.0, max(b["max_z"] for b in bs))))
    return Vector((0, 5, 1.5))

def render_review():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    target = find_scene_target()
    hero = bpy.data.objects.get("F2")
    hb = bounds(hero) if hero else {"min_x":-1,"max_x":1,"min_y":-1,"max_y":1,"min_z":0,"max_z":3}
    hc = center(hb)
    cams = [
        temp_cam("TMP_RemoveStreaks_Storefront", Vector((target.x+6.5, target.y-9.0, target.z+1.1)), target, 50),
        temp_cam("TMP_RemoveStreaks_FXCards", Vector((target.x, target.y-11.0, target.z+1.5)), target, 45),
        temp_cam("TMP_RemoveStreaks_Character", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old = scene.camera
    for cam, fn in [(cams[0],"01_StorefrontNoFloatingStreaks.png"), (cams[1],"02_ReflectionCardsOnlyCheck.png"), (cams[2],"03_CharacterNoStreakIntersections.png")]:
        scene.camera = cam
        scene.render.filepath = str(OUT/fn)
        bpy.ops.render.render(write_still=True)
        log("[render] " + fn)
    scene.camera = old
    for cam in cams:
        bpy.data.objects.remove(cam, do_unlink=True)
    CUR.mkdir(parents=True, exist_ok=True)
    for p in CUR.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT.glob("*"):
        if p.is_file():
            (CUR/p.name).write_bytes(p.read_bytes())

def write_reports(removed, cards, under, fx, lights):
    fit = {"key_objects": [object_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    payload = {"removed_visible_streaks": removed, "reflection_cards_preserved": cards, "underglow_lock": under, "fx_scan_after": fx, "lights_scan": lights, "fit_scan": fit,
               "note": "The visible FX_GlassStreak overlays were a fallback draft to force reflections in Eevee. They were removed because they showed as floating/scene-intersecting lines. Reflection-only cards remain."}
    (REP/"remove_visible_reflection_streaks_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Remove Visible Reflection Streaks v1", "",
             "## What changed",
             f"- Removed visible FX_GlassStreak / FX_WindowGlow overlays: **{len(removed)}**",
             f"- Preserved reflection-only FX_ReflectCard objects: **{len(cards)}**",
             "- Red/yellow/green traffic lights were preserved.",
             "- Car, asphalt, white parking strips, approved amber lights, sky/HDRI, character, and clothing were preserved.",
             "",
             "## Why",
             "- The visible streak overlays were a fallback draft to force reflections in Eevee.",
             "- They showed up as floating/intersecting lines in renders, so they are removed.",
             "- Next reflection attempt should use either better material/probe setup or cards positioned only where they cannot enter camera view.",
             "",
             "## Locked underglow",
             f"- {under.get('after')}"]
    (REP/"Remove_Visible_Reflection_Streaks_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"RemoveVisibleReflectionStreaks_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] remove visible reflection streak fallback geometry")
    removed = remove_visible_streak_overlays()
    cards = harden_reflection_cards()
    under = restore_underglow()
    fx = scan_fx()
    lights = scan_lights()
    write_reports(removed, cards, under, fx, lights)
    manifest()
    render_review()
    out = ROOT / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] " + str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT/"RemoveVisibleReflectionStreaks_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
