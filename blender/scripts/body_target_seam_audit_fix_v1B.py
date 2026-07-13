import bpy, json, csv, math, re, traceback
from pathlib import Path
from mathutils import Vector

ROOT = None
def find_root():
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "blender" / "sackboy_scene.blend").exists():
            return parent
    return Path(__file__).resolve().parents[3]

ROOT = find_root()
OUT = ROOT / "renders" / "current_review"
REP = ROOT / "reports" / "body_target_seam_audit_fix_v1B"
OBJ_DIR = REP / "targeted_mesh_exports"
CSV_DIR = REP / "seam_zone_csv"
OUT.mkdir(parents=True, exist_ok=True)
REP.mkdir(parents=True, exist_ok=True)
OBJ_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)

CAM_PREFIX = "SEAMDIAG_"
TMP_PREFIX = "TMP_SEAMDIAG_"

CLOTHING_TERMS = ["hood", "hoodie", "pullover", "sweatshirt", "cloth", "sleeve", "pant", "jean", "shoe", "boot"]
BODY_PREFERRED = ["f2", "sackboy_body", "sackboy", "body"]

def visible_get(obj):
    try:
        return bool(obj.visible_get())
    except Exception:
        return not obj.hide_viewport

def safe(s):
    return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")[:80] or "unnamed"

def is_clothing(obj):
    n = obj.name.lower()
    return any(t in n for t in CLOTHING_TERMS)

def find_hoodie():
    cand = [o for o in bpy.data.objects if o.type=="MESH" and visible_get(o) and any(t in o.name.lower() for t in ["hood","hoodie","pullover","sweatshirt"])]
    cand.sort(key=lambda o: len(o.data.polygons), reverse=True)
    if not cand:
        raise RuntimeError("No visible hoodie mesh found.")
    return cand[0], cand

def find_body():
    meshes = [o for o in bpy.data.objects if o.type=="MESH" and visible_get(o)]
    # exact F2 is the safest body target in this project
    for o in meshes:
        if o.name == "F2":
            return o, "exact_visible_F2"
    # base F2 variant
    for o in meshes:
        if re.sub(r"\.\d{3,}$", "", o.name) == "F2" and not is_clothing(o):
            return o, "base_visible_F2"
    # name preference but exclude clothing/environment obvious props
    body_cand = []
    for o in meshes:
        n = o.name.lower()
        if is_clothing(o): 
            continue
        if any(t in n for t in BODY_PREFERRED):
            body_cand.append(o)
    body_cand.sort(key=lambda o: len(o.data.polygons), reverse=True)
    if body_cand:
        return body_cand[0], "preferred_nonclothing_name"
    # fallback largest nonclothing mesh under Main Model collection if possible
    mm = []
    for o in meshes:
        if is_clothing(o):
            continue
        if any(c.name.lower() == "main model" for c in o.users_collection):
            mm.append(o)
    mm.sort(key=lambda o: len(o.data.polygons), reverse=True)
    if mm:
        return mm[0], "largest_nonclothing_main_model"
    raise RuntimeError("No visible non-clothing Sackboy body target found.")

def bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min":Vector((min(xs),min(ys),min(zs))),"max":Vector((max(xs),max(ys),max(zs))),"center":Vector(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2)),"dim":Vector((max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs)))}

def remove_old():
    removed=[]
    for o in list(bpy.data.objects):
        if o.name.startswith(CAM_PREFIX) or o.name.startswith(TMP_PREFIX):
            removed.append(o.name); bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.materials):
        if m.name.startswith(TMP_PREFIX):
            bpy.data.materials.remove(m, do_unlink=True)
    return removed

def look_at(obj, target):
    obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()

def camera(name, loc, target, lens=90):
    data=bpy.data.cameras.new(name+"_Data")
    obj=bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location=loc
    obj.data.lens=lens
    obj.data.dof.use_dof=False
    look_at(obj, target)
    return obj

def edge_faces(mesh):
    ef={}
    for p in mesh.polygons:
        vs=list(p.vertices)
        for a,b in zip(vs, vs[1:]+vs[:1]):
            key=tuple(sorted((a,b))); ef[key]=ef.get(key,0)+1
    return ef

