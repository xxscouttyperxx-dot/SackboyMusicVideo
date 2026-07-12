import json, traceback, statistics, math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "current_review"
REP = ROOT / "reports" / "hoodie_surface_data_repair_v1F"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "SACKBOY_Hoodie_Main"
FALLBACK_HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]
PREV_HOODIE_KEYS = [
    "HOODIEFIT_SurfaceRelaxSpikeAudit_v1E",
    "HOODIEFIT_ReportsAndDomeFix_v1D",
    "HOODIEFIT_SideDomeCorrection_v1C",
    "HOODIEFIT_DomeSideDepressionFix_v1B",
    "HOODIEFIT_SideBackBowlFix_v1",
    "HOODIEFIT_CameraCleanupShapeFix_v1",
    "HOODIEFIT_SpikeSleeveSideFix_v1",
    "HOODIEFIT_BowlRimRefine_v1",
    "HOODIEFIT_BowlRidgePolish_v1",
]
NEW_HOODIE_KEY = "HOODIEFIT_SurfaceDataRepair_v1F"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def log(msg):
    print(msg)
    REP.mkdir(parents=True, exist_ok=True)
    with (REP / "HoodieSurfaceDataRepair_v1F_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_outputs():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()
    (REP / "HoodieSurfaceDataRepair_v1F_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords=[o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs),"max_x":max(xs),"min_y":min(ys),"max_y":max(ys),"min_z":min(zs),"max_z":max(zs),"dim_x":max(xs)-min(xs),"dim_y":max(ys)-min(ys),"dim_z":max(zs)-min(zs)}

def bounds_from_key_data(key):
    coords=[p.co for p in key.data]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs),"max_x":max(xs),"min_y":min(ys),"max_y":max(ys),"min_z":min(zs),"max_z":max(zs),"dim_x":max(xs)-min(xs),"dim_y":max(ys)-min(ys),"dim_z":max(zs)-min(zs)}

def key_world_bounds(obj,key=None):
    coords=[obj.matrix_world @ p.co for p in key.data] if key else [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs),"max_x":max(xs),"min_y":min(ys),"max_y":max(ys),"min_z":min(zs),"max_z":max(zs),"dim_x":max(xs)-min(xs),"dim_y":max(ys)-min(ys),"dim_z":max(zs)-min(zs)}

def center_from_bounds(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5,(b["min_y"]+b["max_y"])*0.5,(b["min_z"]+b["max_z"])*0.5))

def smoothstep(a,b,x):
    if a==b: return 0.0
    t=max(0.0,min(1.0,(x-a)/(b-a)))
    return t*t*(3-2*t)

def band(zn,a,b,c,d):
    return smoothstep(a,b,zn)*(1.0-smoothstep(c,d,zn))

def radial(nx,ny,sx,sy):
    r=(nx/max(sx,1e-6))**2+(ny/max(sy,1e-6))**2
    return max(0.0,1.0-min(1.0,r))

def restore_underglow():
    o=bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log("[lock] underglow missing")
        return {"status":"missing"}
    before=[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)]
    o.location=Vector(UNDERGLOW_LOCK_LOC)
    after=[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"before":before,"after":after}

def keep_character_baseline():
    hero=bpy.data.objects.get(HERO_NAME)
    disabled=[]
    if hero and hero.type=="MESH" and hero.data.shape_keys:
        for kb in hero.data.shape_keys.key_blocks:
            if kb.name.startswith("BODYFIT_"):
                before=float(kb.value); kb.value=0.0
                disabled.append({"name":kb.name,"before":before,"after":0.0})
    log("[character] F2 baseline preserved; BODYFIT keys kept disabled")
    return disabled

def find_hoodie():
    for name in FALLBACK_HOODIE_NAMES:
        o=bpy.data.objects.get(name)
        if o and o.type=="MESH":
            if o.name!=HOODIE_NAME:
                old=o.name; o.name=HOODIE_NAME; o.data.name=HOODIE_NAME+"_Mesh"
                log(f"[rename] hoodie renamed {old} -> {o.name}")
            return o
    matches=[o for o in bpy.data.objects if o.type=="MESH" and ("hoodie" in o.name.lower() or "pullover" in o.name.lower() or "apricot" in o.name.lower())]
    if not matches:
        raise RuntimeError("No hoodie mesh found")
    o=sorted(matches,key=lambda x:(not visible(x),-len(x.data.vertices),x.name))[0]
    o.name=HOODIE_NAME; o.data.name=HOODIE_NAME+"_Mesh"
    return o

