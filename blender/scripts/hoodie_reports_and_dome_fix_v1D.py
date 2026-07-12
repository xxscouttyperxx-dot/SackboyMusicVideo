import json, traceback, re, shutil
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "current_review"
PROJECT_CHANGES = ROOT / "renders" / "Project changes"
REP = ROOT / "reports" / "hoodie_reports_and_dome_fix_v1D"
REPORTS = ROOT / "reports"
AUD = ROOT / "reports" / "project_workflow_audit"

HERO_NAME = "F2"
HOODIE_NAME = "SACKBOY_Hoodie_Main"
FALLBACK_HOODIE_NAMES = ["SACKBOY_Hoodie_Main", "Apricot Pullover Hoodie"]
PREV_HOODIE_KEYS = [
    "HOODIEFIT_SideDomeCorrection_v1C",
    "HOODIEFIT_DomeSideDepressionFix_v1B",
    "HOODIEFIT_SideBackBowlFix_v1",
    "HOODIEFIT_CameraCleanupShapeFix_v1",
    "HOODIEFIT_SpikeSleeveSideFix_v1",
    "HOODIEFIT_BowlRimRefine_v1",
    "HOODIEFIT_BowlRidgePolish_v1",
    "HOODIEFIT_TopArtifactFix_v1",
    "HOODIEFIT_RimCrownContain_v1",
    "HOODIEFIT_CrownSmoothExpand_v1",
    "HOODIEFIT_CrownSleeveTaper_v1",
    "HOODIEFIT_NarrowSackboy_v1",
]
NEW_HOODIE_KEY = "HOODIEFIT_ReportsAndDomeFix_v1D"

UNDERGLOW_NAME = "HERO_CyanUnderglow_Area"
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)

def snake_from_camel(name):
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower().strip("_")

def report_prefix(filename):
    stem = Path(filename).stem
    for suffix in ["_FATAL_ERROR", "_build_report", "_report", "_status"]:
        if stem.endswith(suffix):
            return stem[:-len(suffix)]
    return stem

def migrate_project_changes():
    moved = []
    if PROJECT_CHANGES.exists():
        for p in sorted(PROJECT_CHANGES.glob("*")):
            if not p.is_file() or p.suffix.lower() not in {".txt", ".json", ".md"}:
                continue
            prefix = report_prefix(p.name)
            dest_dir = REPORTS / snake_from_camel(prefix)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / p.name
            if dest.exists():
                dest = dest_dir / (p.stem + "_from_project_changes" + p.suffix)
            shutil.move(str(p), str(dest))
            moved.append({"from": str(p), "to": str(dest)})
        try:
            PROJECT_CHANGES.rmdir()
        except OSError:
            pass
    return moved

def log(msg):
    print(msg)
    REP.mkdir(parents=True, exist_ok=True)
    with (REP / "HoodieReportsAndDomeFix_v1D_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_outputs():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()
    (REP / "HoodieReportsAndDomeFix_v1D_report.txt").write_text("", encoding="utf-8")

def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o, "bound_box"):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def bounds_from_key_data(key):
    coords = [p.co for p in key.data]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def key_world_bounds(obj, key=None):
    if key:
        coords = [obj.matrix_world @ p.co for p in key.data]
    else:
        coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {"min_x":min(xs), "max_x":max(xs), "min_y":min(ys), "max_y":max(ys), "min_z":min(zs), "max_z":max(zs),
            "dim_x":max(xs)-min(xs), "dim_y":max(ys)-min(ys), "dim_z":max(zs)-min(zs)}

def center_from_bounds(b):
    return Vector(((b["min_x"]+b["max_x"])*0.5, (b["min_y"]+b["max_y"])*0.5, (b["min_z"]+b["max_z"])*0.5))

def smoothstep(a,b,x):
    if a == b: return 0.0
    t = max(0.0, min(1.0, (x-a)/(b-a)))
    return t*t*(3-2*t)

def band(zn,a,b,c,d):
    return smoothstep(a,b,zn) * (1-smoothstep(c,d,zn))

def radial(nx,ny,sx,sy):
    r = (nx/max(sx,1e-6))**2 + (ny/max(sy,1e-6))**2
    return max(0, 1-min(1,r))

def restore_underglow():
    o = bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log("[lock] underglow missing")
        return {"name": UNDERGLOW_NAME, "status": "missing"}
    before = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    log(f"[lock] underglow locked {before} -> {after}")
    return {"before": before, "after": after}

