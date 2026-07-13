import bpy, json, traceback
from pathlib import Path

def find_root():
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "blender" / "sackboy_scene.blend").exists():
            return parent
    return Path(__file__).resolve().parents[3]

ROOT = find_root()
REP = ROOT / "reports" / "collection_visibility_fix_retry_push_v1"
REP.mkdir(parents=True, exist_ok=True)

HIDDEN_COLLECTION = "08_HIDDEN_NONVISIBLE_REVIEW"

def visible_get(obj):
    try:
        return bool(obj.visible_get())
    except Exception:
        return not obj.hide_viewport

def rec_counts():
    objs = list(bpy.data.objects)
    return {
        "total_objects": len(objs),
        "visible_objects": sum(1 for o in objs if visible_get(o)),
        "hidden_objects": sum(1 for o in objs if not visible_get(o)),
        "mesh_objects": sum(1 for o in objs if o.type == "MESH"),
        "camera_objects": sum(1 for o in objs if o.type == "CAMERA"),
        "light_objects": sum(1 for o in objs if o.type == "LIGHT"),
    }

def collection_objects(coll):
    if not coll:
        return []
    return sorted([o.name for o in coll.objects])

def main():
    before = rec_counts()
    coll = bpy.data.collections.get(HIDDEN_COLLECTION)
    if coll is None:
        raise RuntimeError(f"Missing expected collection: {HIDDEN_COLLECTION}")

    before_collection = {
        "name": coll.name,
        "hide_viewport": bool(coll.hide_viewport),
        "hide_render": bool(coll.hide_render),
        "object_count": len(coll.objects),
        "objects": collection_objects(coll),
    }

    # The organization pass moved previously collection-hidden objects into a visible collection,
    # which made one hidden thing visible by effective viewport state.
    # This fix makes the hidden-review collection actually hidden/render-disabled again.
    coll.hide_viewport = True
    coll.hide_render = True

    # Extra safety: objects inside this collection stay non-selectable.
    changed_select = []
    for obj in coll.objects:
        before_select = bool(obj.hide_select)
        obj.hide_select = True
        if before_select != bool(obj.hide_select):
            changed_select.append(obj.name)

    after = rec_counts()
    after_collection = {
        "name": coll.name,
        "hide_viewport": bool(coll.hide_viewport),
        "hide_render": bool(coll.hide_render),
        "object_count": len(coll.objects),
        "objects": collection_objects(coll),
    }

    report = {
        "pass": "collection_visibility_fix_retry_push_v1",
        "reason": "SceneCollectionsOrganization_v1 reduced multi-collection listings, but visible count changed 204 -> 205. This fixes the hidden-review collection so hidden review objects remain hidden/non-renderable as intended.",
        "safety": "No objects deleted. No geometry/material/modifier/shape-key changes. Only collection visibility flags for 08_HIDDEN_NONVISIBLE_REVIEW and select-lock on objects inside it were changed.",
        "counts_before": before,
        "counts_after": after,
        "collection_before": before_collection,
        "collection_after": after_collection,
        "objects_select_locked": changed_select,
    }
    (REP / "collection_visibility_fix_retry_push_v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REP / "CollectionVisibilityFixRetryPush_status.json").write_text(json.dumps({
        "ok": True,
        "visible_objects_before": before["visible_objects"],
        "visible_objects_after": after["visible_objects"],
        "hidden_collection": HIDDEN_COLLECTION,
        "hidden_collection_hide_viewport": coll.hide_viewport,
        "hidden_collection_hide_render": coll.hide_render,
    }, indent=2), encoding="utf-8")

    md = [
        "# Collection Visibility Fix + Retry Push v1",
        "",
        "## Why this exists",
        "The collection organization pass succeeded locally, but its log showed visible objects changed from 204 to 205. That means one object that had previously been hidden by collection visibility became effectively visible after being moved into the new clean collection structure.",
        "",
        "## Fix",
        f"- Set `{HIDDEN_COLLECTION}` collection `hide_viewport=True`.",
        f"- Set `{HIDDEN_COLLECTION}` collection `hide_render=True`.",
        "- Set objects inside that collection to `hide_select=True`.",
        "",
        "## Safety",
        "- No objects deleted.",
        "- No visible character/clothing/scene objects intentionally changed.",
        "- No geometry, material, modifier, shape-key, light, or camera changes.",
        "",
        "## Counts",
        f"- Total objects before/after: {before['total_objects']} -> {after['total_objects']}",
        f"- Visible objects before/after: {before['visible_objects']} -> {after['visible_objects']}",
        f"- Hidden objects before/after: {before['hidden_objects']} -> {after['hidden_objects']}",
        "",
        "## Push note",
        "The previous push failed after the local commit was created. This package creates a small visibility-fix commit on top and uses a longer retry loop for Git LFS/network failures.",
    ]
    (REP / "Collection_Visibility_Fix_Retry_Push_v1.md").write_text("\n".join(md), encoding="utf-8")
    (REP / "CollectionVisibilityFixRetryPush_report.txt").write_text("\n".join(md), encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "sackboy_scene.blend"))
    print("[visibility_fix] collection visibility fix retry push v1")
    print(f"[counts] visible {before['visible_objects']} -> {after['visible_objects']}; total {before['total_objects']} -> {after['total_objects']}")
    print(f"[collection] {HIDDEN_COLLECTION} hide_viewport={coll.hide_viewport} hide_render={coll.hide_render} objects={len(coll.objects)}")
    print("[save] " + str(ROOT / "blender" / "sackboy_scene.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "CollectionVisibilityFixRetryPush_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
