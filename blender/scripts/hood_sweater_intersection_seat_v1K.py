
import bpy, bmesh, os, json, csv
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","hood_sweater_intersection_seat_v1K")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
TEMP_PREFIX="TMP_V1K_HOODSEAT_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"
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
"hood_collar_back":center+Vector((0,dim.y*.30,dim.z*.02)),
"hood_collar_front":center+Vector((0,-dim.y*.36,dim.z*.02)),
"left_armpit":center+Vector((-dim.x*.40,0,-dim.z*.08)),
"right_armpit":center+Vector((dim.x*.40,0,-dim.z*.08)),
"hood_top":center+Vector((0,0,dim.z*.38)),
}
limits={"hood_collar_back":260,"hood_collar_front":260,"left_armpit":220,"right_armpit":220,"hood_top":150}
zone_caps={"hood_collar_back":0.020,"hood_collar_front":0.020,"left_armpit":0.014,"right_armpit":0.014,"hood_top":0.010}
zone_pcts={"hood_collar_back":0.16,"hood_collar_front":0.16,"left_armpit":0.12,"right_armpit":0.12,"hood_top":0.08}

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
    seen=set(); loops=0; sizes=[]
    for v in adj:
        if v in seen: continue
        loops+=1; stack=[v]; seen.add(v); n=0
        while stack:
            cur=stack.pop(); n+=1
            for nb in adj.get(cur,()):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        sizes.append(n)
    sizes.sort(reverse=True)
    return count,loops,sizes

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
        if char_candidate(o): prev[o.name]=o.hide_render; o.hide_render=hidden
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
    edges=[]; adj={}
    for e in bm.edges:
        k=tuple(sorted((e.verts[0].index,e.verts[1].index)))
        if use.get(k,0)==1:
            a,b=e.verts[0].index,e.verts[1].index
            edges.append((a,b))
            adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    comp={}; cid=0
    for v in adj:
        if v in comp: continue
        cid+=1; stack=[v]; comp[v]=cid
        while stack:
            cur=stack.pop()
            for nb in adj.get(cur,()):
                if nb not in comp:
                    comp[nb]=cid; stack.append(nb)
    return edges,comp,adj

def bm_world(bm, vi): return hoodie.matrix_world @ bm.verts[vi].co

def candidate_ids(bm, edges, z):
    rows=[]
    a=anchors[z]
    for vi,vj in edges:
        if vi>=len(bm.verts) or vj>=len(bm.verts): continue
        mid=(bm_world(bm,vi)+bm_world(bm,vj))*0.5
        rows.append(((mid-a).length,vi,vj))
    rows.sort(key=lambda x:x[0])
    chosen=rows[:limits[z]]
    return sorted({i for _,vi,vj in chosen for i in (vi,vj)}), chosen

def render_review():
    remove_temp(); setup_render()
    full=cam(CAM_PREFIX+"FULL_CHARACTER_CHECK",center+Vector((0,-scale_ref*2.0,scale_ref*.36)),center,55)
    left=find_cam(["DIAG_L.Arm armpit view","DIAG_L.Arm","L.Arm armpit view"],["diag","l"]) or cam(CAM_PREFIX+"LEFT",center+Vector((-scale_ref*1.2,-scale_ref*.35,scale_ref*.25)),anchors["left_armpit"],100)
    right=find_cam(["DIAG_R.Arm armpit view","DIAG_R.Arm","R.Arm armpit view"],["diag","r"]) or cam(CAM_PREFIX+"RIGHT",center+Vector((scale_ref*1.2,-scale_ref*.35,scale_ref*.25)),anchors["right_armpit"],100)
    collar=find_cam(["DIAG_Hood collar view","DIAG_Collar view","DIAG_HoodInside_Collar"],["hood","collar"]) or cam(CAM_PREFIX+"COLLAR",center+Vector((0,-scale_ref*1.10,scale_ref*.50)),anchors["hood_collar_front"],95)
    inside=find_cam(["DIAG_Hood inside view","DIAG_HoodInside","DIAG_Inside hood"],["hood","inside"]) or cam(CAM_PREFIX+"INSIDE",center+Vector((0,-scale_ref*.55,scale_ref*.68)),anchors["hood_collar_back"],110)
    top=cam(CAM_PREFIX+"TOP",center+Vector((0,-scale_ref*.25,scale_ref*1.55)),anchors["hood_top"],90)
    names={"full":full.name,"left":left.name,"right":right.name,"collar":collar.name,"inside":inside.name,"top":top.name}
    render(full,"POST_01_FullCharacterCheck.png")
    prev=set_char_hidden(True)
    try:
        render(left,"POST_02_HoodieOnly_LeftArmpit.png")
        render(right,"POST_03_HoodieOnly_RightArmpit.png")
        render(collar,"POST_04_HoodieOnly_HoodCollar.png")
        render(inside,"POST_05_HoodieOnly_InsideHoodCollar.png")
        render(top,"POST_06_HoodieOnly_HoodTop.png")
    finally:
        restore(prev)
    remove_temp()
    return names

