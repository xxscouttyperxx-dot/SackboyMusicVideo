
import bpy, os, json, csv
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","collar_snap_shape_seat_v1M")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
TEMP_PREFIX="TMP_V1M_COLLARSNAP_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"

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
    "hood_collar_back": center+Vector((0, dim.y*.30, dim.z*.02)),
    "hood_collar_front": center+Vector((0, -dim.y*.36, dim.z*.02)),
    "hood_collar_wide": center+Vector((0, -dim.y*.02, dim.z*.02)),
}
limits={"hood_collar_back":420,"hood_collar_front":420,"hood_collar_wide":520}
caps={"hood_collar_back":0.085,"hood_collar_front":0.085,"hood_collar_wide":0.095}
strengths={"hood_collar_back":0.92,"hood_collar_front":0.92,"hood_collar_wide":0.88}
max_pairs_by_zone={"hood_collar_back":140,"hood_collar_front":140,"hood_collar_wide":180}

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
    use=mesh_edge_use(mesh); adj={}; edges=[]
    for e in mesh.edges:
        a,b=e.vertices[:]
        if use.get(tuple(sorted((a,b))),0)==1:
            edges.append((a,b)); adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
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
    d=bpy.data.cameras.new(name+"_Data")
    o=bpy.data.objects.new(name,d)
    bpy.context.scene.collection.objects.link(o)
    o.location=loc; o.data.lens=lens; look_at(o,target)
    return o
def find_cam(names, parts=None):
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
    s=bpy.context.scene
    s.render.engine="BLENDER_WORKBENCH"
    s.display.shading.light="STUDIO"
    s.display.shading.color_type="MATERIAL"
    s.display.shading.show_cavity=True
    s.display.shading.show_object_outline=True
    s.render.image_settings.file_format="PNG"
    s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100

def render(camera, fn):
    s=bpy.context.scene
    s.camera=camera
    s.render.filepath=os.path.join(RENDER_DIR,fn)
    bpy.ops.render.render(write_still=True)
    print("[render] "+fn)

def render_review():
    remove_temp(); setup_render()
    full=cam(CAM_PREFIX+"FULL_CHARACTER_CHECK",center+Vector((0,-scale_ref*2.0,scale_ref*.36)),center,55)
    collar=find_cam(["DIAG_Hood collar view","DIAG_Collar view","DIAG_HoodInside_Collar"],["hood","collar"]) or cam(CAM_PREFIX+"COLLAR_FRONT",center+Vector((0,-scale_ref*1.10,scale_ref*.50)),anchors["hood_collar_front"],95)
    inside=find_cam(["DIAG_Hood inside view","DIAG_HoodInside","DIAG_Inside hood"],["hood","inside"]) or cam(CAM_PREFIX+"INSIDE_COLLAR",center+Vector((0,-scale_ref*.55,scale_ref*.68)),anchors["hood_collar_back"],110)
    back=cam(CAM_PREFIX+"BACK_COLLAR",center+Vector((0,scale_ref*1.05,scale_ref*.46)),anchors["hood_collar_back"],95)
    top=cam(CAM_PREFIX+"TOP_COLLAR",center+Vector((0,-scale_ref*.22,scale_ref*1.48)),anchors["hood_collar_wide"],90)
    names={"full":full.name,"collar_front":collar.name,"inside":inside.name,"collar_back":back.name,"top":top.name}
    render(full,"POST_01_FullCharacterCheck.png")
    prev=set_char_hidden(True)
    try:
        render(collar,"POST_02_HoodieOnly_CollarFront.png")
        render(inside,"POST_03_HoodieOnly_InsideHoodCollar.png")
        render(back,"POST_04_HoodieOnly_CollarBack.png")
        render(top,"POST_05_HoodieOnly_TopCollar.png")
    finally:
        restore(prev)
    remove_temp()
    return names

remove_temp()
before_edges,before_loops,before_sizes=boundary_metrics(hoodie)
before_poly,before_top=poly_islands(hoodie)

bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.objects.active=hoodie
hoodie.select_set(True)
if hoodie.data.shape_keys is None:
    hoodie.shape_key_add(name="Basis")

# Remove previous v1M for predictable reruns.
if hoodie.data.shape_keys:
    kb=hoodie.data.shape_keys.key_blocks.get("SEAMSEAT_CollarSnap_v1M")
    if kb:
        idx=list(hoodie.data.shape_keys.key_blocks).index(kb)
        hoodie.active_shape_key_index=idx
        bpy.ops.object.shape_key_remove()