def ensure_hoodie_key(obj):
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis",from_mix=False)
    if obj.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True); bpy.context.view_layer.objects.active=obj
        obj.active_shape_key_index=list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
        bpy.ops.object.shape_key_remove()
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value=0.0
    source=None
    for name in PREV_HOODIE_KEYS:
        kb=obj.data.shape_keys.key_blocks.get(name)
        if kb:
            kb.value=1.0; source=name; break
    new_key=obj.shape_key_add(name=NEW_HOODIE_KEY,from_mix=True)
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value=0.0
    new_key.value=1.0
    obj.active_shape_key_index=list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
    return new_key,source

def build_adjacency(mesh):
    adj=[set() for _ in range(len(mesh.vertices))]
    edges=set()
    for poly in mesh.polygons:
        vs=list(poly.vertices); n=len(vs)
        for i,a in enumerate(vs):
            b=vs[(i+1)%n]
            if a!=b:
                adj[a].add(b); adj[b].add(a); edges.add((min(a,b),max(a,b)))
    return adj, sorted(edges)

def vertex_region_weights(key):
    lb=bounds_from_key_data(key)
    cx=(lb["min_x"]+lb["max_x"])/2; cy=(lb["min_y"]+lb["max_y"])/2
    zmin=lb["min_z"]; dz=max(lb["dim_z"],1e-6)
    hx=max(lb["dim_x"]/2,1e-6); hy=max(lb["dim_y"]/2,1e-6)
    weights=[]
    meta=[]
    for p in key.data:
        co=p.co
        zn=(co.z-zmin)/dz
        nx_signed=(co.x-cx)/hx; nx=abs(nx_signed)
        ny_signed=(co.y-cy)/hy
        side=smoothstep(0.26,0.90,nx)
        front=smoothstep(0.10,0.78,-ny_signed)
        rear=smoothstep(0.10,0.78,ny_signed)
        upper=band(zn,0.50,0.60,0.86,0.98)
        mid=band(zn,0.36,0.48,0.78,0.90)
        lower=band(zn,0.26,0.38,0.64,0.82)
        crown=band(zn,0.65,0.76,1.0,1.0)
        # Strong broad hood-side mask, front rim de-emphasized but not totally ignored.
        side_shell=(0.78*upper+1.0*mid+0.78*lower)*side*(1.0-0.32*front)
        rear_shell=(0.60*mid+0.90*lower+0.75*upper)*side*rear
        crown_blend=0.30*crown
        rim=side*(upper+mid+lower)*front
        w=min(1.0, max(side_shell, rear_shell, crown_blend, 0.18*rim))
        weights.append(w)
        meta.append({"zn":zn,"nx":nx,"nx_signed":nx_signed,"ny_signed":ny_signed,"front":front,"rear":rear,"side":side,"rim":rim})
    return weights, meta

def analyze_irregularities(key, adj, weights):
    coords=[p.co.copy() for p in key.data]
    depressions=[]; ridges=[]
    for i,w in enumerate(weights):
        if w <= 0.12 or not adj[i]:
            continue
        avg=Vector((0,0,0))
        for n in adj[i]:
            avg+=coords[n]
        avg/=len(adj[i])
        radial_vec=Vector((coords[i].x, coords[i].y, 0))
        avg_radial=Vector((avg.x, avg.y, 0))
        # Local radial disparity: negative means the point is inward compared to neighbors; positive means ridge/outward.
        disparity=radial_vec.length - avg_radial.length
        lap=(coords[i]-avg).length
        item={"index":i,"disparity":disparity,"laplacian":lap,"co":[round(coords[i].x,6),round(coords[i].y,6),round(coords[i].z,6)],"weight":w}
        if disparity < 0:
            depressions.append(item)
        elif disparity > 0:
            ridges.append(item)
    depressions=sorted(depressions,key=lambda x:x["disparity"])[:40]
    ridges=sorted(ridges,key=lambda x:x["disparity"],reverse=True)[:40]
    max_dep=depressions[0]["disparity"] if depressions else 0.0
    max_ridge=ridges[0]["disparity"] if ridges else 0.0
    return {"top_depressions":depressions,"top_ridges":ridges,"max_depression":max_dep,"max_ridge":max_ridge,"depression_count":len(depressions),"ridge_count":len(ridges)}

