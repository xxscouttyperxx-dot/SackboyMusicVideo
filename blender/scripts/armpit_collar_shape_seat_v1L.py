
import bpy, os, json, csv, math
from mathutils import Vector
from datetime import datetime, timezone
from collections import deque

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","armpit_collar_shape_seat_v1L")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
TEMP_PREFIX="TMP_V1L_SHAPESEAT_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"
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
limits={"hood_collar_back":260,"hood_collar_front":260,"left_armpit":230,"right_armpit":230,"hood_top":140}
caps={"hood_collar_back":0.026,"hood_collar_front":0.026,"left_armpit":0.018,"right_armpit":0.018,"hood_top":0.010}
strengths={"hood_collar_back":0.65,"hood_collar_front":0.60,"left_armpit":0.55,"right_armpit":0.55,"hood_top":0.30}
max_pairs_by_zone={"hood_collar_back":90,"hood_collar_front":70,"left_armpit":70,"right_armpit":60,"hood_top":18}

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

def boundary_components(mesh):
    use=mesh_edge_use(mesh)
    adj={}; edges=[]
    for e in mesh.edges:
        a,b=e.vertices[:]
        if use.get(tuple(sorted((a,b))),0)==1:
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

# Shape key setup.
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.objects.active=hoodie
hoodie.select_set(True)
if hoodie.data.shape_keys is None:
    hoodie.shape_key_add(name="Basis")
# remove previous v1L if it exists so reruns are predictable
if hoodie.data.shape_keys:
    kb=hoodie.data.shape_keys.key_blocks.get("SEAMSEAT_ArmpitCollar_v1L")
    if kb:
        idx=list(hoodie.data.shape_keys.key_blocks).index(kb)
        hoodie.active_shape_key_index=idx
        bpy.ops.object.shape_key_remove()
shape=hoodie.shape_key_add(name="SEAMSEAT_ArmpitCollar_v1L", from_mix=False)
shape.value=1.0
shape.slider_min=0.0; shape.slider_max=1.0
mesh=hoodie.data
verts_world=[hoodie.matrix_world @ v.co for v in mesh.vertices]
edges,comp,adj=boundary_components(mesh)

# Local copy of shapekey coords for editing.
coords=[shape.data[i].co.copy() for i in range(len(shape.data))]
orig=[c.copy() for c in coords]
zone_order=["hood_collar_back","hood_collar_front","left_armpit","right_armpit","hood_top"]
repair={}
total_pairs=0; smooth_all=set(); max_move=0.0

def world_from_local(co):
    return hoodie.matrix_world @ co

for z in zone_order:
    rows=[]
    for a,b in edges:
        mid=(world_from_local(coords[a])+world_from_local(coords[b]))*.5
        rows.append(((mid-anchors[z]).length,a,b))
    rows.sort(key=lambda x:x[0])
    chosen=rows[:limits[z]]
    ids=sorted({i for _,a,b in chosen for i in (a,b)})
    # distances across different boundary components
    dists=[]
    for ix,vi in enumerate(ids):
        p=world_from_local(coords[vi])
        for vj in ids[ix+1:]:
            if vj in adj.get(vi,set()) or comp.get(vi)==comp.get(vj): continue
            d=(p-world_from_local(coords[vj])).length
            if d>1e-8: dists.append(d)
    dists.sort()
    cap=scale_ref*caps[z]
    if dists:
        th=min(max(dists[min(len(dists)-1,int(len(dists)*0.20))]*1.12, scale_ref*.0015), cap)
    else:
        th=scale_ref*.003
    nearest={}
    for vi in ids:
        p=world_from_local(coords[vi]); best=None
        for vj in ids:
            if vj==vi or vj in adj.get(vi,set()) or comp.get(vi)==comp.get(vj): continue
            d=(p-world_from_local(coords[vj])).length
            if d<th and (best is None or d<best[1]): best=(vj,d)
        if best: nearest[vi]=best
    pairs=[]; used=set()
    for vi,(vj,d) in nearest.items():
        if vi in used or vj in used: continue
        if nearest.get(vj,(None,None))[0]==vi:
            pairs.append((vi,vj,d)); used.add(vi); used.add(vj)
    pairs.sort(key=lambda x:x[2])
    pairs=pairs[:max_pairs_by_zone[z]]
    strength=strengths[z]
    smooth=set()
    for vi,vj,d in pairs:
        a=coords[vi]; b=coords[vj]; mid=(a+b)*.5
        na=a.lerp(mid,strength); nb=b.lerp(mid,strength)
        max_move=max(max_move,float((hoodie.matrix_world.to_3x3()@(a-na)).length),float((hoodie.matrix_world.to_3x3()@(b-nb)).length))
        coords[vi]=na; coords[vj]=nb
        smooth.update([vi,vj])
        for n in adj.get(vi,set()): smooth.add(n)
        for n in adj.get(vj,set()): smooth.add(n)
    # tiny local relax around accepted areas only
    if smooth:
        for _ in range(1):
            newcoords={}
            for vi in smooth:
                nbs=list(adj.get(vi,set()))
                if not nbs: continue
                avg=sum((coords[n] for n in nbs), Vector())/len(nbs)
                factor=0.08 if "collar" in z else 0.06
                newcoords[vi]=coords[vi].lerp(avg,factor)
            for vi,nc in newcoords.items():
                max_move=max(max_move,float((hoodie.matrix_world.to_3x3()@(coords[vi]-nc)).length))
                coords[vi]=nc
        smooth_all.update(smooth)
    repair[z]={"candidate_vertices":len(ids),"threshold":round(float(th),6),"pairs":len(pairs),"smoothed_vertices":len(smooth),"components_touched":len(set(comp.get(i) for i in ids if comp.get(i) is not None))}
    total_pairs+=len(pairs)

