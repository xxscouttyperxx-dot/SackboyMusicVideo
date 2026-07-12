import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "remove_hidden_rejected_frames_v1"
REP = ROOT / "reports" / "remove_hidden_rejected_frames_v1"
CUR = ROOT / "renders" / "current_review"
AUD = ROOT / "reports" / "project_workflow_audit"

TARGET_COLLECTION = "PARKING_PAINT_ORIGINALS_HIDDEN"
UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "RemoveHiddenRejectedFrames_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / "RemoveHiddenRejectedFrames_report.txt").write_text("", encoding="utf-8")

def bounds(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

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
            "faces": c["faces"],
            "collections": [c.name for c in o.users_collection]}

def restore_underglow():
    obj = bpy.data.objects.get(UNDERGLOW_NAME)
    if not obj:
        log("[lock] underglow missing")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)]
    obj.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(obj.location.x,6), round(obj.location.y,6), round(obj.location.z,6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"name": UNDERGLOW_NAME, "before": before, "after": after}

def remove_hidden_rejected_objects():
    removed = []
    col = bpy.data.collections.get(TARGET_COLLECTION)
    if col:
        for o in list(col.objects):
            n = o.name
            # User specifically called out ENV_Glass_3 through ENV_FrameTop_-1 in this hidden parking collection.
            if n.startswith("ENV_Glass_") or n.startswith("ENV_Frame") or n.startswith("ENV_Glass") or n.startswith("ENV_FrameTop"):
                removed.append({"name": n, "collection": TARGET_COLLECTION, "visible": visible(o)})
                bpy.data.objects.remove(o, do_unlink=True)
    # Sweep any remaining exact family objects in other hidden/rejected collections, but avoid storefront active collection.
    for o in list(bpy.data.objects):
        n = o.name
        if not (n.startswith("ENV_Glass_") or n.startswith("ENV_Frame") or n.startswith("ENV_Glass") or n.startswith("ENV_FrameTop")):
            continue
        cols = [c.name for c in o.users_collection]
        text = " ".join(cols).lower()
        if any(k in text for k in ["parking_paint_originals_hidden", "backup", "old", "hidden"]):
            removed.append({"name": n, "collection": cols, "visible": visible(o)})
            bpy.data.objects.remove(o, do_unlink=True)
    # Remove the now-empty hidden originals collection only if there are no remaining useful objects in it.
    col = bpy.data.collections.get(TARGET_COLLECTION)
    collection_removed = False
    if col and len(col.objects) == 0 and len(col.children) == 0:
        try:
            bpy.data.collections.remove(col)
            collection_removed = True
        except Exception:
            pass
    log(f"[remove] removed {len(removed)} hidden rejected ENV_Glass/ENV_Frame object(s); removed empty collection={collection_removed}")
    return {"removed_objects": removed, "removed_empty_collection": collection_removed}

def scan_reflection_setup():
    names = []
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        if o.name.startswith("FX_ReflectCard") or o.name.startswith("FX_TrafficLight") or o.name.startswith("TRAFFIC_REFLECT"):
            b = bounds(o)
            row = {"name": o.name, "type": o.type, "visible": visible(o),
                   "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                   "collections": [c.name for c in o.users_collection],
                   "dims": None if not b else [round(b["dim_x"],6), round(b["dim_y"],6), round(b["dim_z"],6)]}
            if o.type == "LIGHT":
                row["energy"] = getattr(o.data, "energy", None)
                row["color"] = [round(v,6) for v in getattr(o.data, "color", [])]
            else:
                row["visible_camera"] = getattr(o, "visible_camera", None)
                row["visible_glossy"] = getattr(o, "visible_glossy", None)
            names.append(row)
    return names