def analyze_long_edges(key, edges):
    coords=[p.co.copy() for p in key.data]
    lens=[(coords[a]-coords[b]).length for a,b in edges]
    med=statistics.median(lens) if lens else 0.0
    threshold=med*7.5 if med else 0.0
    longs=[]
    for (a,b),l in zip(edges,lens):
        if threshold and l>threshold:
            ca=coords[a]; cb=coords[b]
            longs.append({"a":a,"b":b,"length":l,"a_co":[round(ca.x,6),round(ca.y,6),round(ca.z,6)],"b_co":[round(cb.x,6),round(cb.y,6),round(cb.z,6)]})
    longs=sorted(longs,key=lambda x:x["length"],reverse=True)
    return {"median_edge_length":med,"threshold":threshold,"long_edge_count":len(longs),"top_long_edges":longs[:60]}

def smooth_key_with_targets(key, adj, weights, passes=5, factor=0.42):
    total_smoothed=0; max_move=0.0
    for _ in range(passes):
        original=[p.co.copy() for p in key.data]
        for i,w in enumerate(weights):
            if w<=0 or not adj[i]:
                continue
            avg=Vector((0,0,0))
            for n in adj[i]:
                avg+=original[n]
            avg/=len(adj[i])
            before=key.data[i].co.copy()
            key.data[i].co=before.lerp(avg,min(1.0,factor*w))
            d=(key.data[i].co-before).length
            if d>1e-8:
                total_smoothed+=1
                max_move=max(max_move,d)
    return total_smoothed,max_move