def keep_character_baseline():
    hero = bpy.data.objects.get(HERO_NAME)
    disabled = []
    if hero and hero.type == "MESH" and hero.data.shape_keys:
        for kb in hero.data.shape_keys.key_blocks:
            if kb.name.startswith("BODYFIT_"):
                before = float(kb.value)
                kb.value = 0.0
                disabled.append({"name": kb.name, "before": before, "after": 0.0})
    log("[character] F2 baseline preserved; BODYFIT keys kept disabled")
    return disabled

def find_hoodie():
    for name in FALLBACK_HOODIE_NAMES:
        o = bpy.data.objects.get(name)
        if o and o.type == "MESH":
            if o.name != HOODIE_NAME:
                old = o.name
                o.name = HOODIE_NAME
                o.data.name = HOODIE_NAME + "_Mesh"
                log(f"[rename] hoodie renamed {old} -> {o.name}")
            return o
    matches = [o for o in bpy.data.objects if o.type == "MESH" and ("hoodie" in o.name.lower() or "pullover" in o.name.lower() or "apricot" in o.name.lower())]
    if not matches:
        raise RuntimeError("No hoodie mesh found")
    o = sorted(matches, key=lambda x: (not visible(x), -len(x.data.vertices), x.name))[0]
    o.name = HOODIE_NAME
    o.data.name = HOODIE_NAME + "_Mesh"
    return o

def ensure_hoodie_key(obj):
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    if obj.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
        bpy.ops.object.shape_key_remove()
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value = 0.0
    source = None
    for name in PREV_HOODIE_KEYS:
        kb = obj.data.shape_keys.key_blocks.get(name)
        if kb:
            kb.value = 1.0
            source = name
            break
    new_key = obj.shape_key_add(name=NEW_HOODIE_KEY, from_mix=True)
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith("HOODIEFIT_"):
            kb.value = 0.0
    new_key.value = 1.0
    obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
    return new_key, source

def build_adjacency(mesh):
    adj = [set() for _ in range(len(mesh.vertices))]
    for poly in mesh.polygons:
        vs = list(poly.vertices)
        n = len(vs)
        for i,a in enumerate(vs):
            for b in (vs[(i-1)%n], vs[(i+1)%n]):
                if a != b:
                    adj[a].add(b); adj[b].add(a)
    return adj

def smooth_region(key, adjacency, weights, factor=0.34):
    original = [p.co.copy() for p in key.data]
    count=0; max_fix=0.0
    for i,w in enumerate(weights):
        if w <= 0: continue
        nbrs = adjacency[i]
        if not nbrs: continue
        avg = Vector((0,0,0))
        for n in nbrs: avg += original[n]
        avg /= len(nbrs)
        before = key.data[i].co.copy()
        key.data[i].co = before.lerp(avg, min(1.0, factor*w))
        d = (key.data[i].co-before).length
        if d > 1e-8:
            count += 1; max_fix = max(max_fix, d)
    return count, max_fix

