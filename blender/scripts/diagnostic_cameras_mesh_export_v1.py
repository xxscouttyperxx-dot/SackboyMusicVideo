import bpy, json, csv, math, traceback, re
from pathlib import Path
from mathutils import Vector

def find_root():
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "blender" / "sackboy_scene.blend").exists():
            return parent
    return Path(__file__).resolve().parents[3]

ROOT = find_root()
OUT = ROOT / "renders" / "current_review"
REP = ROOT / "reports" / "diagnostic_cameras_mesh_export_v1"
MESH_OUT = REP / "targeted_mesh_exports"
OUT.mkdir(parents=True, exist_ok=True)
REP.mkdir(parents=True, exist_ok=True)
MESH_OUT.mkdir(parents=True, exist_ok=True)

DIAG_PREFIX = "DIAG_CURRENT_"

def visible_get(obj):
    try:
        return bool(obj.visible_get())
    except Exception:
        return not obj.hide_viewport

def strip_suffix(name):
    return re.sub(r"\.\d{3,}$", "", name)

def bounds_world(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {
        "min": Vector((min(xs), min(ys), min(zs))),
        "max": Vector((max(xs), max(ys), max(zs))),
        "center": Vector(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2)),
        "dimensions": Vector((max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))),
    }

def bounds_for_objects(objs):
    coords = []
    for obj in objs:
        if not hasattr(obj, "bound_box"): continue
        coords += [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    if not coords:
        return {"min": Vector((0,0,0)), "max": Vector((0,0,0)), "center": Vector((0,0,0)), "dimensions": Vector((1,1,1))}
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {
        "min": Vector((min(xs), min(ys), min(zs))),
        "max": Vector((max(xs), max(ys), max(zs))),
        "center": Vector(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2)),
        "dimensions": Vector((max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))),
    }

def obj_record(obj):
    data = getattr(obj, "data", None)
    return {
        "name": obj.name,
        "base_name": strip_suffix(obj.name),
        "type": obj.type,
        "visible": visible_get(obj),
        "hide_viewport": bool(obj.hide_viewport),
        "hide_render": bool(obj.hide_render),
        "hide_select": bool(obj.hide_select),
        "collections": [c.name for c in obj.users_collection],
        "data_name": data.name if data else None,
        "data_users": int(getattr(data, "users", 0)) if data else 0,
        "vertices": len(data.vertices) if obj.type == "MESH" and data else 0,
        "faces": len(data.polygons) if obj.type == "MESH" and data else 0,
        "modifiers": [{"name": m.name, "type": m.type, "show_viewport": bool(m.show_viewport), "show_render": bool(m.show_render)} for m in getattr(obj, "modifiers", [])],
        "bounds_world": None if obj.type != "MESH" else {
            "min": [round(v, 6) for v in bounds_world(obj)["min"]],
            "max": [round(v, 6) for v in bounds_world(obj)["max"]],
            "center": [round(v, 6) for v in bounds_world(obj)["center"]],
            "dimensions": [round(v, 6) for v in bounds_world(obj)["dimensions"]],
        }
    }

def choose_targets():
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and visible_get(o)]
    hoodie = [o for o in meshes if any(t in o.name.lower() for t in ["hood", "hoodie", "pullover", "sweatshirt"])]
    hoodie.sort(key=lambda o: len(o.data.polygons), reverse=True)

    clothing = [o for o in meshes if any(t in o.name.lower() for t in ["hood", "hoodie", "pullover", "sweatshirt", "pant", "jean", "shoe", "sleeve"])]
    clothing.sort(key=lambda o: len(o.data.polygons), reverse=True)

    chars = [o for o in meshes if any(t in o.name.lower() for t in ["f2", "sackboy", "body", "head", "eye", "mouth", "arm", "hand", "leg", "foot", "mball"])]
    chars.sort(key=lambda o: len(o.data.polygons), reverse=True)

    body = None
    for o in chars:
        if o.name.lower().startswith("f2") or "sackboy" in o.name.lower() or "body" in o.name.lower():
            body = o
            break
    if body is None and chars:
        body = chars[0]

    return {
        "hoodie": hoodie[0] if hoodie else None,
        "body": body,
        "clothing": clothing,
        "character": chars,
    }

