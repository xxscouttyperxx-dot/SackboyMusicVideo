
import bpy, os, json, csv
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","seam_zone_edit_style_audit_v1J")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
TEMP_PREFIX="TMP_V1J_EDITSTYLE_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"
for name in os.listdir(RENDER_DIR):
    p=os.path.join(RENDER_DIR,name)
    if os.path.isfile(p):
        try: os.remove(p)
        except Exception: pass

def visible_obj(name):
    o=bpy.data.objects.get(name)
    if not o: return None
    try: vis=o.visible_get()
    except Exception: vis=not o.hide_viewport
    if not vis or o.hide_render: return None
    return o

hoodie=visible_obj("SACKBOY_Hoodie_EditProxy"); body=visible_obj("F2")
if hoodie is None or hoodie.type!="MESH": raise RuntimeError("Expected visible mesh SACKBOY_Hoodie_EditProxy not found.")
if body is None or body.type!="MESH": raise RuntimeError("Expected visible mesh F2 not found.")

def wbounds(obj):
    pts=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx,(mn+mx)*0.5,mx-mn
mn,mx,center,dim=wbounds(hoodie); scale_ref=max(dim.x,dim.y,dim.z,1e-6)
anchors={
"left_armpit":center+Vector((-dim.x*.40,0,-dim.z*.08)),
"right_armpit":center+Vector((dim.x*.40,0,-dim.z*.08)),
"hood_collar_front":center+Vector((0,-dim.y*.36,dim.z*.02)),
"hood_collar_back":center+Vector((0,dim.y*.30,dim.z*.02)),
"hood_top":center+Vector((0,0,dim.z*.38)),
}
radii={"left_armpit":scale_ref*.34,"right_armpit":scale_ref*.34,"hood_collar_front":scale_ref*.32,"hood_collar_back":scale_ref*.32,"hood_top":scale_ref*.28}
colors={"left_armpit":(1,0,0,1),"right_armpit":(1,.45,0,1),"hood_collar_front":(.1,1,.1,1),"hood_collar_back":(.1,.45,1,1),"hood_top":(1,.1,1,1)}

def mesh_edge_use(mesh):
    use={}
    for p in mesh.polygons:
        vs=list(p.vertices)
        for i in range(len(vs)):
            k=tuple(sorted((vs[i],vs[(i+1)%len(vs)]))); use[k]=use.get(k,0)+1
    return use

def boundary_data(obj):
    mesh=obj.data; use=mesh_edge_use(mesh); adj={}; edges=[]
    world=[obj.matrix_world@v.co for v in mesh.vertices]
    for e in mesh.edges:
        a,b=e.vertices[:]
        if use.get(tuple(sorted((a,b))),0)==1:
            mid=(world[a]+world[b])*.5
            edges.append({"a":a,"b":b,"wa":world[a],"wb":world[b],"mid":mid})
            adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    seen=set(); comps=[]; comp_by_vert={}
    for v in adj:
        if v in seen: continue
        stack=[v]; seen.add(v); verts=[]
        while stack:
            cur=stack.pop(); verts.append(cur)
            for nb in adj.get(cur,()):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        pts=[world[i] for i in verts]
        cc=sum(pts, Vector())/len(pts)
        ci=len(comps)
        for vi in verts: comp_by_vert[vi]=ci
        comps.append({"index":ci,"verts":verts,"size":len(verts),"center":cc})
    comps.sort(key=lambda c:c["size"], reverse=True)
    return edges, comps, comp_by_vert

def poly_islands(obj):
    mesh=obj.data
    if not mesh.polygons: return 0,[]
    parent=list(range(len(mesh.polygons))); rank=[0]*len(mesh.polygons)
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra==rb: return
        if rank[ra]<rank[rb]: parent[ra]=rb
        elif rank[ra]>rank[rb]: parent[rb]=ra
        else: parent[rb]=ra; rank[ra]+=1
    ep={}
    for pi,p in enumerate(mesh.polygons):
        vs=list(p.vertices)
        for i in range(len(vs)):
            ep.setdefault(tuple(sorted((vs[i],vs[(i+1)%len(vs)]))),[]).append(pi)
    for ps in ep.values():
        for i in range(1,len(ps)): union(ps[0],ps[i])
    sizes={}
    for i in range(len(mesh.polygons)): sizes[find(i)]=sizes.get(find(i),0)+1
    out=sorted(sizes.values(),reverse=True)
    return len(out),out[:10]