# Safety movement clamp; if too high, scale down all deltas.
max_allowed=scale_ref*0.020
if max_move>max_allowed and max_move>0:
    scale=max_allowed/max_move
    for i in range(len(coords)):
        coords[i]=orig[i]+(coords[i]-orig[i])*scale
    max_move=max_allowed

# Write coords into shape key.
for i,co in enumerate(coords):
    shape.data[i].co=co

after_edges,after_loops,after_loop_sizes=boundary_metrics(hoodie); after_poly,after_top=poly_islands(hoodie)
# topology should not change
if after_edges!=before_edges or after_loops!=before_loops:
    raise RuntimeError("Topology metrics changed during shape-key-only pass; refusing to continue.")
if total_pairs<1:
    raise RuntimeError("No shape-key seam seating pairs found; refusing to save.")

with open(os.path.join(CSV_DIR,"zone_shape_seat_summary.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["zone","candidate_vertices","threshold","pairs","smoothed_vertices","components_touched"])
    for z in zone_order:
        r=repair[z]; w.writerow([z,r["candidate_vertices"],r["threshold"],r["pairs"],r["smoothed_vertices"],r["components_touched"]])

cam_names=render_review()

final_engine="UNKNOWN"
for eng in ("CYCLES","BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try:
        bpy.context.scene.render.engine=eng; final_engine=bpy.context.scene.render.engine; break
    except Exception: pass

bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)

status={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"hoodie_target":hoodie.name,"body_target":body.name,"saved_blend":True,"created_backup_blend_files":0,
"shape_key":{"name":"SEAMSEAT_ArmpitCollar_v1L","value":shape.value,"reversible":True},
"metrics":{"boundary_edges_before":before_edges,"boundary_edges_after":after_edges,"boundary_loops_before":before_loops,"boundary_loops_after":after_loops,"polygon_islands_before":before_poly,"polygon_islands_after":after_poly},
"repair":{"total_pairs":total_pairs,"total_smoothed_vertices":len(smooth_all),"max_local_vertex_movement":round(float(max_move),6),"zones":repair},
"rendering":{"cameras":cam_names,"closeups_hide_sackboy":True,"colored_tube_overlays":False,"full_character_check_visible":True},
"final_render_engine":final_engine}
for p in [os.path.join(REPORT_DIR,"ArmpitCollarShapeSeatV1L_status.json"),os.path.join(REPORT_DIR,"armpit_collar_shape_seat_v1L.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)
with open(os.path.join(REPORT_DIR,"ArmpitCollarShapeSeatV1L_report.txt"),"w",encoding="utf-8") as f:
    f.write(f"ARMPIT COLLAR SHAPE SEAT V1L\nshape_key=SEAMSEAT_ArmpitCollar_v1L\nboundary_edges_unchanged={before_edges}\nboundary_loops_unchanged={before_loops}\ntotal_pairs={total_pairs}\ntotal_smoothed_vertices={len(smooth_all)}\nmax_local_vertex_movement={round(float(max_move),6)}\n")
    for z in zone_order:
        r=repair[z]; f.write(f"zone={z}; pairs={r['pairs']}; smoothed_vertices={r['smoothed_vertices']}; threshold={r['threshold']}\n")
with open(os.path.join(REPORT_DIR,"Armpit_Collar_Shape_Seat_V1L.md"),"w",encoding="utf-8") as f:
    f.write(f"# Armpit Collar Shape Seat v1L\n\n- Shape key: `SEAMSEAT_ArmpitCollar_v1L`\n- Reversible: **yes**\n- Boundary edges unchanged: **{before_edges}**\n- Boundary loops unchanged: **{before_loops}**\n- Seating pairs: **{total_pairs}**\n- Smoothed vertices: **{len(smooth_all)}**\n- Max local vertex movement: **{round(float(max_move),6)}**\n\n## Zone changes\n\n")
    for z in zone_order:
        r=repair[z]; f.write(f"- **{z}**: pairs **{r['pairs']}**, smoothed vertices **{r['smoothed_vertices']}**, threshold **{r['threshold']}**\n")
    f.write("\nManual comparison: select `SACKBOY_Hoodie_EditProxy`, then toggle shape key `SEAMSEAT_ArmpitCollar_v1L` between value 1 and 0.\n")
print("[v1L] armpit collar shape seat complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print(f"[shape_key] name=SEAMSEAT_ArmpitCollar_v1L value=1 reversible=True")
print(f"[metrics] boundary_edges_unchanged={before_edges} boundary_loops_unchanged={before_loops}")
print(f"[repair] pairs={total_pairs}; smoothed={len(smooth_all)}; max_move={round(float(max_move),6)}")
for z in zone_order:
    r=repair[z]; print(f"[zone] {z}: pairs={r['pairs']} smoothed={r['smoothed_vertices']} threshold={r['threshold']}")
print(f"[rendering] closeups_hide_sackboy=True colored_tube_overlays=False")
print(f"[viewport] final_render_engine={final_engine}")
print("[safety] saved_blend=True created_backup_blend_files=0")
