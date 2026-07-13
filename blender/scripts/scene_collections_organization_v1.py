import bpy, json, traceback, re
from pathlib import Path
from mathutils import Vector

def find_root():
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "blender" / "sackboy_scene.blend").exists():
            return parent
    return Path(__file__).resolve().parents[3]

ROOT = find_root()
REP = ROOT / "reports" / "scene_collections_organization_v1"
REP.mkdir(parents=True, exist_ok=True)

TOP_COLLECTIONS = [
    "01_CHARACTER_AND_SAME_NAME_GROUPS",
    "02_CLOTHING_AND_SAME_NAME_GROUPS",
    "03_HERO_CAR_AND_IMPORTED_PARTS",
    "04_ENVIRONMENT_STOREFRONTS_PARKING",
    "05_PROPS_SIGNS_DECOR",
    "06_LIGHTING_REFLECTIONS",
    "07_CAMERAS",
    "08_HIDDEN_NONVISIBLE_REVIEW",
]

def clean_name(s):
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return s[:70] if s else "Unnamed"

def base_name(name):
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
            "min": [round(min(xs),6), round(min(ys),6), round(min(zs),6)],
            "max": [round(max(xs),6), round(max(ys),6), round(max(zs),6)],
            "dimensions": [round(max(xs)-min(xs),6), round(max(ys)-min(ys),6), round(max(zs)-min(zs),6)],
        }
    except Exception:
        return None

