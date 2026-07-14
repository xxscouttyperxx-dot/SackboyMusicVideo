
import bpy, bmesh, os, json, csv, math
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","residual_seam_consolidation_v1F")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
STATUS_PATH=os.path.join(REPORT_DIR,"ResidualSeamConsolidationV1F_status.json")
TEMP_PREFIX="TMP_V1F_SEAMCONSOLIDATE_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"

for name in os.listdir(RENDER_DIR):
    p=os.path.join(RENDER_DIR,name)
    if os.path.isfile(p):
        try: os.remove(p)
        except Exception: pass

try: bpy.context.preferences.filepaths.save_version=0
except Exception: pass

def visible_obj(name):
    o=bpy.data.objects.get(name)
    if not o: return None
    try: vis=o.visible_get()
    except Exception: vis=not o.hide_viewport
    if not vis or o.hide_render: return None
    return o

hoodie=visible_obj("SACKBOY_Hoodie_EditProxy")
body=visible_obj("F2")
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
"hood_top":center+Vector((0,0,dim.z*.38))}
limits={"left_armpit":150,"right_armpit":150,"hood_collar_front":170,"hood_collar_back":170,"hood_top":130}

def mesh_edge_use(mesh):
    use={}
    for p in mesh.polygons:
        vs=list(p.vertices)
        for i in range(len(vs)):
            k=tuple(sorted((vs[i],vs[(i+1)%len(vs)]))); use[k]=use.get(k,0)+1
    return use

def boundary_metrics(obj):
    mesh=obj.data; use=mesh_edge_use(mesh); adj={}; count=0
    for e in mesh.edges:
        a,b=e.vertices[:]
        if use.get(tuple(sorted((a,b))),0)==1:
            count+=1; adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    seen=set(); loops=0
    for v in adj:
        if v in seen: continue
        loops+=1; stack=[v]; seen.add(v)
        while stack:
            cur=stack.pop()
            for nb in adj.get(cur,()):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
    return count,loops

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
    comps={}
    for i in range(len(mesh.polygons)): comps[find(i)]=comps.get(find(i),0)+1
    sizes=sorted(comps.values(),reverse=True)
    return len(sizes),sizes[:8]

def remove_temp():
    for o in list(bpy.data.objects):
        if o.name.startswith(TEMP_PREFIX): bpy.data.objects.remove(o,do_unlink=True)
    for m in list(bpy.data.materials):
        if m.name.startswith(TEMP_PREFIX): bpy.data.materials.remove(m,do_unlink=True)

def look_at(o,t): o.rotation_euler=(t-o.location).to_track_quat("-Z","Y").to_euler()
def cam(name, loc, target, lens=90):
    d=bpy.data.cameras.new(name+"_Data"); o=bpy.data.objects.new(name,d); bpy.context.scene.collection.objects.link(o)
    o.location=loc; o.data.lens=lens; look_at(o,target); return o
def find_cam(*names):
    low={o.name.lower():o for o in bpy.data.objects if o.type=="CAMERA"}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    # contains fallback
    for o in bpy.data.objects:
        if o.type=="CAMERA":
            ln=o.name.lower()
            if all(part.lower() in ln for part in names[0].replace("_"," ").replace("."," ").split()[:2]):
                return o
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

def bm_boundary(bm):
    use={}
    for f in bm.faces:
        for e in f.edges:
            k=tuple(sorted((e.verts[0].index,e.verts[1].index))); use[k]=use.get(k,0)+1
    edges=[]; comp={}; adj={}
    for e in bm.edges:
        k=tuple(sorted((e.verts[0].index,e.verts[1].index)))
        if use.get(k,0)==1:
            edges.append((e.verts[0].index,e.verts[1].index))
            a,b=e.verts[0].index,e.verts[1].index; adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    cid=0
    for v in adj:
        if v in comp: continue
        cid+=1; stack=[v]; comp[v]=cid
        while stack:
            cur=stack.pop()
            for nb in adj.get(cur,()):
                if nb not in comp:
                    comp[nb]=cid; stack.append(nb)
    return edges,comp

def bm_world(bm, vi): return hoodie.matrix_world @ bm.verts[vi].co
def candidate_ids(bm, edges, z):
    rows=[]
    for a,b in edges:
        if a>=len(bm.verts) or b>=len(bm.verts): continue
        mid=(bm_world(bm,a)+bm_world(bm,b))*0.5; rows.append(((mid-anchors[z]).length,a,b))
    rows.sort(key=lambda x:x[0])
    chosen=rows[:limits[z]]
    return sorted({i for _,a,b in chosen for i in (a,b)})