def apply_deformation(hoodie):
    key, source = ensure_hoodie_key(hoodie)
    before_world = key_world_bounds(hoodie, key)
    lb = bounds_from_key_data(key)
    cx=(lb["min_x"]+lb["max_x"])/2; cy=(lb["min_y"]+lb["max_y"])/2
    zmin=lb["min_z"]; dz=max(lb["dim_z"],1e-6)
    hx=max(lb["dim_x"]/2,1e-6); hy=max(lb["dim_y"]/2,1e-6)
    v_before=len(hoodie.data.vertices); f_before=len(hoodie.data.polygons)
    touched=0; max_delta=0; weights=[0.0]*len(key.data)
    counts={"front_depressions_down_out":0, "rear_droop_up_out":0, "side_feather":0}

    for i,p in enumerate(key.data):
        co=p.co.copy()
        zn=(co.z-zmin)/dz
        nx_signed=(co.x-cx)/hx; nx=abs(nx_signed)
        ny_signed=(co.y-cy)/hy; ny=abs(ny_signed)
        side=smoothstep(0.34,0.88,nx)
        center=radial(nx,ny,0.82,0.92)
        wide=radial(nx,ny,1.14,1.10)
        front=smoothstep(0.12,0.78,-ny_signed)
        rear=smoothstep(0.12,0.78,ny_signed)

        upper=band(zn,0.52,0.62,0.84,0.94)
        mid=band(zn,0.40,0.50,0.74,0.86)
        lower=band(zn,0.30,0.40,0.62,0.78)
        rear_mid=band(zn,0.35,0.48,0.78,0.94)
        rear_low=band(zn,0.28,0.38,0.62,0.80)
        crown=band(zn,0.68,0.78,1.0,1.0)
        new=co.copy()

        front_w=(0.80*mid + 0.50*upper + 0.40*lower)*side*front*(1-0.30*center)
        if front_w>0:
            # Front view correction: left moves down/left, right down/right.
            new.x = cx + (new.x-cx)*(1 + 0.050*front_w)
            new.z -= dz*0.025*front_w
            new.y = cy + (new.y-cy)*(1 + 0.006*front_w)
            weights[i]=max(weights[i],0.75*front_w)

        rear_w=(0.80*rear_mid + 0.55*rear_low)*side*rear*(0.45+0.55*wide)
        if rear_w>0:
            # Side view correction: right side up/right, left side up/left.
            new.x = cx + (new.x-cx)*(1 + 0.045*rear_w)
            new.z += dz*0.052*rear_w
            new.y = cy + (new.y-cy)*(1 + 0.006*rear_w)
            weights[i]=max(weights[i],0.75*rear_w)

        feather=(0.35*upper+0.45*mid+0.25*lower)*side*(1-0.20*front)
        if feather>0:
            new.x = cx + (new.x-cx)*(1 + 0.010*feather)
            weights[i]=max(weights[i],0.58*feather)

        if crown>0:
            weights[i]=max(weights[i],0.30*crown*(0.5+0.5*center))

        delta=(new-co).length
        if delta>1e-7:
            if front_w>0.08: counts["front_depressions_down_out"] += 1
            if rear_w>0.08: counts["rear_droop_up_out"] += 1
            if feather>0.08: counts["side_feather"] += 1
            p.co=new
            touched+=1
            max_delta=max(max_delta,delta)

    smoothed, max_smooth = smooth_region(key, build_adjacency(hoodie.data), weights, factor=0.34)
    max_delta=max(max_delta,max_smooth)
    after_world=key_world_bounds(hoodie,key)
    hoodie["hoodie_fit_pass"]="HoodieReportsAndDomeFix_v1D"
    hoodie["hoodie_fit_shape_key"]=NEW_HOODIE_KEY
    log(f"[hoodie] active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; smoothed_vertices={smoothed}; max_delta_local={max_delta:.6f}; vertices={v_before}->{len(hoodie.data.vertices)}; faces={f_before}->{len(hoodie.data.polygons)}")
    return {
        "shape_key": NEW_HOODIE_KEY,
        "source_key": source,
        "touched_vertices": touched,
        "smoothed_vertices": smoothed,
        "max_delta_local": max_delta,
        "vertex_count_before": v_before,
        "vertex_count_after": len(hoodie.data.vertices),
        "vertex_count_delta": len(hoodie.data.vertices)-v_before,
        "face_count_before": f_before,
        "face_count_after": len(hoodie.data.polygons),
        "face_count_delta": len(hoodie.data.polygons)-f_before,
        "world_dimensions_before": [round(before_world["dim_x"],6), round(before_world["dim_y"],6), round(before_world["dim_z"],6)],
        "world_dimensions_after": [round(after_world["dim_x"],6), round(after_world["dim_y"],6), round(after_world["dim_z"],6)],
        "world_dimension_delta": [round(after_world["dim_x"]-before_world["dim_x"],6), round(after_world["dim_y"]-before_world["dim_y"],6), round(after_world["dim_z"]-before_world["dim_z"],6)],
        "region_counts": counts,
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

def set_cam(name, loc, target, lens, hidden=False):
    obj=camera_data(name)
    obj.location=Vector(loc); obj.data.lens=lens
    look_at(obj,Vector(target))
    obj.hide_viewport=hidden; obj.hide_render=hidden
    return obj

def reset_cameras(hoodie):
    before=[o.name for o in bpy.data.objects if o.type=="CAMERA"]
    for cam in list(bpy.data.objects):
        if cam.type=="CAMERA":
            bpy.data.objects.remove(cam, do_unlink=True)
    key=hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)
    hb=key_world_bounds(hoodie,key); hc=center_from_bounds(hb)
    hood_mid=Vector((hc.x,hc.y,hb["min_z"]+hb["dim_z"]*0.68))
    hood_top=Vector((hc.x,hc.y,hb["min_z"]+hb["dim_z"]*0.88))
    hero=bpy.data.objects.get(HERO_NAME)
    fb=bounds_world(hero) if hero else hb
    fc=center_from_bounds(fb); fmid=Vector((fc.x,fc.y,fb["min_z"]+fb["dim_z"]*0.52))

    set_cam("CAM_F2_Front",(fmid.x,fmid.y-6.0,fmid.z+0.65),fmid+Vector((0,0,0.10)),55,False)
    set_cam("CAM_F2_Profile",(fmid.x+5.5,fmid.y-0.6,fmid.z+0.65),fmid+Vector((0,0,0.10)),60,False)
    set_cam("CAM_F2_ThreeQuarter",(fmid.x+3.8,fmid.y-5.8,fmid.z+0.85),fmid+Vector((0,0,0.10)),52,False)
    set_cam("CAM_StorefrontReflection",(hc.x+7.8,hc.y-10.0,hc.z+1.65),(hc.x,hc.y+4.2,hc.z+0.85),48,False)
    set_cam("CAM_SceneWide",(hc.x+8.5,hc.y-10.5,hc.z+4.6),(hc.x,hc.y+1.0,hc.z+0.55),35,False)

    # Front camera lowered and aimed upward at hood.
    set_cam("CAM_Hood_Front",(hood_mid.x+0.18,hood_mid.y-3.95,hood_mid.z+0.42),hood_mid+Vector((0,0,0.42)),56,False)
    set_cam("CAM_Hood_LeftSide",(hood_mid.x-3.50,hood_mid.y,hood_mid.z+0.95),hood_mid+Vector((0,0,0.36)),58,False)
    set_cam("CAM_Hood_RightSide",(hood_mid.x+3.50,hood_mid.y,hood_mid.z+0.95),hood_mid+Vector((0,0,0.36)),58,False)
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
    for name, flags in state.items():
        o=bpy.data.objects.get(name)
        if o: o.hide_viewport,o.hide_render=flags