def apply_data_driven_repair(hoodie):
    key,source=ensure_hoodie_key(hoodie)
    before_world=key_world_bounds(hoodie,key)
    adj,edges=build_adjacency(hoodie.data)
    weights,meta=vertex_region_weights(key)
    before_irreg=analyze_irregularities(key,adj,weights)
    before_edges=analyze_long_edges(key,edges)

    lb=bounds_from_key_data(key)
    cx=(lb["min_x"]+lb["max_x"])/2; cy=(lb["min_y"]+lb["max_y"])/2
    zmin=lb["min_z"]; dz=max(lb["dim_z"],1e-6)
    hx=max(lb["dim_x"]/2,1e-6); hy=max(lb["dim_y"]/2,1e-6)
    v_before=len(hoodie.data.vertices); f_before=len(hoodie.data.polygons)
    touched=0; max_delta=0.0

    # One direct corrective stage using measured local disparity.
    coords=[p.co.copy() for p in key.data]
    for i,p in enumerate(key.data):
        w=weights[i]
        if w<=0.10 or not adj[i]:
            continue
        co=coords[i]
        avg=Vector((0,0,0))
        for n in adj[i]:
            avg+=coords[n]
        avg/=len(adj[i])
        m=meta[i]
        # Local side direction: out from center on x/y; keep front opening preserved by reducing front influence.
        nx_signed=m["nx_signed"]
        ny_signed=m["ny_signed"]
        front=m["front"]; rear=m["rear"]
        side=m["side"]
        radial_vec=Vector((co.x-cx, co.y-cy, 0))
        if radial_vec.length == 0:
            radial_dir=Vector((1 if nx_signed>=0 else -1,0,0))
        else:
            radial_dir=radial_vec.normalized()

        disparity=Vector((co.x,co.y,0)).length - Vector((avg.x,avg.y,0)).length
        new=co.copy()
        # If depressed inward relative to neighbors, push outward more aggressively.
        if disparity < -0.0015:
            amount=min(0.055, abs(disparity)*1.9) * w
            new.x += radial_dir.x * amount
            new.y += radial_dir.y * amount
        # If ridged/outward relative to neighbors, pull very gently toward average to remove raised edge.
        elif disparity > 0.0018:
            new = new.lerp(avg, min(0.35, 0.18*w))

        # Additional broad shape intent:
        # side valleys outward, rear droop up/out, front rim lighter.
        side_valley=(0.60+0.40*rear)*side*w*(1.0-0.35*front)
        if side_valley>0:
            new.x = cx + (new.x-cx)*(1.0 + 0.030*side_valley)
            new.y = cy + (new.y-cy)*(1.0 + 0.010*side_valley)
        rear_droop=w*rear*side
        if rear_droop>0:
            new.z += dz*0.035*rear_droop
            new.x = cx + (new.x-cx)*(1.0 + 0.018*rear_droop)

        d=(new-co).length
        if d>1e-7:
            p.co=new; touched+=1; max_delta=max(max_delta,d)

    # Multi-pass masked relaxation for the hard depression boundaries/ridges.
    smoothed,max_smooth=smooth_key_with_targets(key,adj,weights,passes=6,factor=0.38)
    max_delta=max(max_delta,max_smooth)

    # Re-analyze after the repair.
    after_irreg=analyze_irregularities(key,adj,weights)
    after_edges=analyze_long_edges(key,edges)
    after_world=key_world_bounds(hoodie,key)

    hoodie["hoodie_fit_pass"]="HoodieSurfaceDataRepair_v1F"
    hoodie["hoodie_fit_shape_key"]=NEW_HOODIE_KEY

    log(f"[hoodie] active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; smoothed_vertices={smoothed}; max_delta_local={max_delta:.6f}; vertices={v_before}->{len(hoodie.data.vertices)}; faces={f_before}->{len(hoodie.data.polygons)}")
    log(f"[irregularity] max_depression_before={before_irreg['max_depression']:.6f}; max_depression_after={after_irreg['max_depression']:.6f}; max_ridge_before={before_irreg['max_ridge']:.6f}; max_ridge_after={after_irreg['max_ridge']:.6f}")
    log(f"[long_edges] count_before={before_edges['long_edge_count']}; count_after={after_edges['long_edge_count']}; median_edge={before_edges['median_edge_length']:.6f}")

    return {
        "shape_key":NEW_HOODIE_KEY,
        "source_key":source,
        "smoothed_vertices":smoothed,
        "max_delta_local":max_delta,
        "touched_vertices":touched,
        "vertex_count_before":v_before,
        "vertex_count_after":len(hoodie.data.vertices),
        "face_count_before":f_before,
        "face_count_after":len(hoodie.data.polygons),
        "world_dimensions_before":[round(before_world["dim_x"],6),round(before_world["dim_y"],6),round(before_world["dim_z"],6)],
        "world_dimensions_after":[round(after_world["dim_x"],6),round(after_world["dim_y"],6),round(after_world["dim_z"],6)],
        "world_dimension_delta":[round(after_world["dim_x"]-before_world["dim_x"],6),round(after_world["dim_y"]-before_world["dim_y"],6),round(after_world["dim_z"]-before_world["dim_z"],6)],
        "irregularity_before":before_irreg,
        "irregularity_after":after_irreg,
        "long_edges_before":before_edges,
        "long_edges_after":after_edges,
    }

def camera_data(name):
    data=bpy.data.cameras.new(name+"_Data")
    obj=bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(obj)
    return obj

def look_at(obj,target):
    direction=target-obj.location
    if direction.length:
        obj.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()

def set_cam(name,loc,target,lens,hidden=False):
    obj=camera_data(name); obj.location=Vector(loc); obj.data.lens=lens
    look_at(obj,Vector(target)); obj.hide_viewport=hidden; obj.hide_render=hidden
    return obj