def boundary_edges_world(obj):
    mesh=obj.data; ef=edge_faces(mesh)
    rows=[]
    for (a,b), count in ef.items():
        if count != 1: continue
        va=obj.matrix_world @ mesh.vertices[a].co
        vb=obj.matrix_world @ mesh.vertices[b].co
        mid=(va+vb)*0.5
        rows.append({"edge":(a,b),"a":va,"b":vb,"mid":mid,"length":(va-vb).length})
    return rows

def closest_edges(edges, anchor, max_count=160, radius=None):
    scored=[]
    for e in edges:
        dist=(e["mid"]-anchor).length
        if radius is not None and dist > radius:
            continue
        scored.append((dist,e))
    scored.sort(key=lambda x:x[0])
    return [e for _,e in scored[:max_count]]

def mat(name, color):
    m=bpy.data.materials.new(name); m.diffuse_color=color; return m

def make_overlay(zone_rows, material, bevel):
    objs=[]
    for zone, rows in zone_rows.items():
        curve=bpy.data.curves.new(TMP_PREFIX+safe(zone)+"_Curve","CURVE")
        curve.dimensions="3D"; curve.resolution_u=1; curve.bevel_depth=bevel; curve.bevel_resolution=1
        for r in rows:
            s=curve.splines.new("POLY"); s.points.add(1)
            s.points[0].co=(r["a"].x,r["a"].y,r["a"].z,1); s.points[1].co=(r["b"].x,r["b"].y,r["b"].z,1)
        obj=bpy.data.objects.new(TMP_PREFIX+safe(zone), curve)
        bpy.context.scene.collection.objects.link(obj); obj.data.materials.append(material); objs.append(obj)
    return objs

def set_workbench(scene):
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_cavity=True
    scene.display.shading.show_object_outline=True
    scene.display.shading.show_xray=False

def render(cam, fn):
    scene=bpy.context.scene
    scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    set_workbench(scene)
    scene.camera=cam
    scene.render.filepath=str(OUT/fn)
    bpy.ops.render.render(write_still=True)
    print("[render] "+fn)
    return {"filename":fn,"camera":cam.name,"mode":"solid_boundary_overlay"}

def export_obj(obj, path):
    deps=bpy.context.evaluated_depsgraph_get()
    eo=obj.evaluated_get(deps)
    mesh=bpy.data.meshes.new_from_object(eo, depsgraph=deps)
    mesh.transform(obj.matrix_world)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Diagnostic export for {obj.name}\n")
        f.write(f"o {obj.name}\n")
        for v in mesh.vertices:
            f.write(f"v {v.co.x:.6f} {v.co.y:.6f} {v.co.z:.6f}\n")
        for p in mesh.polygons:
            f.write("f "+" ".join(str(i+1) for i in p.vertices)+"\n")
    out={"object":obj.name,"path":str(path),"vertices":len(mesh.vertices),"faces":len(mesh.polygons)}
    bpy.data.meshes.remove(mesh)
    return out

def connected_components(obj):
    mesh=obj.data
    adj={i:set() for i in range(len(mesh.vertices))}
    for e in mesh.edges:
        a,b=e.vertices; adj[a].add(b); adj[b].add(a)
    seen=set(); sizes=[]
    for i in range(len(mesh.vertices)):
        if i in seen: continue
        stack=[i]; seen.add(i); n=0
        while stack:
            cur=stack.pop(); n+=1
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        sizes.append(n)
    sizes.sort(reverse=True)
    return sizes