def remove_temp():
    for o in list(bpy.data.objects):
        if o.name.startswith(TEMP_PREFIX): bpy.data.objects.remove(o,do_unlink=True)
    for m in list(bpy.data.materials):
        if m.name.startswith(TEMP_PREFIX): bpy.data.materials.remove(m,do_unlink=True)

def mat(name, rgba):
    m=bpy.data.materials.new(TEMP_PREFIX+"MAT_"+name); m.diffuse_color=rgba; return m

def make_curve(name, edge_rows, rgba, bevel):
    m=mat(name,rgba)
    cu=bpy.data.curves.new(TEMP_PREFIX+name,"CURVE"); cu.dimensions="3D"; cu.resolution_u=1; cu.bevel_depth=bevel; cu.bevel_resolution=1
    for r in edge_rows:
        sp=cu.splines.new("POLY"); sp.points.add(1)
        sp.points[0].co=(r["wa"].x,r["wa"].y,r["wa"].z,1); sp.points[1].co=(r["wb"].x,r["wb"].y,r["wb"].z,1)
    o=bpy.data.objects.new(TEMP_PREFIX+name,cu); bpy.context.scene.collection.objects.link(o); o.data.materials.append(m); return o

def look_at(o,t): o.rotation_euler=(t-o.location).to_track_quat("-Z","Y").to_euler()
def cam(name, loc, target, lens=90):
    d=bpy.data.cameras.new(name+"_Data"); o=bpy.data.objects.new(name,d); bpy.context.scene.collection.objects.link(o)
    o.location=loc; o.data.lens=lens; look_at(o,target); return o
def find_cam(names,parts=None):
    by={o.name.lower():o for o in bpy.data.objects if o.type=="CAMERA"}
    for n in names:
        if n.lower() in by: return by[n.lower()]
    if parts:
        for o in bpy.data.objects:
            if o.type=="CAMERA" and all(p.lower() in o.name.lower() for p in parts): return o
    return None

def char_candidate(o):
    if o==hoodie: return False
    n=o.name.lower(); cols=" ".join(c.name.lower() for c in o.users_collection)
    hit=any(t in n for t in ["f2","sackboy","eye","mouth","cargo","pant","shoe","boot","sock","hand","arm","leg","body","head","face"])
    chit=any(t in cols for t in ["character","main model","clothing"])
    return o.type in {"MESH","CURVE","EMPTY"} and (hit or chit)
def set_char_hidden(hidden):
    prev={}
    for o in bpy.data.objects:
        if char_candidate(o):
            prev[o.name]=o.hide_render; o.hide_render=hidden
    return prev
def restore(prev):
    for n,val in prev.items():
        o=bpy.data.objects.get(n)
        if o: o.hide_render=val

def setup_render():
    s=bpy.context.scene; s.render.engine="BLENDER_WORKBENCH"; s.display.shading.light="STUDIO"; s.display.shading.color_type="MATERIAL"; s.display.shading.show_cavity=True; s.display.shading.show_object_outline=True; s.render.image_settings.file_format="PNG"; s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100
def render(camera, fn):
    s=bpy.context.scene; s.camera=camera; s.render.filepath=os.path.join(RENDER_DIR,fn); bpy.ops.render.render(write_still=True); print("[render] "+fn)

edges, comps, comp_by_vert=boundary_data(hoodie)
poly_count, top_polys=poly_islands(hoodie)