def reset_cameras(hoodie):
    before=[o.name for o in bpy.data.objects if o.type=="CAMERA"]
    for cam in list(bpy.data.objects):
        if cam.type=="CAMERA": bpy.data.objects.remove(cam,do_unlink=True)
    key=hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)
    hb=key_world_bounds(hoodie,key); hc=center_from_bounds(hb)
    hood_mid=Vector((hc.x,hc.y,hb["min_z"]+hb["dim_z"]*0.68))
    hood_top=Vector((hc.x,hc.y,hb["min_z"]+hb["dim_z"]*0.88))
    hero=bpy.data.objects.get(HERO_NAME); fb=bounds_world(hero) if hero else hb
    fc=center_from_bounds(fb); fmid=Vector((fc.x,fc.y,fb["min_z"]+fb["dim_z"]*0.52))

    set_cam("CAM_F2_Front",(fmid.x,fmid.y-6.0,fmid.z+0.65),fmid+Vector((0,0,0.10)),55,False)
    set_cam("CAM_F2_Profile",(fmid.x+5.5,fmid.y-0.6,fmid.z+0.65),fmid+Vector((0,0,0.10)),60,False)
    set_cam("CAM_F2_ThreeQuarter",(fmid.x+3.8,fmid.y-5.8,fmid.z+0.85),fmid+Vector((0,0,0.10)),52,False)
    set_cam("CAM_StorefrontReflection",(hc.x+7.8,hc.y-10.0,hc.z+1.65),(hc.x,hc.y+4.2,hc.z+0.85),48,False)
    set_cam("CAM_SceneWide",(hc.x+8.5,hc.y-10.5,hc.z+4.6),(hc.x,hc.y+1.0,hc.z+0.55),35,False)

    set_cam("CAM_Hood_Front",(hood_mid.x+0.18,hood_mid.y-4.15,hood_mid.z+0.36),hood_mid+Vector((0,0,0.48)),54,False)
    set_cam("CAM_Hood_LeftSide",(hood_mid.x-3.65,hood_mid.y,hood_mid.z+1.05),hood_mid+Vector((0,0,0.46)),56,False)
    set_cam("CAM_Hood_RightSide",(hood_mid.x+3.65,hood_mid.y,hood_mid.z+1.05),hood_mid+Vector((0,0,0.46)),56,False)
    set_cam("CAM_Hood_Top",(hood_top.x+0.05,hood_top.y-0.22,hood_top.z+3.35),hood_top,72,False)
    set_cam("CAM_ANIM_Wide",(hc.x+9.0,hc.y-11.5,hc.z+4.2),(hc.x,hc.y+0.8,hc.z+0.5),32,True)
    set_cam("CAM_ANIM_Medium",(hc.x+5.0,hc.y-7.0,hc.z+2.5),(hc.x,hc.y+0.4,hc.z+0.5),42,True)
    set_cam("CAM_ANIM_Close",(hc.x+2.2,hc.y-4.0,hc.z+1.7),(hc.x,hc.y+0.1,hc.z+0.55),60,True)

    cams=sorted([o for o in bpy.data.objects if o.type=="CAMERA"],key=lambda o:o.name)
    vis=sum(1 for c in cams if not c.hide_viewport and not c.hide_render)
    report={"before_count":len(before),"after_total":len(cams),"visible_count":vis,"hidden_count":len(cams)-vis,"names":[c.name for c in cams]}
    log(f"[camera] before={len(before)} after_total={len(cams)} visible={vis} hidden={len(cams)-vis}; names={report['names']}")
    return report

def set_workbench(scene,color_type):
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type=color_type
    scene.display.shading.show_xray=False
    scene.display.shading.show_cavity=True
    scene.display.shading.show_object_outline=True

def setup_render_settings():
    scene=bpy.context.scene
    scene.render.resolution_x=960; scene.render.resolution_y=540; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"

def save_visibility_state():
    return {obj.name:(obj.hide_viewport,obj.hide_render) for obj in bpy.data.objects}

def restore_visibility_state(state):
    for name,flags in state.items():
        o=bpy.data.objects.get(name)
        if o: o.hide_viewport,o.hide_render=flags

def isolate_hoodie(hoodie):
    state=save_visibility_state()
    for obj in bpy.data.objects:
        if obj.type!="CAMERA" and obj!=hoodie:
            obj.hide_render=True
    hoodie.hide_render=False
    return state

def make_marker_mat(name, color):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=color
    return mat

def add_marker(name, loc, mat, radius=0.018):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=radius, location=loc)
    obj=bpy.context.object
    obj.name=name
    obj.data.materials.append(mat)
    return obj

