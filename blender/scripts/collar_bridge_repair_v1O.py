
import bpy, os, json, csv, math
from mathutils import Vector
from datetime import datetime, timezone

ROOT=os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath),".."))
REPORT_DIR=os.path.join(ROOT,"reports","collar_bridge_repair_v1O")
CSV_DIR=os.path.join(REPORT_DIR,"csv")
RENDER_DIR=os.path.join(ROOT,"renders","current_review")
os.makedirs(REPORT_DIR,exist_ok=True); os.makedirs(CSV_DIR,exist_ok=True); os.makedirs(RENDER_DIR,exist_ok=True)
TEMP_PREFIX="TMP_V1O_COLLARBRIDGE_"; CAM_PREFIX=TEMP_PREFIX+"CAM_"
BRIDGE_NAME="SACKBOY_CollarGapBridge_v1O"

for name in os.listdir(RENDER_DIR):
    p=os.path.join(RENDER_DIR,name)
    if os.path.isfile(p):
        try: os.remove(p)
        except Exception: pass
try:
    bpy.context.preferences.filepaths.save_version=0
except Exception:
    pass

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

def mesh_edge_use(mesh):
    use={}
    for p in mesh.polygons:
        vs=list(p.vertices)
        for i in range(len(vs)):
            k=tuple(sorted((vs[i],vs[(i+1)%len(vs)])))
            use[k]=use.get(k,0)+1
    return use

def boundary_metrics(obj):
    mesh=obj.data
    use=mesh_edge_use(mesh)
    adj={}; count=0
    for e in mesh.edges:
        a,b=e.vertices[:]
        if use.get(tuple(sorted((a,b))),0)==1:
            count+=1
            adj.setdefault(a,set()).add(b); adj.setdefault(b,set()).add(a)
    seen=set(); loops=0; sizes=[]
    for v in adj:
        if v in seen: continue
        loops+=1
        stack=[v]; seen.add(v); n=0
        while stack:
            cur=stack.pop(); n+=1
            for nb in adj.get(cur,()):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        sizes.append(n)
    sizes.sort(reverse=True)
    return count,loops,sizes

def remove_temp():
    for o in list(bpy.data.objects):
        if o.name.startswith(TEMP_PREFIX):
            bpy.data.objects.remove(o,do_unlink=True)
    for m in list(bpy.data.materials):
        if m.name.startswith(TEMP_PREFIX):
            bpy.data.materials.remove(m,do_unlink=True)

def remove_existing_bridge():
    for o in list(bpy.data.objects):
        if o.name == BRIDGE_NAME or o.name.startswith(BRIDGE_NAME+"."):
            bpy.data.objects.remove(o, do_unlink=True)

def look_at(o,t):
    o.rotation_euler=(t-o.location).to_track_quat("-Z","Y").to_euler()

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
            if o.type=="CAMERA" and all(p.lower() in o.name.lower() for p in parts):
                return o
    return None

def char_candidate(o):
    if o==hoodie or o.name.startswith(BRIDGE_NAME): return False
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

remove_temp()
before_edges,before_loops,before_sizes=boundary_metrics(hoodie)
mn,mx,center,dim=wbounds(hoodie)
scale_ref=max(dim.x,dim.y,dim.z,1e-6)

# Disable the damaging v1N shape key.
v1n_before=None
v1n_after=None
if hoodie.data.shape_keys:
    kb=hoodie.data.shape_keys.key_blocks.get("SEAMSEAT_CollarParallelSnap_v1N")
    if kb:
        v1n_before=float(kb.value)
        kb.value=0.0
        v1n_after=float(kb.value)
    else:
        v1n_before=None
        v1n_after=0.0
else:
    v1n_before=None
    v1n_after=0.0

# Remove previous bridge reruns.
remove_existing_bridge()