def isolate_hoodie(hoodie):
    state=save_visibility_state()
    for obj in bpy.data.objects:
        if obj.type!="CAMERA" and obj != hoodie:
            obj.hide_render=True
    hoodie.hide_render=False
    return state

def create_wire(hoodie):
    dup=hoodie.copy(); dup.data=hoodie.data.copy()
    dup.name="TMP_Hoodie_WireOverlay_DO_NOT_SAVE"; dup.data.name="TMP_Hoodie_WireOverlay_Mesh"
    bpy.context.scene.collection.objects.link(dup)
    if dup.data.shape_keys:
        for kb in dup.data.shape_keys.key_blocks:
            kb.value=1.0 if kb.name==NEW_HOODIE_KEY else 0.0
    mat=bpy.data.materials.new("TMP_Wire_Black_DO_NOT_SAVE")
    mat.diffuse_color=(0,0,0,1)
    dup.data.materials.clear(); dup.data.materials.append(mat)
    mod=dup.modifiers.new("TMP_RenderWire","WIREFRAME")
    mod.thickness=0.0018; mod.use_even_offset=True; mod.use_replace=False
    return dup, mat

def render_review(hoodie):
    scene=bpy.context.scene
    old=(scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.camera,scene.render.filepath)
    setup_render_settings()
    renders=[]; wire_obj=None; wire_mat=None; state=None
    try:
        specs=[
            ("CAM_Hood_Front","01_HoodFrontLowAngleMaterial.png","MATERIAL",True,False),
            ("CAM_Hood_LeftSide","02_HoodLeftSideGray.png","SINGLE",True,False),
            ("CAM_Hood_RightSide","03_HoodRightSideGray.png","SINGLE",True,False),
            ("CAM_Hood_Top","04_HoodTopGray.png","SINGLE",True,False),
            ("CAM_Hood_Front","05_HoodIsolatedWireCheck.png","SINGLE",True,True),
            ("CAM_SceneWide","06_ScenePreserved.png","MATERIAL",False,False),
        ]
        for cam_name,filename,color_type,isolate,wire in specs:
            cam=bpy.data.objects.get(cam_name)
            if not cam: continue
            if isolate: state=isolate_hoodie(hoodie)
            if wire:
                wire_obj,wire_mat=create_wire(hoodie)
                center=center_from_bounds(key_world_bounds(hoodie,hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY)))
                original=cam.location.copy()
                direction=(cam.location-center).normalized()
                cam.location=cam.location+direction*1.55
                cam.location.z+=0.52
                look_at(cam,center+Vector((0,0,0.30)))
            set_workbench(scene,color_type)
            scene.camera=cam; scene.render.filepath=str(OUT/filename)
            bpy.ops.render.render(write_still=True)
            renders.append({"camera":cam.name,"render":filename,"mode":"WORKBENCH_"+color_type+("_ISOLATED_WIRE" if wire else "_HOODIE_ISOLATED" if isolate else "")})
            log("[render] "+filename)
            if wire:
                cam.location=original
                if wire_obj: bpy.data.objects.remove(wire_obj,do_unlink=True); wire_obj=None
                if wire_mat: bpy.data.materials.remove(wire_mat,do_unlink=True); wire_mat=None
            if state:
                restore_visibility_state(state); state=None
    finally:
        if state: restore_visibility_state(state)
        if wire_obj: bpy.data.objects.remove(wire_obj,do_unlink=True)
        if wire_mat: bpy.data.materials.remove(wire_mat,do_unlink=True)
        scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.camera,scene.render.filepath=old
    return renders