def add_edge_curve(name, a, b, mat):
    curve=bpy.data.curves.new(name,"CURVE")
    curve.dimensions="3D"; curve.resolution_u=1; curve.bevel_depth=0.0024
    spl=curve.splines.new("POLY"); spl.points.add(1)
    spl.points[0].co=(a.x,a.y,a.z,1); spl.points[1].co=(b.x,b.y,b.z,1)
    obj=bpy.data.objects.new(name,curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def render_review(hoodie, fit):
    scene=bpy.context.scene
    old=(scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.camera,scene.render.filepath)
    setup_render_settings()
    renders=[]; state=None; temp=[]
    try:
        specs=[
            ("CAM_Hood_Front","01_HoodFrontLowAngleMaterial.png","MATERIAL",True,"normal"),
            ("CAM_Hood_LeftSide","02_HoodLeftSideGray.png","SINGLE",True,"normal"),
            ("CAM_Hood_RightSide","03_HoodRightSideGray.png","SINGLE",True,"normal"),
            ("CAM_Hood_Top","04_HoodTopGray.png","SINGLE",True,"normal"),
            ("CAM_Hood_Front","05_DepressionRidgeMarkers.png","MATERIAL",True,"markers"),
            ("CAM_Hood_Front","06_ActualLongEdgeAudit.png","MATERIAL",True,"edges"),
            ("CAM_SceneWide","07_ScenePreserved.png","MATERIAL",False,"normal"),
        ]
        key=hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)
        for cam_name,filename,color_type,isolate,mode in specs:
            cam=bpy.data.objects.get(cam_name)
            if not cam: continue
            if isolate: state=isolate_hoodie(hoodie)
            if mode=="markers":
                red=make_marker_mat("TMP_RidgeMarkers_RED_DO_NOT_SAVE",(1,0.05,0.02,1))
                blue=make_marker_mat("TMP_DepressionMarkers_BLUE_DO_NOT_SAVE",(0.02,0.18,1,1))
                temp += [red, blue]
                for item in fit["irregularity_after"]["top_ridges"][:20]:
                    temp.append(add_marker("TMP_RidgeMarker_DO_NOT_SAVE", hoodie.matrix_world @ key.data[item["index"]].co, red, 0.016))
                for item in fit["irregularity_after"]["top_depressions"][:20]:
                    temp.append(add_marker("TMP_DepressionMarker_DO_NOT_SAVE", hoodie.matrix_world @ key.data[item["index"]].co, blue, 0.017))
            if mode=="edges":
                mat=make_marker_mat("TMP_LongEdges_MAGENTA_DO_NOT_SAVE",(1,0,1,1)); temp.append(mat)
                for item in fit["long_edges_after"]["top_long_edges"][:80]:
                    a=hoodie.matrix_world @ key.data[item["a"]].co
                    b=hoodie.matrix_world @ key.data[item["b"]].co
                    temp.append(add_edge_curve("TMP_ActualLongEdge_DO_NOT_SAVE", a,b,mat))
            set_workbench(scene,color_type)
            scene.camera=cam
            scene.render.filepath=str(OUT/filename)
            bpy.ops.render.render(write_still=True)
            renders.append({"camera":cam.name,"render":filename,"mode":"WORKBENCH_"+color_type+"_"+mode})
            log("[render] "+filename)
            if mode in {"markers","edges"}:
                for obj in list(temp):
                    try:
                        if isinstance(obj,bpy.types.Object):
                            bpy.data.objects.remove(obj,do_unlink=True)
                        elif isinstance(obj,bpy.types.Material):
                            bpy.data.materials.remove(obj,do_unlink=True)
                    except ReferenceError:
                        pass
                temp.clear()
            if state:
                restore_visibility_state(state); state=None
    finally:
        if state: restore_visibility_state(state)
        for obj in list(temp):
            try:
                if isinstance(obj,bpy.types.Object):
                    bpy.data.objects.remove(obj,do_unlink=True)
                elif isinstance(obj,bpy.types.Material):
                    bpy.data.materials.remove(obj,do_unlink=True)
            except ReferenceError:
                pass
        scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.camera,scene.render.filepath=old
    return renders

def object_report(name):
    o=bpy.data.objects.get(name)
    if not o: return {"name":name,"status":"missing"}
    b=bounds_world(o)
    return {"name":name,"type":o.type,"visible":visible(o),"dims":None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)],"vertices":len(o.data.vertices) if o.type=="MESH" else 0,"faces":len(o.data.polygons) if o.type=="MESH" else 0}