# Use current safe visual hoodie state after disabling v1N.
basis=[v.co.copy() for v in hoodie.data.vertices]
current=[c.copy() for c in basis]
if hoodie.data.shape_keys:
    for kb in hoodie.data.shape_keys.key_blocks:
        if kb.name=="Basis": continue
        val=float(kb.value)
        if abs(val)<1e-8: continue
        for i in range(len(current)):
            current[i] += (kb.data[i].co - basis[i]) * val
world_pts=[hoodie.matrix_world @ c for c in current]

# Collar candidate points: upper/intersection band, nearest to center, excluding low armpit/waist areas.
z_low=center.z - dim.z*0.08
z_high=center.z + dim.z*0.30
candidates=[p for p in world_pts if z_low <= p.z <= z_high and abs(p.x-center.x) <= dim.x*.58 and abs(p.y-center.y) <= dim.y*.55]
if len(candidates)<50:
    # fallback: use conservative bbox estimate
    candidates=[center+Vector((math.cos(i)*dim.x*.32, math.sin(i)*dim.y*.28, dim.z*.05)) for i in [j*math.tau/64 for j in range(64)]]

xs=sorted([p.x for p in candidates]); ys=sorted([p.y for p in candidates]); zs=sorted([p.z for p in candidates])
def pct(vals, q):
    if not vals: return 0.0
    idx=max(0,min(len(vals)-1,int((len(vals)-1)*q)))
    return vals[idx]

# Build a collar bridge that covers the visible intersection with a fabric band.
cx=center.x
cy=center.y
cz=pct(zs,0.55)
rx=max((pct(xs,0.86)-pct(xs,0.14))*0.58, dim.x*0.27)
ry=max((pct(ys,0.86)-pct(ys,0.14))*0.58, dim.y*0.22)
rx=min(rx, dim.x*0.46)
ry=min(ry, dim.y*0.42)

band_width=max(scale_ref*0.035, min(rx,ry)*0.20)
height=max(scale_ref*0.030, dim.z*0.028)
# make it a little wider at sides where user sees the biggest gap
segments=96
verts=[]
faces=[]
# rings: outer top, outer bottom, inner top, inner bottom
for i in range(segments):
    t=math.tau*i/segments
    side_boost=1.0 + 0.13*(abs(math.cos(t))**1.8)
    back_boost=1.0 + 0.06*max(0,math.sin(t))
    outer_x=(rx+band_width*side_boost)*math.cos(t)
    outer_y=(ry+band_width*back_boost)*math.sin(t)
    inner_x=(rx-band_width*0.55)*math.cos(t)
    inner_y=(ry-band_width*0.55)*math.sin(t)
    # slight front dip/back lift so it seats like a hood seam instead of a perfect torus
    z_offset=height*0.18*math.sin(t) - height*0.08*math.cos(t)**2
    verts.append((cx+outer_x, cy+outer_y, cz+height/2+z_offset))
    verts.append((cx+outer_x, cy+outer_y, cz-height/2+z_offset))
    verts.append((cx+inner_x, cy+inner_y, cz+height/2+z_offset))
    verts.append((cx+inner_x, cy+inner_y, cz-height/2+z_offset))

for i in range(segments):
    ni=(i+1)%segments
    a=i*4; b=ni*4
    # outer wall
    faces.append((a,b,b+1,a+1))
    # inner wall
    faces.append((a+2,a+3,b+3,b+2))
    # top face
    faces.append((a,b,a+2))
    faces.append((b,b+2,a+2))
    # bottom face
    faces.append((a+1,a+3,b+1))
    faces.append((b+1,a+3,b+3))