def remove_old_diag_cameras():
    removed = []
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA" and obj.name.startswith(DIAG_PREFIX):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed

def look_at(obj, target):
    direction = target - obj.location
    quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = quat.to_euler()

def make_camera(name, loc, target, lens=55):
    cam_data = bpy.data.cameras.new(name + "_Data")
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.data.lens = lens
    cam.data.dof.use_dof = False
    look_at(cam, target)
    return cam

def set_workbench(scene):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = True
    scene.display.shading.show_xray = False

def set_cycles(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 80
    scene.cycles.preview_samples = 24
    scene.cycles.use_denoising = True

def setup_res(scene):
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

def render_one(cam, filename, mode):
    scene = bpy.context.scene
    setup_res(scene)
    scene.camera = cam
    if mode == "rendered":
        set_cycles(scene)
    else:
        set_workbench(scene)
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
    print(f"[render] {filename}")
    return {"filename": filename, "camera": cam.name, "mode": mode}

def write_obj(obj, path):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph)
    mesh.transform(obj.matrix_world)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Exported diagnostic mesh for {obj.name}\n")
        f.write(f"o {obj.name}\n")
        for v in mesh.vertices:
            f.write(f"v {v.co.x:.6f} {v.co.y:.6f} {v.co.z:.6f}\n")
        for poly in mesh.polygons:
            idxs = " ".join(str(i+1) for i in poly.vertices)
            f.write(f"f {idxs}\n")
    count = {"object": obj.name, "path": str(path), "vertices": len(mesh.vertices), "faces": len(mesh.polygons)}
    bpy.data.meshes.remove(mesh)
    return count

def mesh_diagnostics(obj):
    data = obj.data
    edge_faces = {}
    for poly in data.polygons:
        verts = list(poly.vertices)
        for a,b in zip(verts, verts[1:] + verts[:1]):
            key = tuple(sorted((a,b)))
            edge_faces.setdefault(key, 0)
            edge_faces[key] += 1
    boundary_edges = [e for e,c in edge_faces.items() if c == 1]
    nonmanifold_edges = [e for e,c in edge_faces.items() if c != 2]
    verts_boundary = set()
    for a,b in boundary_edges:
        verts_boundary.add(a); verts_boundary.add(b)

    # connected components by vertices/faces
    adj = {i:set() for i in range(len(data.vertices))}
    for e in data.edges:
        a,b = e.vertices
        adj[a].add(b); adj[b].add(a)
    seen=set(); comp_sizes=[]
    for i in range(len(data.vertices)):
        if i in seen: continue
        stack=[i]; seen.add(i); size=0
        while stack:
            cur=stack.pop(); size+=1
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        comp_sizes.append(size)
    comp_sizes.sort(reverse=True)

    return {
        "object": obj.name,
        "vertices": len(data.vertices),
        "edges": len(data.edges),
        "faces": len(data.polygons),
        "boundary_edge_count": len(boundary_edges),
        "boundary_vertex_count": len(verts_boundary),
        "nonmanifold_edge_count": len(nonmanifold_edges),
        "connected_vertex_island_count": len(comp_sizes),
        "connected_vertex_island_sizes_top_20": comp_sizes[:20],
        "note": "Boundary/open edges can be normal at cuffs/hood opening/bottom hem; high counts or many islands suggest separated panels/seams needing inspection."
    }

def csv_rows(path, rows):
    if not rows: return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k,v in r.items()})