zone_rows={}
zone_summary={}
for z,a in anchors.items():
    within=[r for r in edges if (r["mid"]-a).length <= radii[z]]
    nearest=sorted(edges,key=lambda r:(r["mid"]-a).length)[:170]
    use=within if within else nearest
    comps_hit=sorted(set(comp_by_vert.get(r["a"],-1) for r in use) | set(comp_by_vert.get(r["b"],-1) for r in use))
    comps_hit=[c for c in comps_hit if c>=0]
    zone_rows[z]=nearest  # render consistent dense nearest boundary edges
    zone_summary[z]={
        "edges_within_radius":len(within),
        "vertices_within_radius":len(set(i for r in within for i in (r["a"],r["b"]))),
        "components_within_radius":len(comps_hit),
        "rendered_nearest_edges":len(nearest),
        "rendered_nearest_vertices":len(set(i for r in nearest for i in (r["a"],r["b"]))),
        "nearest_component_sizes":[comps[c]["size"] for c in comps_hit[:8] if c < len(comps)]
    }

# Try to include recorded v1F zone changes if local report exists.
prior={}
v1f_path=os.path.join(ROOT,"reports","residual_seam_consolidation_v1F","ResidualSeamConsolidationV1F_status.json")
if os.path.exists(v1f_path):
    try:
        with open(v1f_path,"r",encoding="utf-8") as f: v1f=json.load(f)
        for z, row in v1f.get("repair",{}).get("zones",{}).items():
            prior[z]={"v1F_pairs_accepted":row.get("pairs_accepted"),"v1F_smoothed_vertices":row.get("smoothed_vertices"),"v1F_threshold":row.get("threshold")}
    except Exception as e:
        prior={"error":str(e)}