def object_report(name):
    obj=bpy.data.objects.get(name)
    if not obj: return {"name":name,"status":"missing"}
    b=bounds_world(obj)
    return {"name":name,"type":obj.type,"visible":visible(obj),"dims":None if not b else [round(b["dim_x"],6),round(b["dim_y"],6),round(b["dim_z"],6)],"vertices":len(obj.data.vertices) if obj.type=="MESH" else 0,"faces":len(obj.data.polygons) if obj.type=="MESH" else 0}

def write_reports(migrated, hoodie_fit, camera_report, disabled_bodyfit, under, renders):
    payload={"pass":"hoodie_reports_and_dome_fix_v1D","migrated_project_changes":migrated,"hoodie_fit":hoodie_fit,"camera_report":camera_report,"disabled_bodyfit_keys":disabled_bodyfit,"underglow_lock":under,"renders":renders,"key_objects":[object_report(n) for n in [HERO_NAME,HOODIE_NAME,"Cargo pants","Plane.001","Plane.022","Asphalt ground","Audi e-tron GT quattro Black"]]}
    (REP/"hoodie_reports_and_dome_fix_v1D.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    status={"ok":True,"migrated_project_change_files":len(migrated),"smoothed_vertices":hoodie_fit["smoothed_vertices"],"max_local_vertex_movement":hoodie_fit["max_delta_local"],"camera_total":camera_report["after_total"]}
    (REP/"HoodieReportsAndDomeFix_v1D_status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
    md=[
        "# Hoodie Reports and Dome Fix v1D",
        "",
        "## Latest numbers",
        f"- Smoothed vertices: {hoodie_fit['smoothed_vertices']}",
        f"- Max local vertex movement: {hoodie_fit['max_delta_local']:.6f}",
        "",
        "## Report migration",
        f"- Moved text/json files from `renders/Project changes` into `reports/<matching_pass_folder>`: {len(migrated)} files.",
        "- `renders/Project changes` is removed when empty.",
        "",
        "## Shape/camera changes",
        "- Front hood camera is lowered and aimed upward at the hood.",
        "- Remaining front side depressions were moved down/outward.",
        "- Rear side droop was moved up/outward and feathered.",
        "- Current review remains image-only.",
    ]
    (REP/"Hoodie_Reports_And_Dome_Fix_v1D.md").write_text("\n".join(md),encoding="utf-8")
    (REP/"HoodieReportsAndDomeFix_v1D_report.txt").write_text("\n".join(md),encoding="utf-8")

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
    (AUD/"scene_layout_summary.md").write_text("# Scene Layout Summary\n\nUpdated by Hoodie Reports and Dome Fix v1D.\n\n- Project changes folder migrated into reports.\n- Front hood camera lowered for a slight upward view.\n- Camera inventory remains 12 cameras.\n",encoding="utf-8")
    (AUD/"project_file_layout.json").write_text(json.dumps({"generated_by":"hoodie_reports_and_dome_fix_v1D","reports":str(REP),"current_review":str(OUT)},indent=2),encoding="utf-8")

def main():
    reset_outputs()
    migrated=migrate_project_changes()
    log("[pass] hoodie reports and dome fix v1D")
    log(f"[reports] migrated_project_change_files={len(migrated)}")
    hoodie=find_hoodie()
    under=restore_underglow()
    disabled=keep_character_baseline()
    hoodie_fit=apply_deformation(hoodie)
    cameras=reset_cameras(hoodie)
    renders=render_review(hoodie)
    write_reports(migrated,hoodie_fit,cameras,disabled,under,renders)
    manifest()
    out=ROOT/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log("[save] "+str(out))

if __name__=="__main__":
    try:
        main()
    except Exception:
        REP.mkdir(parents=True,exist_ok=True)
        with (REP/"HoodieReportsAndDomeFix_v1D_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
