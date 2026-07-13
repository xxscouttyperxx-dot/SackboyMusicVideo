import bpy, json, traceback, re
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
if not (ROOT / "blender" / "sackboy_scene.blend").exists():
    ROOT = Path(__file__).resolve().parents[2]

REP = ROOT / "reports" / "temp_safe_duplicate_visibility_cleanup_v1"
REP.mkdir(parents=True, exist_ok=True)

ARCHIVE_COLL = "ARCHIVE_HIDDEN_HELPERS_DO_NOT_DELETE"
KEEP_VISIBLE = True

# Extremely conservative. These were hidden in viewport but renderable according to the read-only audit.
# They are not current visible scene objects. This pass only makes them non-renderable/select-locked
# and places them in a clearly named archive collection. It does NOT delete them.
SAFE_HIDE_RENDER_OBJECTS = [
    "HERO_BlackSkateShoe_L_WhiteSole",
    "HERO_BlackSkateShoe_R_WhiteSole",
    "MOUTH_CUT_GUIDE_Data",
]

def strip_suffix(name):
    return re.sub(r"\.\d{3,}$", "", name)

def visible_get(obj):
    try:
        return bool(obj.visible_get())
    except Exception:
        return not obj.hide_viewport

def bounds_world(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return {
            "min": [round(min(xs), 6), round(min(ys), 6), round(min(zs), 6)],
            "max": [round(max(xs), 6), round(max(ys), 6), round(max(zs), 6)],
            "dimensions": [round(max(xs)-min(xs), 6), round(max(ys)-min(ys), 6), round(max(zs)-min(zs), 6)]
        }
    except Exception:
        return None

def rec(obj):
    data = getattr(obj, "data", None)
    return {
        "name": obj.name,
        "base_name": strip_suffix(obj.name),
        "type": obj.type,
        "visible_viewport": visible_get(obj),
        "hide_viewport": bool(obj.hide_viewport),
        "hide_render": bool(obj.hide_render),
        "hide_select": bool(obj.hide_select),
        "collections": [c.name for c in obj.users_collection],
        "collection_count": len(obj.users_collection),
        "data_name": data.name if data else None,
        "data_users": int(getattr(data, "users", 0)) if data else 0,
        "vertices": len(data.vertices) if obj.type == "MESH" and data else 0,
        "faces": len(data.polygons) if obj.type == "MESH" and data else 0,
        "bounds_world": bounds_world(obj),
    }

def get_archive_collection():
    coll = bpy.data.collections.get(ARCHIVE_COLL)
    if coll is None:
        coll = bpy.data.collections.new(ARCHIVE_COLL)
        bpy.context.scene.collection.children.link(coll)
    coll.hide_viewport = False
    coll.hide_render = True
    return coll

def link_to_archive(obj, archive):
    if obj.name not in archive.objects:
        archive.objects.link(obj)

def analyze():
    objects = [rec(o) for o in bpy.data.objects]
    by_base = {}
    by_data = {}
    for r in objects:
        by_base.setdefault(r["base_name"], []).append(r["name"])
        if r["data_name"]:
            by_data.setdefault(r["type"] + "::" + r["data_name"], []).append(r["name"])
    dup_base = {k:v for k,v in by_base.items() if len(v) > 1}
    shared_data = {k:v for k,v in by_data.items() if len(v) > 1}
    multi = [r for r in objects if r["collection_count"] > 1]
    visible = [r for r in objects if r["visible_viewport"]]
    hidden = [r for r in objects if not r["visible_viewport"]]
    hidden_renderable = [r for r in hidden if not r["hide_render"]]
    return {
        "total_objects": len(objects),
        "visible_objects": len(visible),
        "hidden_objects": len(hidden),
        "duplicate_base_name_groups": dup_base,
        "shared_data_groups": shared_data,
        "multi_collection_objects": multi,
        "hidden_but_renderable": hidden_renderable,
        "all_objects": objects,
    }

def main():
    before = analyze()
    archive = get_archive_collection()
    actions = []
    skipped = []

    for name in SAFE_HIDE_RENDER_OBJECTS:
        obj = bpy.data.objects.get(name)
        if not obj:
            skipped.append({"name": name, "reason": "not found"})
            continue
        was_visible = visible_get(obj)
        before_state = rec(obj)
        # Do not touch anything currently visible in the scene.
        if KEEP_VISIBLE and was_visible:
            skipped.append({"name": name, "reason": "object is currently visible; left untouched"})
            continue
        link_to_archive(obj, archive)
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_select = True
        actions.append({
            "name": name,
            "action": "archived hidden helper / set hide_viewport=true hide_render=true hide_select=true",
            "before": before_state,
            "after": rec(obj),
        })

    after = analyze()

    explanation = {
        "outliner_highlight_cause": "Your audit shows the main issue is multi-collection linking: 40 objects appear in multiple collections. That makes one selected object highlight in more than one Outliner location. It is not necessarily an actual duplicate object.",
        "shared_data_cause": "There is also one shared mesh-data group: F2 and F2.001 share the same mesh datablock. F2 is visible; F2.001 is hidden/render-disabled. This package does not delete or unlink either one.",
        "generic_names_warning": "The big Plane/Circle/Bolt duplicate-name groups are mostly imported asset parts, especially the Audi and sign. They are visible unique data pieces, not safe duplicates to remove automatically.",
        "what_this_changed": "This package only archived three hidden helper objects that were hidden in the viewport but still renderable/selectable. It did not touch visible objects."
    }

    report = {
        "pass": "temp_safe_duplicate_visibility_cleanup_v1",
        "safety": "No objects deleted. No visible objects hidden. Only selected hidden helper objects made render-disabled/select-locked and linked into an archive collection.",
        "explanation": explanation,
        "actions": actions,
        "skipped": skipped,
        "before_summary": {
            "total_objects": before["total_objects"],
            "visible_objects": before["visible_objects"],
            "hidden_objects": before["hidden_objects"],
            "duplicate_base_name_group_count": len(before["duplicate_base_name_groups"]),
            "shared_data_group_count": len(before["shared_data_groups"]),
            "multi_collection_object_count": len(before["multi_collection_objects"]),
            "hidden_but_renderable_count": len(before["hidden_but_renderable"]),
        },
        "after_summary": {
            "total_objects": after["total_objects"],
            "visible_objects": after["visible_objects"],
            "hidden_objects": after["hidden_objects"],
            "duplicate_base_name_group_count": len(after["duplicate_base_name_groups"]),
            "shared_data_group_count": len(after["shared_data_groups"]),
            "multi_collection_object_count": len(after["multi_collection_objects"]),
            "hidden_but_renderable_count": len(after["hidden_but_renderable"]),
        },
        "duplicate_base_name_groups": before["duplicate_base_name_groups"],
        "shared_data_groups": before["shared_data_groups"],
        "multi_collection_objects": before["multi_collection_objects"],
        "hidden_but_renderable_before": before["hidden_but_renderable"],
        "hidden_but_renderable_after": after["hidden_but_renderable"],
    }

    (REP / "temp_safe_duplicate_visibility_cleanup_v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = []
    md.append("# Temp Safe Duplicate Visibility Cleanup v1")
    md.append("")
    md.append("## What I found from the audit")
    md.append("- Main cause of repeated highlighted Outliner labels: **multi-collection linking**, not true duplicates.")
    md.append(f"- Multi-collection objects before: {len(before['multi_collection_objects'])}")
    md.append(f"- Duplicate base-name groups before: {len(before['duplicate_base_name_groups'])}")
    md.append(f"- Shared mesh-data groups before: {len(before['shared_data_groups'])}")
    md.append("")
    md.append("## What this package changed")
    if actions:
        for a in actions:
            md.append(f"- {a['name']}: {a['action']}")
    else:
        md.append("- No objects changed.")
    md.append("")
    md.append("## What it deliberately did NOT touch")
    md.append("- Did not delete anything.")
    md.append("- Did not hide any currently visible object.")
    md.append("- Did not touch the visible current Sackboy character.")
    md.append("- Did not touch the visible current hoodie/clothing.")
    md.append("- Did not touch the Audi/car Plane/Circle/Bolt parts because those are visible imported asset pieces, not safe duplicates.")
    md.append("- Did not unlink multi-collection objects yet, because that is organization cleanup and should be reviewed before changing collection structure.")
    md.append("")
    md.append("## Important exact findings")
    md.append("- `F2` and `F2.001` are the only shared mesh-data group. `F2` is visible. `F2.001` is hidden/render-disabled. They share the same mesh data-block.")
    md.append("- `SACKBOY_Hoodie_EditProxy` is visible and appears to be your current edited hoodie.")
    md.append("- `SACKBOY_Hoodie_Main` is hidden and appears to be the original/imported hoodie baseline backup.")
    md.append("- Many `Plane`, `Circle`, and `Bolt` names belong to visible Audi/sign asset pieces. The repeated names are generic import names, not automatically removable duplicates.")
    md.append("")
    md.append("## Before / after")
    md.append(f"- Hidden-but-renderable before: {len(before['hidden_but_renderable'])}")
    md.append(f"- Hidden-but-renderable after: {len(after['hidden_but_renderable'])}")
    md.append(f"- Total objects before/after: {before['total_objects']} -> {after['total_objects']}")
    md.append(f"- Visible objects before/after: {before['visible_objects']} -> {after['visible_objects']}")
    md.append("")
    md.append("## Next recommended cleanup")
    md.append("Next pass should be collection organization only: move/link objects into clean top-level collections without deleting mesh objects. I recommend organizing first, then deciding what to remove.")
    (REP / "Temp_Safe_Duplicate_Visibility_Cleanup_v1.md").write_text("\n".join(md), encoding="utf-8")
    (REP / "TempSafeDuplicateVisibilityCleanup_report.txt").write_text("\n".join(md), encoding="utf-8")
    (REP / "TempSafeDuplicateVisibilityCleanup_status.json").write_text(json.dumps({
        "ok": True,
        "actions_count": len(actions),
        "skipped_count": len(skipped),
        "hidden_but_renderable_before": len(before["hidden_but_renderable"]),
        "hidden_but_renderable_after": len(after["hidden_but_renderable"]),
        "visible_objects_before": before["visible_objects"],
        "visible_objects_after": after["visible_objects"],
    }, indent=2), encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "sackboy_scene.blend"))
    print("[cleanup] temp safe duplicate visibility cleanup v1")
    print(f"[actions] {len(actions)} hidden helpers archived/render-disabled; {len(skipped)} skipped")
    print(f"[hidden_renderable] {len(before['hidden_but_renderable'])} -> {len(after['hidden_but_renderable'])}")
    print("[save] " + str(ROOT / "blender" / "sackboy_scene.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "TempSafeDuplicateVisibilityCleanup_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