mesh=hoodie.data
basis=[v.co.copy() for v in mesh.vertices]
current=[c.copy() for c in basis]
if mesh.shape_keys:
    for kb in mesh.shape_keys.key_blocks:
        if kb.name=="Basis": continue
        val=float(kb.value)
        if abs(val)<1e-8: continue
        for i in range(len(current)):
            current[i] += (kb.data[i].co - basis[i]) * val

edges,comp,adj=boundary_components(mesh)
coords=[c.copy() for c in current]
orig=[c.copy() for c in coords]
zone_order=["hood_collar_back","hood_collar_front","hood_collar_wide"]
repair={}; total_pairs=0; smooth_all=set(); max_move=0.0

def world(co): return hoodie.matrix_world @ co

for z in zone_order:
    rows=[]
    for a,b in edges:
        mid=(world(coords[a])+world(coords[b]))*.5
        rows.append(((mid-anchors[z]).length,a,b))
    rows.sort(key=lambda x:x[0])
    chosen=rows[:limits[z]]
    ids=sorted({i for _,a,b in chosen for i in (a,b)})
    candidates=[]
    for idx,vi in enumerate(ids):
        p=world(coords[vi])
        for vj in ids[idx+1:]:
            if vj in adj.get(vi,set()) or comp.get(vi)==comp.get(vj): continue
            d=(p-world(coords[vj])).length
            if d>1e-8:
                candidates.append((d,vi,vj))
    candidates.sort(key=lambda x:x[0])
    if candidates:
        dynamic=candidates[min(len(candidates)-1,int(len(candidates)*0.45))][0]*1.35
        th=min(max(dynamic, scale_ref*.006), scale_ref*caps[z])
    else:
        th=scale_ref*.010

    # Greedy sorted closest across components, intentionally stronger than mutual-only v1L.
    pairs=[]; used=set()
    for d,vi,vj in candidates:
        if d>th: continue
        if vi in used or vj in used: continue
        pairs.append((vi,vj,d))
        used.add(vi); used.add(vj)
        if len(pairs)>=max_pairs_by_zone[z]: break

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

    # Gentle post-seating relax on collar only.
    if smooth:
        newcoords={}
        for vi in smooth:
            nbs=list(adj.get(vi,set()))
            if not nbs: continue
            avg=sum((coords[n] for n in nbs), Vector())/len(nbs)
            newcoords[vi]=coords[vi].lerp(avg,0.055)
        for vi,nc in newcoords.items():
            max_move=max(max_move,float((hoodie.matrix_world.to_3x3()@(coords[vi]-nc)).length))
            coords[vi]=nc
        smooth_all.update(smooth)

    repair[z]={"candidate_vertices":len(ids),"threshold":round(float(th),6),"pairs":len(pairs),"smoothed_vertices":len(smooth),"components_touched":len(set(comp.get(i) for i in ids if comp.get(i) is not None))}
    total_pairs+=len(pairs)

max_allowed=scale_ref*0.075
scaled=False
if max_move>max_allowed and max_move>0:
    scale=max_allowed/max_move
    for i in range(len(coords)):
        coords[i]=orig[i]+(coords[i]-orig[i])*scale
    max_move=max_allowed
    scaled=True

shape=hoodie.shape_key_add(name="SEAMSEAT_CollarSnap_v1M", from_mix=False)
shape.value=1.0
shape.slider_min=0.0; shape.slider_max=1.0
# New key contains only the additional delta beyond the current visual mix, so it stacks correctly with v1L.
for i in range(len(coords)):
    additional_delta=coords[i]-current[i]
    shape.data[i].co=basis[i]+additional_delta

after_edges,after_loops,after_sizes=boundary_metrics(hoodie)
after_poly,after_top=poly_islands(hoodie)
if after_edges!=before_edges or after_loops!=before_loops:
    raise RuntimeError("Topology metrics changed during shape-key-only collar pass; refusing to continue.")
if total_pairs<1:
    raise RuntimeError("No collar snap pairs found; refusing to save.")