remove_temp()
before_edges,before_loops=boundary_metrics(hoodie); before_poly,before_top=poly_islands(hoodie)
orig=hoodie.data.copy()
bm=bmesh.new(); bm.from_mesh(hoodie.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
repair={}; total_pairs=0; smooth_all=set(); max_move=0.0
zone_order=["left_armpit","right_armpit","hood_collar_front","hood_collar_back","hood_top"]

for z in zone_order:
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    edges,comp=bm_boundary(bm)  # rebuilt every zone to avoid stale BMEdge refs
    adj={v.index:set() for v in bm.verts}
    for e in bm.edges:
        a,b=e.verts[0].index,e.verts[1].index; adj[a].add(b); adj[b].add(a)
    ids=candidate_ids(bm,edges,z)
    ds=[]
    for ii,vi in enumerate(ids):
        if vi>=len(bm.verts): continue
        p=bm_world(bm,vi)
        for vj in ids[ii+1:]:
            if vj>=len(bm.verts) or vj in adj.get(vi,set()) or comp.get(vi)==comp.get(vj): continue
            ds.append((p-bm_world(bm,vj)).length)
    ds=sorted(d for d in ds if d>1e-8)
    th=min(max((ds[int(len(ds)*0.20)] if ds else scale_ref*.003)*1.10, scale_ref*.0012), scale_ref*.010)
    nearest={}
    for vi in ids:
        if vi>=len(bm.verts): continue
        p=bm_world(bm,vi); best=None
        for vj in ids:
            if vj==vi or vj>=len(bm.verts) or vj in adj.get(vi,set()) or comp.get(vi)==comp.get(vj): continue
            d=(p-bm_world(bm,vj)).length
            if d<th and (best is None or d<best[1]): best=(vj,d)
        if best: nearest[vi]=best
    pairs=[]; used=set()
    for vi,(vj,d) in nearest.items():
        if vi in used or vj in used: continue
        if nearest.get(vj,(None,None))[0]==vi:
            pairs.append((vi,vj,d)); used.add(vi); used.add(vj)
    pairs.sort(key=lambda x:x[2])
    moved=[]; smooth=set()
    for vi,vj,d in pairs:
        if vi>=len(bm.verts) or vj>=len(bm.verts): continue
        va,vb=bm.verts[vi],bm.verts[vj]; mid=(va.co+vb.co)*0.5
        max_move=max(max_move, float((hoodie.matrix_world.to_3x3()@(va.co-mid)).length), float((hoodie.matrix_world.to_3x3()@(vb.co-mid)).length))
        va.co=mid.copy(); vb.co=mid.copy(); moved.extend([va,vb]); smooth.update([vi,vj])
        for e in list(va.link_edges)+list(vb.link_edges):
            for v in e.verts: smooth.add(v.index)
    if moved:
        bmesh.ops.remove_doubles(bm, verts=list(set(moved)), dist=max(th*.08,1e-7))
        bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        sv=[bm.verts[i] for i in sorted(i for i in smooth if i<len(bm.verts))]
        if sv:
            bmesh.ops.smooth_vert(bm, verts=sv, factor=.14, use_axis_x=True,use_axis_y=True,use_axis_z=True)
            smooth_all.update(v.index for v in sv)
    repair[z]={"candidate_vertices":len(ids),"threshold":round(float(th),6),"pairs_accepted":len(pairs),"smoothed_vertices":len(smooth),"components_touched":len(set(comp.get(i) for i in ids if comp.get(i) is not None))}
    total_pairs+=len(pairs)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(hoodie.data); hoodie.data.update(); bm.free()
after_edges,after_loops=boundary_metrics(hoodie); after_poly,after_top=poly_islands(hoodie)
reverted=False
if after_edges>before_edges or after_loops>before_loops:
    reverted=True
    old=hoodie.data; hoodie.data=orig
    try: bpy.data.meshes.remove(old)
    except Exception: pass
    after_edges,after_loops=boundary_metrics(hoodie); after_poly,after_top=poly_islands(hoodie)
else:
    try: bpy.data.meshes.remove(orig)
    except Exception: pass

# write csv summary
with open(os.path.join(CSV_DIR,"zone_summary.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["zone","candidate_vertices","threshold","pairs_accepted","smoothed_vertices","components_touched"])
    for z in zone_order:
        r=repair[z]; w.writerow([z,r["candidate_vertices"],r["threshold"],r["pairs_accepted"],r["smoothed_vertices"],r["components_touched"]])

# renders
remove_temp(); setup_render()
full_cam=cam(CAM_PREFIX+"FULL_CHARACTER_CHECK", center+Vector((0,-scale_ref*2.0,scale_ref*.36)), center, 55)
left_cam=find_cam("DIAG_L.Arm armpit view","DIAG_L.Arm","L.Arm armpit view") or cam(CAM_PREFIX+"HOODIE_ONLY_LEFT", center+Vector((-scale_ref*1.20,-scale_ref*.35,scale_ref*.25)), anchors["left_armpit"],100)
right_cam=find_cam("DIAG_R.Arm armpit view","DIAG_R.Arm","R.Arm armpit view") or cam(CAM_PREFIX+"HOODIE_ONLY_RIGHT", center+Vector((scale_ref*1.20,-scale_ref*.35,scale_ref*.25)), anchors["right_armpit"],100)
collar_cam=cam(CAM_PREFIX+"HOODIE_ONLY_COLLAR", center+Vector((0,-scale_ref*1.10,scale_ref*.50)), anchors["hood_collar_front"],95)
top_cam=cam(CAM_PREFIX+"HOODIE_ONLY_TOP", center+Vector((0,-scale_ref*.25,scale_ref*1.55)), anchors["hood_top"],90)
render(full_cam,"POST_01_FullCharacterCheck.png")
prev=set_char_hidden(True)
try:
    render(left_cam,"POST_02_HoodieOnly_LeftArmpit.png")
    render(right_cam,"POST_03_HoodieOnly_RightArmpit.png")
    render(collar_cam,"POST_04_HoodieOnly_HoodCollar.png")
    render(top_cam,"POST_05_HoodieOnly_HoodTop.png")
finally:
    restore(prev)
remove_temp()

saved=False
if not reverted:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath); saved=True

status={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"hoodie_target":hoodie.name,"body_target":body.name,"saved_blend":saved,"reverted_due_to_safety_gate":reverted,"created_backup_blend_files":0,
"before":{"boundary_edges":before_edges,"boundary_loop_count":before_loops,"polygon_island_count":before_poly,"top_polygon_islands":before_top},
"after":{"boundary_edges":after_edges,"boundary_loop_count":after_loops,"polygon_island_count":after_poly,"top_polygon_islands":after_top},
"repair":{"total_pairs_accepted":total_pairs if not reverted else 0,"total_smoothed_vertices":len(smooth_all) if not reverted else 0,"max_local_vertex_movement":round(float(max_move),6) if not reverted else 0.0,"zones":repair},
"rendering":{"left_armpit_camera":left_cam.name,"right_armpit_camera":right_cam.name,"closeups_hide_sackboy":True,"full_character_check_visible":True}}
for p in [STATUS_PATH, os.path.join(REPORT_DIR,"residual_seam_consolidation_v1F.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)
with open(os.path.join(REPORT_DIR,"ResidualSeamConsolidationV1F_report.txt"),"w",encoding="utf-8") as f:
    f.write(f"RESIDUAL SEAM CONSOLIDATION V1F\nbefore_boundary_edges={before_edges}\nafter_boundary_edges={after_edges}\nbefore_boundary_loop_count={before_loops}\nafter_boundary_loop_count={after_loops}\ntotal_pairs_accepted={status['repair']['total_pairs_accepted']}\ntotal_smoothed_vertices={status['repair']['total_smoothed_vertices']}\nmax_local_vertex_movement={status['repair']['max_local_vertex_movement']}\nleft_armpit_camera={left_cam.name}\nright_armpit_camera={right_cam.name}\n")
with open(os.path.join(REPORT_DIR,"Residual_Seam_Consolidation_V1F.md"),"w",encoding="utf-8") as f:
    f.write(f"# Residual Seam Consolidation v1F\n\n- Boundary edges: **{before_edges} -> {after_edges}**\n- Boundary loops: **{before_loops} -> {after_loops}**\n- Accepted seam pairs: **{status['repair']['total_pairs_accepted']}**\n- Smoothed vertices: **{status['repair']['total_smoothed_vertices']}**\n- Max local vertex movement: **{status['repair']['max_local_vertex_movement']}**\n- Left armpit camera: `{left_cam.name}`\n- Right armpit camera: `{right_cam.name}`\n\nOnly `POST_01_FullCharacterCheck.png` shows the full character. Other closeups hide Sackboy/body/accessories.\n")
print("[v1F] residual seam consolidation complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print(f"[repair] boundary_edges {before_edges} -> {after_edges}; boundary_loops {before_loops} -> {after_loops}; pairs={status['repair']['total_pairs_accepted']}; smoothed={status['repair']['total_smoothed_vertices']}; max_move={status['repair']['max_local_vertex_movement']}")
print(f"[rendering] left_armpit_camera={left_cam.name} right_armpit_camera={right_cam.name} closeups_hide_sackboy=True")
print(f"[safety] saved_blend={saved} reverted_due_to_safety_gate={reverted} created_backup_blend_files=0")
if reverted:
    raise RuntimeError("Safety gate reverted v1F because boundary metrics worsened; blend was not saved.")
