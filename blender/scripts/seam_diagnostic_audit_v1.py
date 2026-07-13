import bpy, json, csv, math, re, traceback
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
REP = ROOT / "reports" / "seam_diagnostic_audit_v1"
CSV_DIR = REP / "seam_zone_csv"
OBJ_DIR = REP / "seam_zone_obj"
OUT.mkdir(parents=True, exist_ok=True)
REP.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)
OBJ_DIR.mkdir(parents=True, exist_ok=True)

CAM_PREFIX = "SEAMDIAG_"
TMP_PREFIX = "TMP_SEAMDIAG_"

def visible_get(obj):
    try:
        return bool(obj.visible_get())
    except Exception:
        return not obj.hide_viewport

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")[:80] or "unnamed"

def find_hoodie():
    candidates = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not visible_get(o):
            continue
        n = o.name.lower()
        if any(t in n for t in ["hood", "hoodie", "pullover", "sweatshirt"]):
            candidates.append(o)
    candidates.sort(key=lambda o: len(o.data.polygons), reverse=True)
    if not candidates:
        raise RuntimeError("No visible hoodie/pullover/sweatshirt mesh candidate found.")
    return candidates[0], candidates

def bounds_world(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {
        "min": Vector((min(xs), min(ys), min(zs))),
        "max": Vector((max(xs), max(ys), max(zs))),
        "center": Vector(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2)),
        "dimensions": Vector((max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))),
    }

def remove_previous():
    removed = []
    for obj in list(bpy.data.objects):
        if obj.name.startswith(CAM_PREFIX) or obj.name.startswith(TMP_PREFIX):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    for mat in list(bpy.data.materials):
        if mat.name.startswith(TMP_PREFIX):
            bpy.data.materials.remove(mat, do_unlink=True)
    return removed

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def make_camera(name, loc, target, lens=80):
    cam_data = bpy.data.cameras.new(name + "_Data")
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.data.lens = lens
    cam.data.dof.use_dof = False
    look_at(cam, target)
    return cam

def make_mat(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat

def edge_faces(mesh):
    ef = {}
    for p in mesh.polygons:
        verts = list(p.vertices)
        for a,b in zip(verts, verts[1:] + verts[:1]):
            key = tuple(sorted((a,b)))
            ef[key] = ef.get(key, 0) + 1
    return ef

def boundary_edges_world(obj):
    mesh = obj.data
    ef = edge_faces(mesh)
    rows = []
    for a,b in ef.keys():
        if ef[(a,b)] != 1:
            continue
        va = obj.matrix_world @ mesh.vertices[a].co
        vb = obj.matrix_world @ mesh.vertices[b].co
        mid = (va + vb) * 0.5
        rows.append({"edge": (a,b), "a": va, "b": vb, "mid": mid, "length": (va-vb).length})
    return rows

def connected_components(obj):
    mesh = obj.data
    adj = {i:set() for i in range(len(mesh.vertices))}
    for e in mesh.edges:
        a,b = e.vertices
        adj[a].add(b); adj[b].add(a)
    seen=set(); comps=[]
    for i in range(len(mesh.vertices)):
        if i in seen: continue
        stack=[i]; seen.add(i); size=0
        while stack:
            cur=stack.pop(); size += 1
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        comps.append(size)
    comps.sort(reverse=True)
    return comps

def zone_predicates(b):
    mn=b["min"]; mx=b["max"]; c=b["center"]; d=b["dimensions"]
    h=max(d.z, 0.001); w=max(d.x, 0.001); dep=max(d.y, 0.001)
    return {
        "left_armpit": lambda p: (p.x < c.x - 0.18*w and mn.z + 0.25*h < p.z < mn.z + 0.70*h),
        "right_armpit": lambda p: (p.x > c.x + 0.18*w and mn.z + 0.25*h < p.z < mn.z + 0.70*h),
        "hood_collar_band": lambda p: (mn.z + 0.48*h < p.z < mn.z + 0.72*h and abs(p.x-c.x) < 0.52*w),
        "hood_top_center": lambda p: (p.z > mn.z + 0.68*h and abs(p.x-c.x) < 0.22*w),
        "all_boundary_edges": lambda p: True,
    }

def edge_rows_for_zone(edges, pred):
    return [e for e in edges if pred(e["mid"])]

def write_zone_csv(zone, rows):
    path = CSV_DIR / f"{zone}_boundary_edges.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        fields = ["edge_a","edge_b","mid_x","mid_y","mid_z","length"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "edge_a": r["edge"][0],
                "edge_b": r["edge"][1],
                "mid_x": round(r["mid"].x, 6),
                "mid_y": round(r["mid"].y, 6),
                "mid_z": round(r["mid"].z, 6),
                "length": round(r["length"], 6),
            })
    return str(path)