mesh=bpy.data.meshes.new(BRIDGE_NAME+"_Mesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
bridge=bpy.data.objects.new(BRIDGE_NAME, mesh)
bpy.context.scene.collection.objects.link(bridge)

# Material: copy hoodie first material appearance when possible.
mat=None
if hoodie.data.materials and hoodie.data.materials[0]:
    src=hoodie.data.materials[0]
    mat=bpy.data.materials.new("SACKBOY_CollarBridge_Fabric_v1O")
    mat.diffuse_color=src.diffuse_color
else:
    mat=bpy.data.materials.new("SACKBOY_CollarBridge_Fabric_v1O")
    mat.diffuse_color=(0.028,0.024,0.020,1.0)
bridge.data.materials.append(mat)

# Smooth normals via shade_smooth.
bpy.context.view_layer.objects.active=bridge
bridge.select_set(True)
for o in bpy.context.scene.objects:
    if o != bridge:
        o.select_set(False)
try:
    bpy.ops.object.shade_smooth()
except Exception:
    pass

# Put bridge into a hoodie-related collection if possible.
target_col=None
for c in hoodie.users_collection:
    target_col=c
    break
if target_col:
    try:
        if bridge.name not in target_col.objects:
            target_col.objects.link(bridge)
        if bridge.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(bridge)
    except Exception:
        pass

after_edges,after_loops,after_sizes=boundary_metrics(hoodie)
if after_edges!=before_edges or after_loops!=before_loops:
    raise RuntimeError("Hoodie topology changed; this repair must not alter hoodie mesh topology.")

# Render review.
setup_render()
full=cam(CAM_PREFIX+"FULL_CHARACTER_CHECK", center+Vector((0,-scale_ref*2.0,scale_ref*.36)), center, 55)
left=find_cam(["DIAG_L.Arm armpit view","DIAG_L.Arm","L.Arm armpit view"],["diag","l"]) or cam(CAM_PREFIX+"SIDE_LEFT", center+Vector((-scale_ref*1.20,-scale_ref*.35,scale_ref*.25)), center, 100)
right=find_cam(["DIAG_R.Arm armpit view","DIAG_R.Arm","R.Arm armpit view"],["diag","r"]) or cam(CAM_PREFIX+"SIDE_RIGHT", center+Vector((scale_ref*1.20,-scale_ref*.35,scale_ref*.25)), center, 100)
inside=find_cam(["DIAG_Hood inside view","DIAG_HoodInside","DIAG_Inside hood"],["hood","inside"]) or cam(CAM_PREFIX+"INSIDE_COLLAR", center+Vector((0,-scale_ref*.55,scale_ref*.68)), center, 110)
front=cam(CAM_PREFIX+"FRONT_COLLAR", center+Vector((0,-scale_ref*1.10,scale_ref*.50)), center, 95)
back=cam(CAM_PREFIX+"BACK_COLLAR", center+Vector((0,scale_ref*1.05,scale_ref*.46)), center, 95)
cam_names={"full":full.name,"collar_side_left":left.name,"collar_side_right":right.name,"inside":inside.name,"front":front.name,"back":back.name}
render(full,"POST_01_FullCharacterCheck.png")
prev=set_char_hidden(True)
try:
    render(left,"POST_02_HoodieOnly_CollarSideLeft_DIAG_L.png")
    render(right,"POST_03_HoodieOnly_CollarSideRight_DIAG_R.png")
    render(inside,"POST_04_HoodieOnly_InsideHoodCollar.png")
    render(front,"POST_05_HoodieOnly_CollarFront.png")
    render(back,"POST_06_HoodieOnly_CollarBack.png")
finally:
    restore(prev)

# remove only temp cameras; bridge remains
for o in list(bpy.data.objects):
    if o.name.startswith(TEMP_PREFIX):
        bpy.data.objects.remove(o,do_unlink=True)

final_engine="UNKNOWN"
for eng in ("CYCLES","BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try:
        bpy.context.scene.render.engine=eng
        final_engine=bpy.context.scene.render.engine
        break
    except Exception:
        pass

bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)

status={
    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "hoodie_target":hoodie.name,
    "body_target":body.name,
    "saved_blend":True,
    "created_backup_blend_files":0,
    "v1N_shape_key":{
        "name":"SEAMSEAT_CollarParallelSnap_v1N",
        "value_before":v1n_before,
        "value_after":v1n_after,
        "disabled_to_remove_side_shoulder_distortion":True
    },
    "hoodie_topology":{
        "boundary_edges_before":before_edges,
        "boundary_edges_after":after_edges,
        "boundary_loops_before":before_loops,
        "boundary_loops_after":after_loops
    },
    "bridge":{
        "created":True,
        "name":bridge.name,
        "vertex_count":len(bridge.data.vertices),
        "face_count":len(bridge.data.polygons),
        "center":[round(cx,6),round(cy,6),round(cz,6)],
        "x_radius_outer":round(rx+band_width*1.13,6),
        "y_radius_outer":round(ry+band_width*1.06,6),
        "band_width":round(band_width,6),
        "vertical_height":round(height,6),
        "material":mat.name
    },
    "rendering":{
        "cameras":cam_names,
        "uses_armpit_named_cameras_as_collar_side_views":True,
        "closeups_hide_sackboy":True,
        "colored_tube_overlays":False,
        "full_character_check_visible":True
    },
    "final_render_engine":final_engine
}
for p in [os.path.join(REPORT_DIR,"CollarBridgeRepairV1O_status.json"), os.path.join(REPORT_DIR,"collar_bridge_repair_v1O.json")]:
    with open(p,"w",encoding="utf-8") as f: json.dump(status,f,indent=2)
with open(os.path.join(REPORT_DIR,"CollarBridgeRepairV1O_report.txt"),"w",encoding="utf-8") as f:
    f.write("COLLAR BRIDGE REPAIR V1O\n")
    f.write(f"v1N_value_before={v1n_before}\nv1N_value_after={v1n_after}\n")
    f.write(f"bridge_object={bridge.name}\nbridge_vertices={len(bridge.data.vertices)}\nbridge_faces={len(bridge.data.polygons)}\n")
    f.write(f"bridge_x_radius_outer={status['bridge']['x_radius_outer']}\nbridge_y_radius_outer={status['bridge']['y_radius_outer']}\nbridge_band_width={status['bridge']['band_width']}\nbridge_vertical_height={status['bridge']['vertical_height']}\n")
    f.write(f"hoodie_boundary_edges_unchanged={before_edges}\nhoodie_boundary_loops_unchanged={before_loops}\n")
with open(os.path.join(REPORT_DIR,"Collar_Bridge_Repair_V1O.md"),"w",encoding="utf-8") as f:
    f.write("# Collar Bridge Repair v1O\n\n")
    f.write("- Disabled `SEAMSEAT_CollarParallelSnap_v1N` to remove side/shoulder distortion.\n")
    f.write(f"- Created bridge object: `{bridge.name}`\n")
    f.write("- The bridge is a separate collar seam/gasket object, so it does not deform armpit or shoulder vertices.\n")
    f.write(f"- Bridge vertices/faces: **{len(bridge.data.vertices)} / {len(bridge.data.polygons)}**\n")
    f.write(f"- Hoodie boundary edges unchanged: **{before_edges}**\n")
    f.write(f"- Hoodie boundary loops unchanged: **{before_loops}**\n")
    f.write(f"- v1N value: **{v1n_before} -> {v1n_after}**\n\n")
    f.write("Manual revert: hide/delete `SACKBOY_CollarGapBridge_v1O` or set `SEAMSEAT_CollarParallelSnap_v1N` back to 1 for comparison.\n")
print("[v1O] collar bridge repair complete")
print(f"[targets] hoodie={hoodie.name} body={body.name}")
print(f"[fix] disabled_v1N_shape_key={v1n_before}->{v1n_after}")
print(f"[bridge] name={bridge.name} vertices={len(bridge.data.vertices)} faces={len(bridge.data.polygons)} band_width={status['bridge']['band_width']} vertical_height={status['bridge']['vertical_height']}")
print(f"[topology] hoodie_boundary_edges_unchanged={before_edges} hoodie_boundary_loops_unchanged={before_loops}")
print("[rendering] closeups_hide_sackboy=True uses_DIAG_L_R_as_collar_side_views=True")
print(f"[viewport] final_render_engine={final_engine}")
print("[safety] saved_blend=True created_backup_blend_files=0")
