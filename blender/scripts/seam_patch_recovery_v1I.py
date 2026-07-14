
import bpy, os, json, csv
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","seam_patch_recovery_v1I")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
TEMP_PREFIX="TMP_V1I_RECOVERY_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"
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
            edges.append((a,b,(world[a]+world[b])*.5))
            adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    seen=set(); comps=[]
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
        comps.append({"verts":verts,"size":len(verts),"center":cc})
    comps.sort(key=lambda c:c["size"], reverse=True)
    return edges, comps

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

edges, comps = boundary_data(hoodie)
poly_count, top_polys = poly_islands(hoodie)
zone_summary={}
for z,a in anchors.items():
    scored=sorted(edges, key=lambda r:(r[2]-a).length)[:170]
    zone_summary[z]={"candidate_edges":len(scored),"candidate_vertices":len(set(i for e in scored for i in e[:2]))}

with open(os.path.join(CSV_DIR,"boundary_components.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["rank","vertex_count","center_x","center_y","center_z","nearest_zone","nearest_zone_distance"])
    for rank,c in enumerate(comps[:30],1):
        z,d=min(((z,(c["center"]-a).length) for z,a in anchors.items()), key=lambda x:x[1])
        w.writerow([rank,c["size"],round(c["center"].x,6),round(c["center"].y,6),round(c["center"].z,6),z,round(d,6)])

remove_temp(); setup_render()
full=cam(CAM_PREFIX+"FULL_CHARACTER_CHECK", center+Vector((0,-scale_ref*2.0,scale_ref*.36)), center,55)
left=find_cam(["DIAG_L.Arm armpit view","DIAG_L.Arm","L.Arm armpit view"],["diag","l"]) or cam(CAM_PREFIX+"HOODIE_ONLY_LEFT",center+Vector((-scale_ref*1.2,-scale_ref*.35,scale_ref*.25)),anchors["left_armpit"],100)
right=find_cam(["DIAG_R.Arm armpit view","DIAG_R.Arm","R.Arm armpit view"],["diag","r"]) or cam(CAM_PREFIX+"HOODIE_ONLY_RIGHT",center+Vector((scale_ref*1.2,-scale_ref*.35,scale_ref*.25)),anchors["right_armpit"],100)
collar=find_cam(["DIAG_Hood collar view","DIAG_Collar view","DIAG_HoodInside_Collar"],["hood","collar"]) or cam(CAM_PREFIX+"HOODIE_ONLY_COLLAR",center+Vector((0,-scale_ref*1.10,scale_ref*.50)),anchors["hood_collar_front"],95)
inside=find_cam(["DIAG_Hood inside view","DIAG_HoodInside","DIAG_Inside hood"],["hood","inside"]) or cam(CAM_PREFIX+"HOODIE_ONLY_INSIDE",center+Vector((0,-scale_ref*.55,scale_ref*.68)),anchors["hood_collar_back"],110)

camera_names={"full":full.name,"left":left.name,"right":right.name,"collar":collar.name,"inside":inside.name}
render(full,"POST_01_FullCharacterCheck.png")
prev=set_char_hidden(True)
try:
    render(left,"POST_02_HoodieOnly_LeftArmpit.png")
    render(right,"POST_03_HoodieOnly_RightArmpit.png")
    render(collar,"POST_04_HoodieOnly_HoodCollar.png")
    render(inside,"POST_05_HoodieOnly_InsideHoodCollar.png")
finally:
    restore(prev)
remove_temp()

# Restore render engine in memory but DO NOT save blend.
final_engine="UNKNOWN"
for eng in ("CYCLES","BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try:
        bpy.context.scene.render.engine=eng; final_engine=bpy.context.scene.render.engine; break
    except Exception: pass

status={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"hoodie_target":hoodie.name,"body_target":body.name,"saved_blend":False,"created_backup_blend_files":0,
"current":{"boundary_edges":len(edges),"boundary_loop_count":len(comps),"boundary_loop_sizes":[c["size"] for c in comps[:10]],"polygon_island_count":poly_count,"top_polygon_islands":top_polys,"zone_summary":zone_summary},
"comparison_to_v1F_after":{"v1F_after_edges":582,"v1F_after_loops":13,"boundary_edges_delta":len(edges)-582,"boundary_loop_delta":len(comps)-13},
"rendering":{"left_armpit_camera":camera_names["left"],"right_armpit_camera":camera_names["right"],"collar_camera":camera_names["collar"],"inside_hood_camera":camera_names["inside"],"closeups_hide_sackboy":True,"full_character_check_visible":True},
"final_render_engine_memory_only":final_engine}
for p in [os.path.join(REPORT_DIR,"SeamPatchRecoveryV1I_status.json"), os.path.join(REPORT_DIR,"seam_patch_recovery_v1I.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)
with open(os.path.join(REPORT_DIR,"SeamPatchRecoveryV1I_report.txt"),"w",encoding="utf-8") as f:
    f.write(f"SEAM PATCH RECOVERY V1I\ncurrent_boundary_edges={len(edges)}\ncurrent_boundary_loops={len(comps)}\ncurrent_polygon_islands={poly_count}\nedge_delta_vs_v1F_after={len(edges)-582}\nloop_delta_vs_v1F_after={len(comps)-13}\nleft_armpit_camera={camera_names['left']}\nright_armpit_camera={camera_names['right']}\ncloseups_hide_sackboy=True\n")
with open(os.path.join(REPORT_DIR,"Seam_Patch_Recovery_V1I.md"),"w",encoding="utf-8") as f:
    f.write(f"# Seam Patch Recovery v1I\n\n- Current boundary edges: **{len(edges)}**\n- Current boundary loops: **{len(comps)}**\n- Current polygon islands: **{poly_count}**\n- Delta vs v1F after edges: **{len(edges)-582}**\n- Delta vs v1F after loops: **{len(comps)-13}**\n- Left armpit camera: `{camera_names['left']}`\n- Right armpit camera: `{camera_names['right']}`\n\nThis package did not save the blend or change geometry.\n")
print("[v1I] seam patch recovery complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print(f"[current] boundary_edges={len(edges)} boundary_loops={len(comps)} polygon_islands={poly_count}")
print(f"[comparison_to_v1F_after] edges_delta={len(edges)-582} loops_delta={len(comps)-13}")
print(f"[rendering] left={camera_names['left']} right={camera_names['right']} closeups_hide_sackboy=True")
print("[safety] saved_blend=False created_backup_blend_files=0")