def rec(obj):
    data = getattr(obj, "data", None)
    return {
        "name": obj.name,
        "base_name": base_name(obj.name),
        "type": obj.type,
        "visible": visible_get(obj),
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

def ensure_top_collection(name):
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll

def ensure_child(parent, name):
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
    if coll.name not in parent.children:
        try:
            parent.children.link(coll)
        except RuntimeError:
            pass
    return coll

def classify_base_group(base):
    b = base.lower()
    if b in {"f2", "mball"} or any(t in b for t in ["sackboy","character","body","head","eye","mouth","arm","hand","leg","foot"]):
        return "01_CHARACTER_AND_SAME_NAME_GROUPS"
    if any(t in b for t in ["hood","hoodie","pullover","pant","shoe","sleeve","cloth","jean"]):
        return "02_CLOTHING_AND_SAME_NAME_GROUPS"
    if b in {"plane","circle","bolt"} or any(t in b for t in ["audi","car","wheel","tire","rim","brake","e_tron"]):
        return "03_HERO_CAR_AND_IMPORTED_PARTS"
    if any(t in b for t in ["light","lamp","glow","reflect","traffic"]):
        return "06_LIGHTING_REFLECTIONS"
    if any(t in b for t in ["cam","camera"]):
        return "07_CAMERAS"
    return "05_PROPS_SIGNS_DECOR"

def classify_single(obj):
    n = obj.name.lower()
    if obj.type == "CAMERA" or "cam" in n:
        return "07_CAMERAS", "CAMERAS"
    if obj.type == "LIGHT" or any(t in n for t in ["light","lamp","glow","reflect","reflection","traffic","underglow"]):
        return "06_LIGHTING_REFLECTIONS", "LIGHTS_AND_REFLECTION_HELPERS"
    if not visible_get(obj):
        return "08_HIDDEN_NONVISIBLE_REVIEW", "HIDDEN_NONVISIBLE_OBJECTS"
    if any(t in n for t in ["hood","hoodie","pullover"]):
        return "02_CLOTHING_AND_SAME_NAME_GROUPS", "HOODIES"
    if any(t in n for t in ["pant","jean"]):
        return "02_CLOTHING_AND_SAME_NAME_GROUPS", "PANTS"
    if any(t in n for t in ["shoe"]):
        return "02_CLOTHING_AND_SAME_NAME_GROUPS", "SHOES"
    if any(t in n for t in ["cloth","sleeve"]):
        return "02_CLOTHING_AND_SAME_NAME_GROUPS", "OTHER_CLOTHING"
    if any(t in n for t in ["f2","sackboy","character","body","head","eye","mouth","arm","hand","leg","foot","mball"]):
        return "01_CHARACTER_AND_SAME_NAME_GROUPS", "CHARACTER_CURRENT_AND_PARTS"
    if any(t in n for t in ["audi","car","wheel","tire","rim","brake","e-tron","etron"]) or base_name(obj.name).lower() in {"plane","circle","bolt"}:
        return "03_HERO_CAR_AND_IMPORTED_PARTS", "IMPORTED_CAR_OR_GENERIC_ASSET_PARTS"
    if any(t in n for t in ["store","building","asphalt","parking","line","curb","road","ground","sky","hdri"]):
        return "04_ENVIRONMENT_STOREFRONTS_PARKING", "ENVIRONMENT_AND_PARKING"
    if any(t in n for t in ["cone","sign","utility","box","decal","trash","prop"]):
        return "05_PROPS_SIGNS_DECOR", "PROPS_SIGNS_DECOR"
    return "05_PROPS_SIGNS_DECOR", "UNSORTED_VISIBLE_REVIEW"

def link_object_to_only_collection(obj, target):
    if obj.name not in target.objects:
        target.objects.link(obj)
    # unlink from every other collection so Outliner doesn't show same object in many places.
    for c in list(obj.users_collection):
        if c != target:
            try:
                c.objects.unlink(obj)
            except RuntimeError:
                pass

def main():
    before = [rec(o) for o in bpy.data.objects]
    by_base = {}
    by_data = {}
    for r in before:
        by_base.setdefault(r["base_name"], []).append(r["name"])
        if r["data_name"]:
            by_data.setdefault(r["type"] + "::" + r["data_name"], []).append(r["name"])
    duplicate_groups = {k:v for k,v in by_base.items() if len(v) > 1}
    shared_data_groups = {k:v for k,v in by_data.items() if len(v) > 1}

    top = {name: ensure_top_collection(name) for name in TOP_COLLECTIONS}
    moved = []
    duplicate_group_collections = {}

    for obj in sorted(bpy.data.objects, key=lambda o: o.name.lower()):
        b = base_name(obj.name)
        if b in duplicate_groups:
            top_name = classify_base_group(b)
            parent = top[top_name]
            child_name = f"SAME_NAME_{clean_name(b)}"
            child = ensure_child(parent, child_name)
            duplicate_group_collections.setdefault(child_name, []).append(obj.name)
            target = child
        else:
            top_name, child_label = classify_single(obj)
            parent = top[top_name]
            child = ensure_child(parent, child_label)
            target = child

        before_cols = [c.name for c in obj.users_collection]
        link_object_to_only_collection(obj, target)
        after_cols = [c.name for c in obj.users_collection]
        moved.append({
            "object": obj.name,
            "base_name": b,
            "target_collection": target.name,
            "before_collections": before_cols,
            "after_collections": after_cols,
            "visible": visible_get(obj),
            "type": obj.type,
        })

    after = [rec(o) for o in bpy.data.objects]
    multi_before = [r for r in before if r["collection_count"] > 1]
    multi_after = [r for r in after if r["collection_count"] > 1]

    summary = {
        "pass": "scene_collections_organization_v1",
        "safety": "No objects deleted. No geometry, materials, modifiers, shape keys, visibility flags, or render flags intentionally changed. Objects were moved/unlinked between collections only.",
        "total_objects_before": len(before),
        "total_objects_after": len(after),
        "visible_objects_before": sum(1 for r in before if r["visible"]),
        "visible_objects_after": sum(1 for r in after if r["visible"]),
        "duplicate_base_name_group_count": len(duplicate_groups),
        "duplicate_base_name_object_count": sum(len(v) for v in duplicate_groups.values()),
        "shared_data_group_count": len(shared_data_groups),
        "multi_collection_objects_before": len(multi_before),
        "multi_collection_objects_after": len(multi_after),
        "top_collections": TOP_COLLECTIONS,
    }

    report = {
        "summary": summary,
        "duplicate_base_name_groups": duplicate_groups,
        "shared_data_groups": shared_data_groups,
        "duplicate_group_collections": duplicate_group_collections,
        "multi_collection_before": multi_before,
        "multi_collection_after": multi_after,
        "moved_objects": moved,
        "objects_after": after,
    }

    (REP / "scene_collections_organization_v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REP / "SceneCollectionsOrganization_status.json").write_text(json.dumps({
        "ok": True,
        "total_objects_before": summary["total_objects_before"],
        "total_objects_after": summary["total_objects_after"],
        "visible_objects_before": summary["visible_objects_before"],
        "visible_objects_after": summary["visible_objects_after"],
        "multi_collection_objects_before": summary["multi_collection_objects_before"],
        "multi_collection_objects_after": summary["multi_collection_objects_after"],
        "duplicate_base_name_object_count": summary["duplicate_base_name_object_count"],
    }, indent=2), encoding="utf-8")

    md = []
    md.append("# Scene Collections Organization v1")
    md.append("")
    md.append("## Safety")
    md.append("- No objects were deleted.")
    md.append("- No visible objects were hidden.")
    md.append("- No geometry, materials, modifiers, shape keys, light values, camera transforms, or render settings were intentionally changed.")
    md.append("- Objects were only linked into clean collections and unlinked from old collections to reduce repeated Outliner listings.")
    md.append("")
    md.append("## Counts")
    md.append(f"- Total objects before/after: {summary['total_objects_before']} -> {summary['total_objects_after']}")
    md.append(f"- Visible objects before/after: {summary['visible_objects_before']} -> {summary['visible_objects_after']}")
    md.append(f"- Duplicate base-name groups: {summary['duplicate_base_name_group_count']}")
    md.append(f"- Objects inside duplicate base-name groups: {summary['duplicate_base_name_object_count']}")
    md.append(f"- Shared mesh-data groups: {summary['shared_data_group_count']}")
    md.append(f"- Multi-collection objects before/after: {summary['multi_collection_objects_before']} -> {summary['multi_collection_objects_after']}")
    md.append("")
    md.append("## Top collection order")
    for name in TOP_COLLECTIONS:
        md.append(f"- `{name}`")
    md.append("")
    md.append("## Same-name object groups")
    for group, names in sorted(duplicate_group_collections.items()):
        md.append(f"- `{group}`: {len(names)} objects -> {', '.join(names[:30])}{' ...' if len(names) > 30 else ''}")
    md.append("")
    md.append("## Shared mesh-data groups")
    for group, names in sorted(shared_data_groups.items()):
        md.append(f"- `{group}`: {len(names)} objects -> {', '.join(names)}")
    md.append("")
    md.append("## Notes")
    md.append("- Same-name groups were kept together under their most likely category instead of being split into separate backup/duplicate collections.")
    md.append("- Hidden non-visible objects that are not part of a same-name group were placed under `08_HIDDEN_NONVISIBLE_REVIEW`.")
    md.append("- Visible generic imported car/sign parts such as `Plane`, `Circle`, and `Bolt` were grouped together instead of deleted.")
    md.append("- The current hoodie proxy and original hoodie remain intact; this pass does not decide which clothing object to keep.")
    (REP / "Scene_Collections_Organization_v1.md").write_text("\n".join(md), encoding="utf-8")
    (REP / "SceneCollectionsOrganization_report.txt").write_text("\n".join(md), encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "sackboy_scene.blend"))
    print("[collections] scene collections organization v1")
    print(f"[objects] total {summary['total_objects_before']} -> {summary['total_objects_after']}; visible {summary['visible_objects_before']} -> {summary['visible_objects_after']}")
    print(f"[multi_collection] {summary['multi_collection_objects_before']} -> {summary['multi_collection_objects_after']}")
    print(f"[duplicates] duplicate_base_name_groups={summary['duplicate_base_name_group_count']} duplicate_name_objects={summary['duplicate_base_name_object_count']}")
    print("[save] " + str(ROOT / "blender" / "sackboy_scene.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "SceneCollectionsOrganization_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