def write_zone(zone, rows):
    csvp=CSV_DIR/(zone+"_edges.csv")
    with csvp.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["edge_a","edge_b","mid_x","mid_y","mid_z","length"])
        w.writeheader()
        for r in rows:
            w.writerow({"edge_a":r["edge"][0],"edge_b":r["edge"][1],"mid_x":round(r["mid"].x,6),"mid_y":round(r["mid"].y,6),"mid_z":round(r["mid"].z,6),"length":round(r["length"],6)})
    objp=OBJ_DIR/(zone+"_edges.obj")
    with objp.open("w", encoding="utf-8") as f:
        f.write(f"# Edge lines for {zone}\n")
        idx=1
        for r in rows:
            f.write(f"v {r['a'].x:.6f} {r['a'].y:.6f} {r['a'].z:.6f}\n")
            f.write(f"v {r['b'].x:.6f} {r['b'].y:.6f} {r['b'].z:.6f}\n")
            f.write(f"l {idx} {idx+1}\n"); idx+=2
    return {"csv":str(csvp),"obj":str(objp)}

def main():
    for p in OUT.glob("*"):
        if p.is_file(): p.unlink()
    removed=remove_old()
    hoodie, hoodie_candidates=find_hoodie()
    body, body_method=find_body()

    hb=bounds(hoodie); c=hb["center"]; d=hb["dim"]; r=max(d.x,d.y,d.z,1.0)
    edges=boundary_edges_world(hoodie)

    anchors={
        "left_armpit": c + Vector((-d.x*0.42, 0, -d.z*0.10)),
        "right_armpit": c + Vector((d.x*0.42, 0, -d.z*0.10)),
        "hood_collar_front": c + Vector((0, -d.y*0.40, d.z*0.04)),
        "hood_collar_back": c + Vector((0, d.y*0.35, d.z*0.04)),
        "hood_top_center": c + Vector((0, 0, d.z*0.38)),
    }
    zone_rows={}
    for z,a in anchors.items():
        # Use nearest open edges so we still get evidence even when broad box predicates miss collar/top.
        zone_rows[z]=closest_edges(edges, a, max_count=180, radius=r*0.75)

    material=mat(TMP_PREFIX+"BoundaryHighlight",(1.0,0.05,0.02,1.0))
    overlays=make_overlay(zone_rows, material, max(r*0.002,0.003))

    cams={
        "full":camera(CAM_PREFIX+"V1B_FULL_CONTEXT", c+Vector((0,-r*2.0,r*0.35)), c, 55),
        "left":camera(CAM_PREFIX+"V1B_LEFT_ARMPIT", c+Vector((-r*1.3,-r*0.35,r*0.25)), anchors["left_armpit"], 100),
        "right":camera(CAM_PREFIX+"V1B_RIGHT_ARMPIT", c+Vector((r*1.3,-r*0.35,r*0.25)), anchors["right_armpit"], 100),
        "collar":camera(CAM_PREFIX+"V1B_HOOD_COLLAR", c+Vector((0,-r*1.25,r*0.55)), anchors["hood_collar_front"], 100),
        "top":camera(CAM_PREFIX+"V1B_HOOD_TOP", c+Vector((0,-r*0.32,r*1.75)), anchors["hood_top_center"], 90),
    }
    old={"engine":bpy.context.scene.render.engine,"camera":bpy.context.scene.camera.name if bpy.context.scene.camera else None,"filepath":bpy.context.scene.render.filepath}
    renders=[]
    try:
        renders += [
            render(cams["full"],"01_V1B_FullContext_SeamOverlay.png"),
            render(cams["left"],"02_V1B_LeftArmpit_SeamOverlay.png"),
            render(cams["right"],"03_V1B_RightArmpit_SeamOverlay.png"),
            render(cams["collar"],"04_V1B_HoodCollar_SeamOverlay.png"),
            render(cams["top"],"05_V1B_HoodTop_SeamOverlay.png"),
        ]
    finally:
        bpy.context.scene.render.engine=old["engine"]
        if old["camera"] and bpy.data.objects.get(old["camera"]):
            bpy.context.scene.camera=bpy.data.objects[old["camera"]]
        bpy.context.scene.render.filepath=old["filepath"]

    zone_exports={}
    for z,rows in zone_rows.items():
        files=write_zone(z, rows)
        zone_exports[z]={"edge_count":len(rows),"total_length":round(sum(e["length"] for e in rows),6),**files}

    exports=[
        export_obj(hoodie, OBJ_DIR/("current_hoodie_"+safe(hoodie.name)+".obj")),
        export_obj(body, OBJ_DIR/("current_body_"+safe(body.name)+".obj")),
    ]

    # remove temporary overlays only; keep cameras
    for o in overlays: bpy.data.objects.remove(o, do_unlink=True)
    if material.name in bpy.data.materials: bpy.data.materials.remove(material, do_unlink=True)

    comps=connected_components(hoodie)
    summary={
        "pass":"body_target_seam_audit_fix_v1B",
        "safety":"Diagnostic correction pass. Fixes body target selection, improves seam zone selection, deletes old SEAMDIAG/TMP objects only, renders overlays, removes temporary overlays, saves local blend to keep cameras.",
        "hoodie_object":hoodie.name,
        "hoodie_candidates":[o.name for o in hoodie_candidates],
        "body_object":body.name,
        "body_selection_method":body_method,
        "removed_previous_diag_objects":removed,
        "created_cameras":[c.name for c in cams.values()],
        "hoodie_vertices":len(hoodie.data.vertices),
        "hoodie_faces":len(hoodie.data.polygons),
        "hoodie_boundary_edges_total":len(edges),
        "hoodie_island_count":len(comps),
        "hoodie_top_island_sizes":comps[:20],
        "zone_exports":zone_exports,
        "mesh_exports":exports,
        "renders":renders,
    }
    (REP/"BodyTargetSeamAuditFix_status.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (REP/"body_target_seam_audit_fix_v1B.json").write_text(json.dumps({"summary":summary}, indent=2), encoding="utf-8")
    md=[
        "# Body Target + Seam Audit Fix v1B",
        "",
        "## Why",
        "- The previous diagnostic pass selected the hoodie as both hoodie and body because the hoodie name contains `SACKBOY`.",
        "- This pass explicitly selects visible `F2` as the current body target when available.",
        "- It also uses nearest-boundary-edge seam zones so collar/top hood zones are not reported as zero merely because a bounding-box heuristic missed them.",
        "",
        "## Safety",
        "- No seam repair.",
        "- No smoothing/shrinkwrap/welding/bridging.",
        "- Deletes only previous `SEAMDIAG_*` and `TMP_SEAMDIAG_*` diagnostic objects.",
        "- Temporary overlays are removed before save.",
        "",
        "## Targets",
        f"- Hoodie: `{hoodie.name}`",
        f"- Body: `{body.name}` selected by `{body_method}`",
        "",
        "## Hoodie mesh",
        f"- vertices: {len(hoodie.data.vertices)}",
        f"- faces: {len(hoodie.data.polygons)}",
        f"- boundary edges total: {len(edges)}",
        f"- vertex islands: {len(comps)}",
        f"- top island sizes: {comps[:10]}",
        "",
        "## Seam zones",
    ]
    for z,info in zone_exports.items():
        md.append(f"- `{z}`: edges={info['edge_count']} total_length={info['total_length']}")
    md += ["", "## Mesh exports"]
    for e in exports:
        md.append(f"- `{Path(e['path']).name}` verts={e['vertices']} faces={e['faces']}")
    md += ["", "## Renders"]
    for rr in renders:
        md.append(f"- `{rr['filename']}` camera=`{rr['camera']}`")
    text="\n".join(md)
    (REP/"Body_Target_Seam_Audit_Fix_v1B.md").write_text(text, encoding="utf-8")
    (REP/"BodyTargetSeamAuditFix_report.txt").write_text(text, encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"blender"/"sackboy_scene.blend"))
    print("[v1B] body target seam audit fix")
    print(f"[targets] hoodie={hoodie.name} body={body.name} method={body_method}")
    print(f"[hoodie] boundary_edges={len(edges)} islands={len(comps)} top={comps[:8]}")
    print(f"[cameras] removed={len(removed)} created={len(cams)}")
    print("[save] "+str(ROOT/"blender"/"sackboy_scene.blend"))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True, exist_ok=True)
        with (REP/"BodyTargetSeamAuditFix_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