remove_temp()
before_edges,before_loops,before_loop_sizes=boundary_metrics(hoodie); before_poly,before_top=poly_islands(hoodie)
orig=hoodie.data.copy()
bm=bmesh.new(); bm.from_mesh(hoodie.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()

zone_order=["hood_collar_back","hood_collar_front","left_armpit","right_armpit","hood_top"]
repair={}; total_pairs=0; smooth_all=set(); max_move=0.0

for z in zone_order:
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    edges,comp,adj=bm_boundary(bm)
    ids,_=candidate_ids(bm,edges,z)
    # Build distance sample across different boundary components.
    dists=[]
    for idx,vi in enumerate(ids):
        if vi>=len(bm.verts): continue
        p=bm_world(bm,vi)
        for vj in ids[idx+1:]:
            if vj>=len(bm.verts) or vj in adj.get(vi,set()) or comp.get(vi)==comp.get(vj): continue
            dists.append((p-bm_world(bm,vj)).length)
    ds=sorted(d for d in dists if d>1e-8)
    pct=zone_pcts[z]
    cap=scale_ref*zone_caps[z]
    if ds:
        th=min(max(ds[min(len(ds)-1,int(len(ds)*pct))]*1.08, scale_ref*.0012), cap)
    else:
        th=scale_ref*.003
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
    # Zone caps to avoid over-pulling
    max_pairs={"hood_collar_back":90,"hood_collar_front":70,"left_armpit":55,"right_armpit":45,"hood_top":20}[z]
    pairs=pairs[:max_pairs]
    moved=[]; smooth=set()
    for vi,vj,d in pairs:
        if vi>=len(bm.verts) or vj>=len(bm.verts): continue
        va,vb=bm.verts[vi],bm.verts[vj]
        mid=(va.co+vb.co)*0.5
        max_move=max(max_move,float((hoodie.matrix_world.to_3x3()@(va.co-mid)).length),float((hoodie.matrix_world.to_3x3()@(vb.co-mid)).length))
        va.co=mid.copy(); vb.co=mid.copy()
        moved.extend([va,vb]); smooth.update([vi,vj])
        for e in list(va.link_edges)+list(vb.link_edges):
            for v in e.verts: smooth.add(v.index)
    if moved:
        bmesh.ops.remove_doubles(bm, verts=list(set(moved)), dist=max(th*.09,1e-7))
        bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        sv=[bm.verts[i] for i in sorted(i for i in smooth if i<len(bm.verts))]
        if sv:
            bmesh.ops.smooth_vert(bm, verts=sv, factor=.10, use_axis_x=True,use_axis_y=True,use_axis_z=True)
            smooth_all.update(v.index for v in sv)
    repair[z]={"candidate_vertices":len(ids),"threshold":round(float(th),6),"pairs_accepted":len(pairs),"smoothed_vertices":len(smooth),"components_touched":len(set(comp.get(i) for i in ids if comp.get(i) is not None))}
    total_pairs+=len(pairs)

bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(hoodie.data); hoodie.data.update(); bm.free()
after_edges,after_loops,after_loop_sizes=boundary_metrics(hoodie); after_poly,after_top=poly_islands(hoodie)

reverted=False
if total_pairs<1 or after_edges>before_edges or after_loops>before_loops or max_move>(scale_ref*.020):
    reverted=True
    old=hoodie.data; hoodie.data=orig
    try: bpy.data.meshes.remove(old)
    except Exception: pass
    after_edges,after_loops,after_loop_sizes=boundary_metrics(hoodie); after_poly,after_top=poly_islands(hoodie)
else:
    try: bpy.data.meshes.remove(orig)
    except Exception: pass

with open(os.path.join(CSV_DIR,"zone_repair_summary.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["zone","candidate_vertices","threshold","pairs_accepted","smoothed_vertices","components_touched"])
    for z in zone_order:
        r=repair[z]; w.writerow([z,r["candidate_vertices"],r["threshold"],r["pairs_accepted"],r["smoothed_vertices"],r["components_touched"]])

cam_names=render_review()

final_engine="UNKNOWN"
for eng in ("CYCLES","BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try:
        bpy.context.scene.render.engine=eng; final_engine=bpy.context.scene.render.engine; break
    except Exception: pass

saved=False
if not reverted:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath); saved=True

status={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"hoodie_target":hoodie.name,"body_target":body.name,"saved_blend":saved,"reverted_due_to_safety_gate":reverted,"created_backup_blend_files":0,
"before":{"boundary_edges":before_edges,"boundary_loop_count":before_loops,"boundary_loop_sizes":before_loop_sizes[:10],"polygon_island_count":before_poly,"top_polygon_islands":before_top},
"after":{"boundary_edges":after_edges,"boundary_loop_count":after_loops,"boundary_loop_sizes":after_loop_sizes[:10],"polygon_island_count":after_poly,"top_polygon_islands":after_top},
"repair":{"total_pairs_accepted":total_pairs if not reverted else 0,"total_smoothed_vertices":len(smooth_all) if not reverted else 0,"max_local_vertex_movement":round(float(max_move),6) if not reverted else 0.0,"zones":repair},
"rendering":{"cameras":cam_names,"closeups_hide_sackboy":True,"full_character_check_visible":True,"colored_tube_overlays":False},
"final_render_engine":final_engine}
for p in [os.path.join(REPORT_DIR,"HoodSweaterIntersectionSeatV1K_status.json"),os.path.join(REPORT_DIR,"hood_sweater_intersection_seat_v1K.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)
with open(os.path.join(REPORT_DIR,"HoodSweaterIntersectionSeatV1K_report.txt"),"w",encoding="utf-8") as f:
    f.write(f"HOOD SWEATER INTERSECTION SEAT V1K\nbefore_boundary_edges={before_edges}\nafter_boundary_edges={after_edges}\nbefore_boundary_loop_count={before_loops}\nafter_boundary_loop_count={after_loops}\ntotal_pairs_accepted={status['repair']['total_pairs_accepted']}\ntotal_smoothed_vertices={status['repair']['total_smoothed_vertices']}\nmax_local_vertex_movement={status['repair']['max_local_vertex_movement']}\n")
    for z in zone_order:
        r=repair[z]; f.write(f"zone={z}; pairs_accepted={r['pairs_accepted']}; smoothed_vertices={r['smoothed_vertices']}; threshold={r['threshold']}\n")
with open(os.path.join(REPORT_DIR,"Hood_Sweater_Intersection_Seat_V1K.md"),"w",encoding="utf-8") as f:
    f.write(f"# Hood Sweater Intersection Seat v1K\n\n- Boundary edges: **{before_edges} -> {after_edges}**\n- Boundary loops: **{before_loops} -> {after_loops}**\n- Accepted seam seating pairs: **{status['repair']['total_pairs_accepted']}**\n- Smoothed vertices: **{status['repair']['total_smoothed_vertices']}**\n- Max local vertex movement: **{status['repair']['max_local_vertex_movement']}**\n\n## Zone changes\n\n")
    for z in zone_order:
        r=repair[z]; f.write(f"- **{z}**: pairs **{r['pairs_accepted']}**, smoothed vertices **{r['smoothed_vertices']}**, threshold **{r['threshold']}**\n")
    f.write("\nRender note: closeups hide Sackboy/body/accessories and no colored tube overlays are used.\n")
print("[v1K] hood sweater intersection seat complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print(f"[repair] boundary_edges {before_edges} -> {after_edges}; boundary_loops {before_loops} -> {after_loops}; pairs={status['repair']['total_pairs_accepted']}; smoothed={status['repair']['total_smoothed_vertices']}; max_move={status['repair']['max_local_vertex_movement']}")
for z in zone_order:
    r=repair[z]; print(f"[zone] {z}: pairs={r['pairs_accepted']} smoothed={r['smoothed_vertices']} threshold={r['threshold']}")
print(f"[rendering] closeups_hide_sackboy=True colored_tube_overlays=False")
print(f"[viewport] final_render_engine={final_engine}")
print(f"[safety] saved_blend={saved} reverted_due_to_safety_gate={reverted} created_backup_blend_files=0")
if reverted:
    raise RuntimeError("Safety gate reverted v1K because no safe improvement was found or metrics worsened; blend was not saved.")