def main():
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()

    removed_cams = remove_old_diag_cameras()
    targets = choose_targets()
    hoodie = targets["hoodie"]
    body = targets["body"]
    focus_objs = [o for o in [hoodie, body] if o is not None] + targets["clothing"][:4]
    focus_objs = list(dict((o.name,o) for o in focus_objs).values())
    b = bounds_for_objects(focus_objs if focus_objs else [o for o in bpy.data.objects if o.type=="MESH" and visible_get(o)])
    c = b["center"]; d = b["dimensions"]
    radius = max(d.x, d.y, d.z, 1.0)

    cameras = [
        make_camera(DIAG_PREFIX+"FULL_FRONT", c + Vector((0, -radius*2.2, radius*0.35)), c, 55),
        make_camera(DIAG_PREFIX+"FULL_3Q", c + Vector((radius*1.55, -radius*1.8, radius*0.55)), c, 55),
        make_camera(DIAG_PREFIX+"LEFT_ARMPIT", c + Vector((-radius*1.4, -radius*0.35, radius*0.25)), c + Vector((0,0,radius*0.05)), 75),
        make_camera(DIAG_PREFIX+"RIGHT_ARMPIT", c + Vector((radius*1.4, -radius*0.35, radius*0.25)), c + Vector((0,0,radius*0.05)), 75),
        make_camera(DIAG_PREFIX+"HOOD_TOP", c + Vector((0, -radius*0.35, radius*2.0)), c + Vector((0,0,radius*0.2)), 70),
    ]

    old = {
        "engine": bpy.context.scene.render.engine,
        "camera": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
        "filepath": bpy.context.scene.render.filepath,
        "res": (bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y, bpy.context.scene.render.resolution_percentage),
    }
    renders=[]
    try:
        render_specs = [
            (cameras[0], "01_DIAG_FullFront_SOLID.png", "solid"),
            (cameras[1], "02_DIAG_Full3Q_SOLID.png", "solid"),
            (cameras[1], "03_DIAG_Full3Q_RENDERED.png", "rendered"),
            (cameras[2], "04_DIAG_LeftArmpit_SOLID.png", "solid"),
            (cameras[3], "05_DIAG_RightArmpit_SOLID.png", "solid"),
            (cameras[4], "06_DIAG_HoodTop_SOLID.png", "solid"),
        ]
        for cam, fn, mode in render_specs:
            renders.append(render_one(cam, fn, mode))
    finally:
        scene = bpy.context.scene
        scene.render.engine = old["engine"]
        if old["camera"] and bpy.data.objects.get(old["camera"]):
            scene.camera = bpy.data.objects[old["camera"]]
        scene.render.filepath = old["filepath"]
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old["res"]

    exports=[]
    for label, obj in [("current_hoodie", hoodie), ("current_body", body)]:
        if obj:
            exports.append(write_obj(obj, MESH_OUT / f"{label}_{re.sub(r'[^A-Za-z0-9_]+','_',obj.name)}.obj"))
    for i, obj in enumerate(targets["clothing"][:4], start=1):
        if obj not in [hoodie, body]:
            exports.append(write_obj(obj, MESH_OUT / f"clothing_{i}_{re.sub(r'[^A-Za-z0-9_]+','_',obj.name)}.obj"))

    diag = []
    for obj in [o for o in [hoodie, body] if o is not None] + targets["clothing"][:4]:
        if obj and obj.type == "MESH":
            if obj.name not in [d["object"] for d in diag]:
                diag.append(mesh_diagnostics(obj))

    all_objects = [obj_record(o) for o in sorted(bpy.data.objects, key=lambda x: x.name.lower())]
    by_base={}
    by_data={}
    for r in all_objects:
        by_base.setdefault(strip_suffix(r["name"]), []).append(r["name"])
        if r["data_name"]:
            by_data.setdefault(r["type"]+"::"+r["data_name"], []).append(r["name"])
    dup_groups = {k:v for k,v in sorted(by_base.items()) if len(v)>1}
    shared_data = {k:v for k,v in sorted(by_data.items()) if len(v)>1}

    summary = {
        "pass": "diagnostic_cameras_mesh_export_v1",
        "safety": "Creates fresh DIAG_CURRENT_* cameras after deleting older DIAG_CURRENT_* cameras. Exports targeted OBJ diagnostics. Renders current_review. Does not change mesh geometry/materials/lights/world. Saves blend locally only so diagnostic cameras remain available.",
        "removed_previous_diag_cameras": removed_cams,
        "created_diag_cameras": [c.name for c in cameras],
        "total_objects": len(bpy.data.objects),
        "visible_objects": sum(1 for o in bpy.data.objects if visible_get(o)),
        "hidden_objects": sum(1 for o in bpy.data.objects if not visible_get(o)),
        "duplicate_base_name_groups": len(dup_groups),
        "duplicate_base_name_object_count": sum(len(v) for v in dup_groups.values()),
        "shared_data_groups": len(shared_data),
        "current_hoodie": obj_record(hoodie) if hoodie else None,
        "current_body": obj_record(body) if body else None,
        "clothing_candidates": [obj_record(o) for o in targets["clothing"]],
        "character_candidates": [obj_record(o) for o in targets["character"]],
        "mesh_exports": exports,
        "mesh_diagnostics": diag,
        "renders": renders,
    }

    report = {
        "summary": summary,
        "duplicate_base_name_groups": dup_groups,
        "shared_data_groups": shared_data,
        "all_objects": all_objects,
    }

    (REP / "diagnostic_cameras_mesh_export_v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REP / "DiagnosticCamerasMeshExport_status.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    csv_rows(REP / "mesh_diagnostics.csv", diag)
    csv_rows(REP / "mesh_exports.csv", exports)
    csv_rows(REP / "all_objects.csv", all_objects)

    md = ["# Diagnostic Cameras + Mesh Export v1", "", "## Safety", "- Deleted only previous `DIAG_CURRENT_*` diagnostic cameras.", "- Created fresh `DIAG_CURRENT_*` cameras aimed at the current visible character/clothing baseline.", "- Exported targeted OBJ diagnostics for current hoodie/body/clothing candidates.", "- Did not edit mesh geometry, materials, shape keys, modifiers, lights, world, car, or environment.", "- Saved the blend locally so diagnostic cameras remain available.", "", "## Counts"]
    for k in ["total_objects","visible_objects","hidden_objects","duplicate_base_name_groups","duplicate_base_name_object_count","shared_data_groups"]:
        md.append(f"- {k}: {summary[k]}")
    md += ["", "## Current targets"]
    md.append(f"- Current hoodie: `{hoodie.name if hoodie else 'NOT FOUND'}`")
    md.append(f"- Current body: `{body.name if body else 'NOT FOUND'}`")
    md += ["", "## Removed old diagnostic cameras"]
    md.append(", ".join(removed_cams) if removed_cams else "- None")
    md += ["", "## Created diagnostic cameras"]
    for ccam in cameras:
        md.append(f"- `{ccam.name}`")
    md += ["", "## Mesh diagnostics"]
    for ddd in diag:
        md.append(f"- `{ddd['object']}`: boundary_edges={ddd['boundary_edge_count']}, boundary_vertices={ddd['boundary_vertex_count']}, nonmanifold_edges={ddd['nonmanifold_edge_count']}, islands={ddd['connected_vertex_island_count']}, top_islands={ddd['connected_vertex_island_sizes_top_20'][:5]}")
    md += ["", "## Exports"]
    for e in exports:
        md.append(f"- `{Path(e['path']).name}` verts={e['vertices']} faces={e['faces']}")
    md += ["", "## Renders"]
    for r in renders:
        md.append(f"- `{r['filename']}` camera=`{r['camera']}` mode={r['mode']}")
    md += ["", "## Next recommendation", "- Use the mesh diagnostics and current renders to choose a seam-repair pass, not broad smoothing.", "- Sleeve/armpit seam repair should use local seam-border repositioning/merge or bridge repair before any cloth simulation."]
    text = "\n".join(md)
    (REP / "Diagnostic_Cameras_Mesh_Export_v1.md").write_text(text, encoding="utf-8")
    (REP / "DiagnosticCamerasMeshExport_report.txt").write_text(text, encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "sackboy_scene.blend"))
    print("[diag] diagnostic cameras mesh export v1")
    print(f"[targets] hoodie={hoodie.name if hoodie else 'NONE'} body={body.name if body else 'NONE'} clothing={len(targets['clothing'])} character={len(targets['character'])}")
    print(f"[cameras] removed={len(removed_cams)} created={len(cameras)}")
    print(f"[exports] {len(exports)} OBJ files")
    print(f"[counts] total={summary['total_objects']} visible={summary['visible_objects']} hidden={summary['hidden_objects']} duplicates={summary['duplicate_base_name_groups']} shared_data={summary['shared_data_groups']}")
    print("[save] " + str(ROOT / "blender" / "sackboy_scene.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "DiagnosticCamerasMeshExport_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