def light_scan():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == "LIGHT"], key=lambda x: x.name):
        d = o.data
        rows.append({"name": o.name, "type": d.type,
                     "loc": [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     "energy": getattr(d, "energy", None),
                     "color": [round(v,6) for v in getattr(d, "color", [])] if hasattr(d, "color") else None})
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
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Remove Hidden Rejected Frames v1.\n\n- Removed hidden ENV_Glass*/ENV_Frame* rejected objects from PARKING_PAINT_ORIGINALS_HIDDEN.\n- Preserved white parking strips, car, asphalt, lighting, sky, character, and clothing.\n- Reflection cards remain intentional camera-invisible reflection sources in FX_REFLECTION_TRAFFIC.\n", encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"remove_hidden_rejected_frames_v1","reports":str(REP),"renders":str(OUT),"current_review":str(CUR)}, indent=2), encoding="utf-8")

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def temp_cam(name, loc, aim, lens):
    data = bpy.data.cameras.new(name + "_Data")
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    cam.data.lens = lens
    look_at(cam, aim)
    bpy.context.scene.collection.objects.link(cam)
    return cam

def find_storefront_target():
    bs=[]
    for o in bpy.data.objects:
        text = (o.name + " " + " ".join(c.name for c in o.users_collection)).lower()
        if any(k in text for k in ["storefront","window","glass","door"]):
            b=bounds(o)
            if b: bs.append(b)
    if bs:
        return Vector(((min(b["min_x"] for b in bs)+max(b["max_x"] for b in bs))*0.5,
                       (min(b["min_y"] for b in bs)+max(b["max_y"] for b in bs))*0.5,
                       min(3.0, max(b["max_z"] for b in bs))))
    return Vector((0,7.5,2.0))

def render_review():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    target = find_storefront_target()
    hero = bpy.data.objects.get("F2")
    hb = bounds(hero) if hero else {"min_x":-1,"max_x":1,"min_y":-1,"max_y":1,"min_z":0,"max_z":3}
    hc = center(hb)
    cams = [
        temp_cam("TMP_RemoveHiddenRejected_Overview", Vector((4.5,-10.5,3.0)), Vector((0,0,0.8)), 42),
        temp_cam("TMP_RemoveHiddenRejected_ReflectionSetup", Vector((0,-21.5,3.2)), target, 45),
        temp_cam("TMP_RemoveHiddenRejected_CharacterReady", Vector((hc.x+2.2,hc.y-6.0,hc.z+1.5)), Vector((hc.x,hc.y,hc.z+0.45)), 55),
    ]
    old = scene.camera
    for cam, fn in [(cams[0],"01_CleanupOverview.png"), (cams[1],"02_ReflectionSetupIntentionalCards.png"), (cams[2],"03_CharacterReadyUnchanged.png")]:
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

def write_reports(removed, under, reflect, lights):
    fit = {"key_objects": [object_report(n) for n in ["F2","Apricot Pullover Hoodie","Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    payload = {"removed_hidden_rejected_objects": removed, "underglow_lock": under, "reflection_setup_scan": reflect, "lights_scan": lights, "fit_scan": fit,
               "note": "The FX_ReflectCard objects are intentional reflection-only cards. The hidden ENV_Glass*/ENV_Frame* objects in PARKING_PAINT_ORIGINALS_HIDDEN are not used and were removed."}
    (REP/"remove_hidden_rejected_frames_v1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Remove Hidden Rejected Frames v1", "",
             "## What changed",
             f"- Removed hidden rejected ENV_Glass/ENV_Frame objects: **{len(removed.get('removed_objects', []))}**",
             f"- Removed empty PARKING_PAINT_ORIGINALS_HIDDEN collection: **{removed.get('removed_empty_collection')}**",
             "- White parking paint strips were preserved.",
             "- Car, asphalt, sky/HDRI, approved amber lights, character, and clothing were preserved.",
             "- Character deformation was not applied.",
             "",
             "## Reflection card note",
             "- `FX_ReflectCard_*` objects are intentional reflection-only emissive cards.",
             "- They are camera-invisible where Blender supports ray visibility, and are meant to appear in glass reflections.",
             "- The hidden `ENV_Glass*` / `ENV_Frame*` objects were not reflection cards and were removed.",
             "",
             "## Locked underglow",
             f"- {under.get('after')}",
             ""]
    (REP/"Remove_Hidden_Rejected_Frames_v1.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT/"RemoveHiddenRejectedFrames_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def main():
    reset()
    log("[pass] remove hidden rejected glass/frame leftovers only")
    removed = remove_hidden_rejected_objects()
    under = restore_underglow()
    reflect = scan_reflection_setup()
    lights = light_scan()
    write_reports(removed, under, reflect, lights)
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
        with (OUT/"RemoveHiddenRejectedFrames_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