with open(os.path.join(CSV_DIR,"zone_current_boundaries.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["zone","edges_within_radius","vertices_within_radius","components_within_radius","rendered_nearest_edges","rendered_nearest_vertices","nearest_component_sizes","v1F_pairs_accepted","v1F_smoothed_vertices"])
    for z in anchors.keys():
        s=zone_summary[z]; p=prior.get(z,{})
        w.writerow([z,s["edges_within_radius"],s["vertices_within_radius"],s["components_within_radius"],s["rendered_nearest_edges"],s["rendered_nearest_vertices"],";".join(map(str,s["nearest_component_sizes"])),p.get("v1F_pairs_accepted",""),p.get("v1F_smoothed_vertices","")])

remove_temp(); setup_render()
bevel=max(scale_ref*.0022,.0025)
# full render with all zone overlays, character visible
for z,rows in zone_rows.items():
    make_curve(z,rows,colors[z],bevel)
full=cam(CAM_PREFIX+"FULL_CHARACTER_CHECK",center+Vector((0,-scale_ref*2.0,scale_ref*.36)),center,55)
left=find_cam(["DIAG_L.Arm armpit view","DIAG_L.Arm","L.Arm armpit view"],["diag","l"]) or cam(CAM_PREFIX+"LEFT",center+Vector((-scale_ref*1.2,-scale_ref*.35,scale_ref*.25)),anchors["left_armpit"],100)
right=find_cam(["DIAG_R.Arm armpit view","DIAG_R.Arm","R.Arm armpit view"],["diag","r"]) or cam(CAM_PREFIX+"RIGHT",center+Vector((scale_ref*1.2,-scale_ref*.35,scale_ref*.25)),anchors["right_armpit"],100)
collar=find_cam(["DIAG_Hood collar view","DIAG_Collar view","DIAG_HoodInside_Collar"],["hood","collar"]) or cam(CAM_PREFIX+"COLLAR",center+Vector((0,-scale_ref*1.10,scale_ref*.50)),anchors["hood_collar_front"],95)
inside=find_cam(["DIAG_Hood inside view","DIAG_HoodInside","DIAG_Inside hood"],["hood","inside"]) or cam(CAM_PREFIX+"INSIDE",center+Vector((0,-scale_ref*.55,scale_ref*.68)),anchors["hood_collar_back"],110)
top=cam(CAM_PREFIX+"TOP",center+Vector((0,-scale_ref*.25,scale_ref*1.55)),anchors["hood_top"],90)
names={"full":full.name,"left":left.name,"right":right.name,"collar":collar.name,"inside":inside.name,"top":top.name}
render(full,"EDITSTYLE_01_FullCharacter_AllBoundaryZones.png")
prev=set_char_hidden(True)
try:
    render(left,"EDITSTYLE_02_HoodieOnly_LeftArmpit_BoundaryOverlay.png")
    render(right,"EDITSTYLE_03_HoodieOnly_RightArmpit_BoundaryOverlay.png")
    render(collar,"EDITSTYLE_04_HoodieOnly_HoodCollar_BoundaryOverlay.png")
    render(inside,"EDITSTYLE_05_HoodieOnly_InsideHoodCollar_BoundaryOverlay.png")
    render(top,"EDITSTYLE_06_HoodieOnly_HoodTop_BoundaryOverlay.png")
finally:
    restore(prev)
remove_temp()

# Set engine in memory only; no save.
final_engine="UNKNOWN"
for eng in ("CYCLES","BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try:
        bpy.context.scene.render.engine=eng; final_engine=bpy.context.scene.render.engine; break
    except Exception: pass

status={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"hoodie_target":hoodie.name,"body_target":body.name,"saved_blend":False,"created_backup_blend_files":0,
"current":{"boundary_edges":len(edges),"boundary_loop_count":len(comps),"boundary_loop_sizes":[c["size"] for c in comps[:10]],"polygon_island_count":poly_count,"top_polygon_islands":top_polys},
"zones":zone_summary,"prior_recorded_changes":prior,
"rendering":{"cameras":names,"closeups_hide_sackboy":True,"full_character_check_visible":True,"style":"Workbench solid with colored boundary-edge overlay; approximates edit-mode solid gap inspection."},
"final_render_engine_memory_only":final_engine}
for p in [os.path.join(REPORT_DIR,"SeamZoneEditStyleAuditV1J_status.json"), os.path.join(REPORT_DIR,"seam_zone_edit_style_audit_v1J.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)
with open(os.path.join(REPORT_DIR,"SeamZoneEditStyleAuditV1J_report.txt"),"w",encoding="utf-8") as f:
    f.write("SEAM ZONE EDIT STYLE AUDIT V1J\n")
    f.write(f"boundary_edges={len(edges)}\nboundary_loops={len(comps)}\npolygon_islands={poly_count}\n")
    for z,s in zone_summary.items():
        p=prior.get(z,{})
        f.write(f"zone={z}; edges_within_radius={s['edges_within_radius']}; vertices_within_radius={s['vertices_within_radius']}; components_within_radius={s['components_within_radius']}; v1F_pairs_accepted={p.get('v1F_pairs_accepted','')}\n")
with open(os.path.join(REPORT_DIR,"Seam_Zone_Edit_Style_Audit_V1J.md"),"w",encoding="utf-8") as f:
    f.write("# Seam Zone Edit-Style Audit v1J\n\n")
    f.write(f"- Boundary edges: **{len(edges)}**\n- Boundary loops: **{len(comps)}**\n- Polygon islands: **{poly_count}**\n\n")
    f.write("## Current zone boundary counts\n\n")
    for z,s in zone_summary.items():
        p=prior.get(z,{})
        f.write(f"- **{z}**: edges within radius **{s['edges_within_radius']}**, components **{s['components_within_radius']}**, rendered nearest edges **{s['rendered_nearest_edges']}**, v1F accepted pairs **{p.get('v1F_pairs_accepted','unknown')}**\n")
    f.write("\n## Render note\n\nCloseups hide Sackboy/body/accessories and use colored boundary-edge overlays to mimic solid edit-mode seam inspection.\n")

print("[v1J] seam zone edit-style audit complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print(f"[current] boundary_edges={len(edges)} boundary_loops={len(comps)} polygon_islands={poly_count}")
for z,s in zone_summary.items():
    print(f"[zone] {z}: edges_within_radius={s['edges_within_radius']} components={s['components_within_radius']} rendered_edges={s['rendered_nearest_edges']} v1F_pairs={prior.get(z,{}).get('v1F_pairs_accepted','unknown')}")
print(f"[rendering] closeups_hide_sackboy=True style=solid_edit_boundary_overlay")
print("[safety] saved_blend=False created_backup_blend_files=0")