with open(os.path.join(CSV_DIR,"collar_snap_zone_summary.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["zone","candidate_vertices","threshold","pairs","smoothed_vertices","components_touched"])
    for z in zone_order:
        r=repair[z]
        w.writerow([z,r["candidate_vertices"],r["threshold"],r["pairs"],r["smoothed_vertices"],r["components_touched"]])

cam_names=render_review()

final_engine="UNKNOWN"
for eng in ("CYCLES","BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try:
        bpy.context.scene.render.engine=eng
        final_engine=bpy.context.scene.render.engine
        break
    except Exception:
        pass

bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)

status={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"hoodie_target":hoodie.name,"body_target":body.name,"saved_blend":True,"created_backup_blend_files":0,
"shape_key":{"name":"SEAMSEAT_CollarSnap_v1M","value":shape.value,"reversible":True,"stacks_on_existing_active_keys":True},
"metrics":{"boundary_edges_before":before_edges,"boundary_edges_after":after_edges,"boundary_loops_before":before_loops,"boundary_loops_after":after_loops,"polygon_islands_before":before_poly,"polygon_islands_after":after_poly},
"repair":{"total_pairs":total_pairs,"total_smoothed_vertices":len(smooth_all),"max_local_vertex_movement":round(float(max_move),6),"movement_scaled_by_safety_cap":scaled,"zones":repair},
"rendering":{"cameras":cam_names,"closeups_hide_sackboy":True,"colored_tube_overlays":False,"full_character_check_visible":True},
"final_render_engine":final_engine}

for p in [os.path.join(REPORT_DIR,"CollarSnapShapeSeatV1M_status.json"), os.path.join(REPORT_DIR,"collar_snap_shape_seat_v1M.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)

with open(os.path.join(REPORT_DIR,"CollarSnapShapeSeatV1M_report.txt"),"w",encoding="utf-8") as f:
    f.write("COLLAR SNAP SHAPE SEAT V1M\n")
    f.write(f"shape_key=SEAMSEAT_CollarSnap_v1M\nboundary_edges_unchanged={before_edges}\nboundary_loops_unchanged={before_loops}\ntotal_pairs={total_pairs}\ntotal_smoothed_vertices={len(smooth_all)}\nmax_local_vertex_movement={round(float(max_move),6)}\n")
    for z in zone_order:
        r=repair[z]
        f.write(f"zone={z}; pairs={r['pairs']}; smoothed_vertices={r['smoothed_vertices']}; threshold={r['threshold']}; components_touched={r['components_touched']}\n")

with open(os.path.join(REPORT_DIR,"Collar_Snap_Shape_Seat_V1M.md"),"w",encoding="utf-8") as f:
    f.write("# Collar Snap Shape Seat v1M\n\n")
    f.write("- Scope: collar / hood-to-sweater intersection only\n")
    f.write("- Shape key: `SEAMSEAT_CollarSnap_v1M`\n")
    f.write("- Reversible: **yes**\n")
    f.write(f"- Boundary edges unchanged: **{before_edges}**\n")
    f.write(f"- Boundary loops unchanged: **{before_loops}**\n")
    f.write(f"- Collar snap pairs: **{total_pairs}**\n")
    f.write(f"- Smoothed vertices: **{len(smooth_all)}**\n")
    f.write(f"- Max local vertex movement: **{round(float(max_move),6)}**\n\n")
    f.write("## Zone changes\n\n")
    for z in zone_order:
        r=repair[z]
        f.write(f"- **{z}**: pairs **{r['pairs']}**, smoothed vertices **{r['smoothed_vertices']}**, threshold **{r['threshold']}**, components touched **{r['components_touched']}**\n")
    f.write("\nManual comparison: select `SACKBOY_Hoodie_EditProxy`, then toggle shape key `SEAMSEAT_CollarSnap_v1M` between value 1 and 0.\n")

print("[v1M] collar snap shape seat complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print("[scope] collar_only=True")
print("[shape_key] name=SEAMSEAT_CollarSnap_v1M value=1 reversible=True")
print(f"[metrics] boundary_edges_unchanged={before_edges} boundary_loops_unchanged={before_loops}")
print(f"[repair] pairs={total_pairs}; smoothed={len(smooth_all)}; max_move={round(float(max_move),6)}")
for z in zone_order:
    r=repair[z]
    print(f"[zone] {z}: pairs={r['pairs']} smoothed={r['smoothed_vertices']} threshold={r['threshold']} components_touched={r['components_touched']}")
print("[rendering] closeups_hide_sackboy=True colored_tube_overlays=False")
print(f"[viewport] final_render_engine={final_engine}")
print("[safety] saved_blend=True created_backup_blend_files=0")