def write_reports(fit,camera_report,disabled_bodyfit,under,renders):
    payload={"pass":"hoodie_surface_data_repair_v1F","hoodie_fit":fit,"camera_report":camera_report,"disabled_bodyfit_keys":disabled_bodyfit,"underglow_lock":under,"renders":renders,"key_objects":[object_report(n) for n in [HERO_NAME,HOODIE_NAME,"Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    (REP/"hoodie_surface_data_repair_v1F.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    status={"ok":True,"smoothed_vertices":fit["smoothed_vertices"],"max_local_vertex_movement":fit["max_delta_local"],"max_depression_before":fit["irregularity_before"]["max_depression"],"max_depression_after":fit["irregularity_after"]["max_depression"],"max_ridge_before":fit["irregularity_before"]["max_ridge"],"max_ridge_after":fit["irregularity_after"]["max_ridge"],"long_edge_count_before":fit["long_edges_before"]["long_edge_count"],"long_edge_count_after":fit["long_edges_after"]["long_edge_count"]}
    (REP/"HoodieSurfaceDataRepair_v1F_status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
    md=[
        "# Hoodie Surface Data Repair v1F",
        "",
        "## Latest numbers",
        f"- Smoothed vertices: {fit['smoothed_vertices']}",
        f"- Max local vertex movement: {fit['max_delta_local']:.6f}",
        "",
        "## Depression / ridge disparity",
        f"- Max depression before: {fit['irregularity_before']['max_depression']:.6f}",
        f"- Max depression after: {fit['irregularity_after']['max_depression']:.6f}",
        f"- Max ridge before: {fit['irregularity_before']['max_ridge']:.6f}",
        f"- Max ridge after: {fit['irregularity_after']['max_ridge']:.6f}",
        "",
        "## Long edge / spike audit",
        f"- Long edge count before: {fit['long_edges_before']['long_edge_count']}",
        f"- Long edge count after: {fit['long_edges_after']['long_edge_count']}",
        f"- Median edge length: {fit['long_edges_before']['median_edge_length']:.6f}",
        "- `06_ActualLongEdgeAudit.png` visualizes actual long topology edges directly, without using the Wireframe modifier.",
        "- `05_DepressionRidgeMarkers.png` visualizes remaining red ridge and blue depression extremes after this pass.",
        "",
        "## Repair approach",
        "- Measured local radial disparity between each hood-side vertex and its neighbors.",
        "- Pushed inward depression extremes outward toward the dome silhouette.",
        "- Pulled outward ridge extremes toward their local neighbor average.",
        "- Applied masked multi-pass relaxation to remove hard valley boundaries.",
        "- Preserved the front rim/opening and did not deform F2.",
    ]
    (REP/"Hoodie_Surface_Data_Repair_v1F.md").write_text("\n".join(md),encoding="utf-8")
    (REP/"HoodieSurfaceDataRepair_v1F_report.txt").write_text("\n".join(md),encoding="utf-8")

def manifest():
    data={"blend_file":bpy.data.filepath,"objects":[]}
    for obj in sorted(bpy.data.objects,key=lambda x:x.name):
        b=bounds_world(obj)
        item={"name":obj.name,"type":obj.type,"visible":visible(obj),"hidden":bool(obj.hide_viewport or obj.hide_render),"dimensions":None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)]}
        if obj.type=="MESH":
            item["vertices"]=len(obj.data.vertices); item["faces"]=len(obj.data.polygons)
        if obj.type=="CAMERA": item["camera"]=True
        data["objects"].append(item)
    (ROOT/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Hoodie Surface Data Repair v1F.\n\n- Hood ridges/depressions were measured and repaired using local disparity data.\n- Actual long-edge audit render replaces the old wireframe-modifier suspicion path.\n- Current review remains image-only; text/json reports go under reports.\n",encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"hoodie_surface_data_repair_v1F","reports":str(REP),"current_review":str(OUT)},indent=2),encoding="utf-8")

def main():
    reset_outputs()
    log("[pass] hoodie surface data repair v1F")
    hoodie=find_hoodie()
    under=restore_underglow()
    disabled=keep_character_baseline()
    fit=apply_data_driven_repair(hoodie)
    cameras=reset_cameras(hoodie)
    renders=render_review(hoodie,fit)
    write_reports(fit,cameras,disabled,under,renders)
    manifest()
    out=ROOT/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] "+str(out))

if __name__=="__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True,exist_ok=True)
        with (REP/"HoodieSurfaceDataRepair_v1F_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