def write_zone_obj(zone, rows):
    path = OBJ_DIR / f"{zone}_boundary_edges.obj"
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Boundary/open-edge diagnostic OBJ for {zone}\n")
        idx = 1
        for r in rows:
            f.write(f"v {r['a'].x:.6f} {r['a'].y:.6f} {r['a'].z:.6f}\n")
            f.write(f"v {r['b'].x:.6f} {r['b'].y:.6f} {r['b'].z:.6f}\n")
            f.write(f"l {idx} {idx+1}\n")
            idx += 2
    return str(path)

def create_boundary_curves(zone_rows, mat, bevel=0.006):
    created=[]
    for zone, rows in zone_rows.items():
        curve = bpy.data.curves.new(TMP_PREFIX + safe_name(zone) + "_Curve", type="CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 1
        curve.bevel_depth = bevel
        curve.bevel_resolution = 1
        for r in rows:
            spl = curve.splines.new("POLY")
            spl.points.add(1)
            spl.points[0].co = (r["a"].x, r["a"].y, r["a"].z, 1)
            spl.points[1].co = (r["b"].x, r["b"].y, r["b"].z, 1)
        obj = bpy.data.objects.new(TMP_PREFIX + safe_name(zone), curve)
        bpy.context.scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
        created.append(obj)
    return created

def set_workbench(scene):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = True
    scene.display.shading.show_xray = False

def setup_res(scene):
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

def render_one(cam, filename):
    scene = bpy.context.scene
    setup_res(scene)
    set_workbench(scene)
    scene.camera = cam
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
    print("[render] " + filename)
    return {"filename": filename, "camera": cam.name, "mode": "solid_boundary_overlay"}

def main():
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()

    removed = remove_previous()
    hoodie, hoodie_candidates = find_hoodie()
    b = bounds_world(hoodie)
    mn=b["min"]; mx=b["max"]; c=b["center"]; d=b["dimensions"]
    r = max(d.x, d.y, d.z, 1.0)

    edges = boundary_edges_world(hoodie)
    preds = zone_predicates(b)
    zone_rows = {zone: edge_rows_for_zone(edges, pred) for zone, pred in preds.items()}
    # Render overlays for important zones, not every boundary edge.
    render_zone_rows = {z: zone_rows[z] for z in ["left_armpit", "right_armpit", "hood_collar_band", "hood_top_center"]}

    mat = make_mat(TMP_PREFIX + "BoundaryHighlight_Material", (1.0, 0.08, 0.02, 1.0))
    overlay_objs = create_boundary_curves(render_zone_rows, mat, bevel=max(r*0.0022, 0.003))

    cams = {
        "left_armpit": make_camera(CAM_PREFIX+"LEFT_ARMPIT_CLOSE", c + Vector((-r*1.25, -r*0.35, r*0.25)), c + Vector((-d.x*0.23, 0, 0)), 95),
        "right_armpit": make_camera(CAM_PREFIX+"RIGHT_ARMPIT_CLOSE", c + Vector((r*1.25, -r*0.35, r*0.25)), c + Vector((d.x*0.23, 0, 0)), 95),
        "hood_collar": make_camera(CAM_PREFIX+"HOOD_COLLAR_FRONT", c + Vector((0, -r*1.35, r*0.55)), c + Vector((0,0,r*0.22)), 95),
        "hood_top": make_camera(CAM_PREFIX+"HOOD_TOP_CENTER", c + Vector((0, -r*0.35, r*1.75)), c + Vector((0,0,r*0.35)), 85),
        "full_front": make_camera(CAM_PREFIX+"FULL_FRONT_CONTEXT", c + Vector((0, -r*2.0, r*0.35)), c, 55),
    }

    old = {
        "engine": bpy.context.scene.render.engine,
        "camera": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
        "filepath": bpy.context.scene.render.filepath,
        "res": (bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y, bpy.context.scene.render.resolution_percentage),
    }
    renders=[]
    try:
        renders.append(render_one(cams["full_front"], "01_SEAM_FullFront_BoundaryOverlay.png"))
        renders.append(render_one(cams["left_armpit"], "02_SEAM_LeftArmpit_BoundaryOverlay.png"))
        renders.append(render_one(cams["right_armpit"], "03_SEAM_RightArmpit_BoundaryOverlay.png"))
        renders.append(render_one(cams["hood_collar"], "04_SEAM_HoodCollar_BoundaryOverlay.png"))
        renders.append(render_one(cams["hood_top"], "05_SEAM_HoodTop_BoundaryOverlay.png"))
    finally:
        scene=bpy.context.scene
        scene.render.engine = old["engine"]
        if old["camera"] and bpy.data.objects.get(old["camera"]):
            scene.camera = bpy.data.objects[old["camera"]]
        scene.render.filepath = old["filepath"]
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old["res"]

    zone_exports={}
    for zone, rows in zone_rows.items():
        zone_exports[zone] = {
            "boundary_edge_count": len(rows),
            "csv": write_zone_csv(zone, rows),
            "obj": write_zone_obj(zone, rows),
            "total_boundary_length": round(sum(x["length"] for x in rows), 6),
            "mean_boundary_length": round((sum(x["length"] for x in rows) / len(rows)) if rows else 0.0, 6),
        }

    # remove temporary overlay curves before saving; keep seam cameras.
    for obj in overlay_objs:
        bpy.data.objects.remove(obj, do_unlink=True)
    if mat.name in bpy.data.materials:
        bpy.data.materials.remove(mat, do_unlink=True)

    comps = connected_components(hoodie)
    mesh_diag = {
        "object": hoodie.name,
        "vertices": len(hoodie.data.vertices),
        "edges": len(hoodie.data.edges),
        "faces": len(hoodie.data.polygons),
        "boundary_edge_count_total": len(edges),
        "connected_vertex_island_count": len(comps),
        "connected_vertex_island_sizes_top_30": comps[:30],
        "interpretation": "Open/boundary edges are expected at cuffs, hem, hood opening, and garment openings; seam breaks show up as unexpected boundary edges in armpit/collar/top-hood zones."
    }

    summary = {
        "pass": "seam_diagnostic_audit_v1",
        "safety": "Diagnostic only. Deletes prior SEAMDIAG_* cameras/TMP_SEAMDIAG_* objects, creates fresh seam cameras, temporarily renders boundary overlays, removes temporary overlay objects before save, and does not edit hoodie geometry.",
        "hoodie_object": hoodie.name,
        "hoodie_candidates": [o.name for o in hoodie_candidates],
        "removed_previous_seam_diag_objects": removed,
        "created_seam_cameras": [cam.name for cam in cams.values()],
        "mesh_diagnostics": mesh_diag,
        "zone_exports": zone_exports,
        "renders": renders,
    }
    report = {
        "summary": summary,
    }
    (REP / "seam_diagnostic_audit_v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REP / "SeamDiagnosticAudit_status.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md=[
        "# Seam Diagnostic Audit v1",
        "",
        "## Safety",
        "- Diagnostic only.",
        "- Deleted only previous `SEAMDIAG_*` cameras and `TMP_SEAMDIAG_*` temporary objects.",
        "- Created fresh seam diagnostic cameras.",
        "- Temporarily rendered boundary-edge overlays, then removed overlay objects before saving.",
        "- Did not edit hoodie mesh geometry, smoothing, shrinkwrap, materials, shape keys, lights, car, or environment.",
        "",
        "## Hoodie target",
        f"- `{hoodie.name}`",
        "",
        "## Mesh diagnostics",
        f"- vertices: {mesh_diag['vertices']}",
        f"- edges: {mesh_diag['edges']}",
        f"- faces: {mesh_diag['faces']}",
        f"- total boundary/open edges: {mesh_diag['boundary_edge_count_total']}",
        f"- connected vertex islands: {mesh_diag['connected_vertex_island_count']}",
        f"- largest island sizes: {mesh_diag['connected_vertex_island_sizes_top_30'][:10]}",
        "",
        "## Seam zone boundary/open-edge counts",
    ]
    for zone, info in zone_exports.items():
        md.append(f"- `{zone}`: boundary_edges={info['boundary_edge_count']}, total_length={info['total_boundary_length']}, mean_length={info['mean_boundary_length']}")
    md += [
        "",
        "## Created seam cameras",
    ]
    for cam in cams.values():
        md.append(f"- `{cam.name}`")
    md += ["", "## Renders"]
    for rr in renders:
        md.append(f"- `{rr['filename']}` camera=`{rr['camera']}`")
    md += ["", "## Repair guidance for next pass", "- Do not broad-smooth the armpit or hood top seam areas.", "- Use local seam-border repositioning, bridge/fill, or merge-by-distance only after reviewing these zone overlays.", "- Sleeve/armpit zones should be fixed locally before any cloth simulation."]
    text="\n".join(md)
    (REP / "Seam_Diagnostic_Audit_v1.md").write_text(text, encoding="utf-8")
    (REP / "SeamDiagnosticAudit_report.txt").write_text(text, encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "sackboy_scene.blend"))
    print("[seam_diag] seam diagnostic audit v1")
    print(f"[hoodie] {hoodie.name}")
    print(f"[boundary] total={len(edges)} left={len(zone_rows['left_armpit'])} right={len(zone_rows['right_armpit'])} collar={len(zone_rows['hood_collar_band'])} hood_top={len(zone_rows['hood_top_center'])}")
    print(f"[islands] {len(comps)} top={comps[:8]}")
    print(f"[cameras] removed={len(removed)} created={len(cams)}")
    print("[save] " + str(ROOT / "blender" / "sackboy_scene.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP / "SeamDiagnosticAudit_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
