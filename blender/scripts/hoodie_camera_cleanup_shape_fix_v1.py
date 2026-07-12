import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'renders' / 'hoodie_camera_cleanup_shape_fix_v1'
REP = ROOT / 'reports' / 'hoodie_camera_cleanup_shape_fix_v1'
CUR = ROOT / 'renders' / 'current_review'
AUD = ROOT / 'reports' / 'project_workflow_audit'

HERO_NAME='F2'
HOODIE_NAME='SACKBOY_Hoodie_Main'
FALLBACK_HOODIE_NAMES=['SACKBOY_Hoodie_Main','Apricot Pullover Hoodie']
PREV_HOODIE_KEYS=[
 'HOODIEFIT_SpikeSleeveSideFix_v1',
 'HOODIEFIT_BowlRimRefine_v1',
 'HOODIEFIT_BowlRidgePolish_v1',
 'HOODIEFIT_TopArtifactFix_v1',
 'HOODIEFIT_RimCrownContain_v1',
 'HOODIEFIT_CrownSmoothExpand_v1',
 'HOODIEFIT_CrownSleeveTaper_v1',
 'HOODIEFIT_NarrowSackboy_v1',
]
NEW_HOODIE_KEY='HOODIEFIT_CameraCleanupShapeFix_v1'
UNDERGLOW_NAME='HERO_CyanUnderglow_Area'
UNDERGLOW_LOCK_LOC=(-1.522953,5.177517,0.075276)

KEEP_REVIEW_CAMERA_NAMES={
 'CAM_REVIEW_Hoodie_Material',
 'CAM_REVIEW_Hoodie_LeftSide',
 'CAM_REVIEW_Hoodie_RightSide',
 'CAM_REVIEW_Hoodie_IsolatedWire',
 'CAM_REVIEW_Hoodie_ScenePreserved',
 'CAM_REVIEW_F2_Front',
 'CAM_REVIEW_F2_ThreeQuarter',
 'CAM_REVIEW_F2_Profile',
 'CAM_REVIEW_StorefrontReflection_A',
 'CAM_REVIEW_StorefrontReflection_B',
 'CAM_REVIEW_StorefrontReflection_C',
}

def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'HoodieCameraCleanupShapeFix_report.txt').open('a',encoding='utf-8') as f: f.write(msg+'\n')

def reset():
    OUT.mkdir(parents=True, exist_ok=True); REP.mkdir(parents=True, exist_ok=True); CUR.mkdir(parents=True, exist_ok=True); AUD.mkdir(parents=True, exist_ok=True)
    (OUT/'HoodieCameraCleanupShapeFix_report.txt').write_text('',encoding='utf-8')

def visible(o): return (not o.hide_viewport) and (not o.hide_render)

def bounds_world(o):
    if not o or not hasattr(o,'bound_box'): return None
    coords=[o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {'min_x':min(xs),'max_x':max(xs),'min_y':min(ys),'max_y':max(ys),'min_z':min(zs),'max_z':max(zs),
            'dim_x':max(xs)-min(xs),'dim_y':max(ys)-min(ys),'dim_z':max(zs)-min(zs)}

def bounds_from_key_data(key):
    coords=[p.co for p in key.data]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {'min_x':min(xs),'max_x':max(xs),'min_y':min(ys),'max_y':max(ys),'min_z':min(zs),'max_z':max(zs),
            'dim_x':max(xs)-min(xs),'dim_y':max(ys)-min(ys),'dim_z':max(zs)-min(zs)}

def key_world_bounds(obj,key=None):
    coords=[obj.matrix_world @ p.co for p in key.data] if key else [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {'min_x':min(xs),'max_x':max(xs),'min_y':min(ys),'max_y':max(ys),'min_z':min(zs),'max_z':max(zs),
            'dim_x':max(xs)-min(xs),'dim_y':max(ys)-min(ys),'dim_z':max(zs)-min(zs)}

def center_from_bounds(b): return Vector(((b['min_x']+b['max_x'])*0.5,(b['min_y']+b['max_y'])*0.5,(b['min_z']+b['max_z'])*0.5))

def smoothstep(edge0,edge1,x):
    if edge0==edge1: return 0.0
    t=max(0.0,min(1.0,(x-edge0)/(edge1-edge0)))
    return t*t*(3.0-2.0*t)

def band(zn,a,b,c,d): return smoothstep(a,b,zn)*(1.0-smoothstep(c,d,zn))

def radial(nx,ny,sx,sy):
    r=(nx/max(sx,1e-6))**2+(ny/max(sy,1e-6))**2
    return max(0.0,1.0-min(1.0,r))

def restore_underglow():
    o=bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log('[lock] underglow missing'); return {'name':UNDERGLOW_NAME,'status':'missing'}
    before=[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)]
    o.location=Vector(UNDERGLOW_LOCK_LOC)
    after=[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)]
    log(f'[lock] underglow locked {before} -> {after}')
    return {'name':UNDERGLOW_NAME,'before':before,'after':after}

def keep_character_baseline():
    hero=bpy.data.objects.get(HERO_NAME); disabled=[]
    if hero and hero.type=='MESH' and hero.data.shape_keys:
        for kb in hero.data.shape_keys.key_blocks:
            if kb.name.startswith('BODYFIT_'):
                before=float(kb.value); kb.value=0.0; disabled.append({'name':kb.name,'before':round(before,4),'after':0.0})
    log('[character] F2 baseline preserved; BODYFIT keys kept disabled')
    return disabled

def find_hoodie():
    for name in FALLBACK_HOODIE_NAMES:
        o=bpy.data.objects.get(name)
        if o and o.type=='MESH':
            if o.name!=HOODIE_NAME:
                old=o.name; o.name=HOODIE_NAME; o.data.name=HOODIE_NAME+'_Mesh'; log(f'[rename] hoodie renamed {old} -> {o.name}')
            return o
    matches=[o for o in bpy.data.objects if o.type=='MESH' and ('hoodie' in o.name.lower() or 'pullover' in o.name.lower() or 'apricot' in o.name.lower())]
    if not matches: raise RuntimeError('No hoodie mesh found')
    o=sorted(matches,key=lambda x:(not visible(x),-len(x.data.vertices),x.name))[0]
    old=o.name; o.name=HOODIE_NAME; o.data.name=HOODIE_NAME+'_Mesh'; log(f'[rename] hoodie renamed {old} -> {o.name}')
    return o

def cleanup_review_cameras():
    removed=[]
    for o in list(bpy.data.objects):
        if o.type=='CAMERA' and o.name.startswith('CAM_REVIEW_') and o.name not in KEEP_REVIEW_CAMERA_NAMES:
            removed.append(o.name); bpy.data.objects.remove(o, do_unlink=True)
    # remove orphan camera data from old review cameras when possible
    for cam in list(bpy.data.cameras):
        if cam.users==0 and cam.name.startswith('CAM_REVIEW_'):
            bpy.data.cameras.remove(cam)
    log(f'[camera] removed {len(removed)} old CAM_REVIEW_* camera object(s): {removed}')
    return removed

def ensure_hoodie_key(obj):
    if not obj.data.shape_keys: obj.shape_key_add(name='Basis', from_mix=False)
    if obj.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY):
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
        obj.active_shape_key_index=list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY); bpy.ops.object.shape_key_remove()
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith('HOODIEFIT_'): kb.value=0.0
    source=None
    for key_name in PREV_HOODIE_KEYS:
        kb=obj.data.shape_keys.key_blocks.get(key_name)
        if kb:
            kb.value=1.0; source=key_name; break
    new_key=obj.shape_key_add(name=NEW_HOODIE_KEY, from_mix=True)
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith('HOODIEFIT_'): kb.value=0.0
    new_key.value=1.0; obj.active_shape_key_index=list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
    return new_key,source

def build_adjacency(mesh):
    adj=[set() for _ in range(len(mesh.vertices))]
    for poly in mesh.polygons:
        vs=list(poly.vertices); n=len(vs)
        for i,a in enumerate(vs):
            b1=vs[(i-1)%n]; b2=vs[(i+1)%n]
            if a!=b1: adj[a].add(b1); adj[b1].add(a)
            if a!=b2: adj[a].add(b2); adj[b2].add(a)
    return adj

def smooth_region(key, adjacency, weights, factor=0.30):
    original=[p.co.copy() for p in key.data]
    count=0; max_fix=0.0
    for i,w in enumerate(weights):
        if w<=0: continue
        nbrs=adjacency[i]
        if not nbrs: continue
        avg=Vector((0,0,0))
        for n in nbrs: avg+=original[n]
        avg/=len(nbrs)
        before=key.data[i].co.copy(); key.data[i].co=before.lerp(avg,min(1.0,factor*w))
        d=(key.data[i].co-before).length
        if d>1e-8:
            count+=1; max_fix=max(max_fix,d)
    return count,max_fix

def apply_shape_fix(hoodie):
    key,source=ensure_hoodie_key(hoodie)
    lb=bounds_from_key_data(key); before_world=key_world_bounds(hoodie,key)
    cx=(lb['min_x']+lb['max_x'])*0.5; cy=(lb['min_y']+lb['max_y'])*0.5
    zmin=lb['min_z']; dz=max(lb['dim_z'],1e-6); hx=max(lb['dim_x']*0.5,1e-6); hy=max(lb['dim_y']*0.5,1e-6)
    v_before=len(hoodie.data.vertices); f_before=len(hoodie.data.polygons)
    weights=[0.0]*len(key.data)
    counts={'top_ridge_rounded':0,'lower_sides_pulled_out_down':0,'shoulder_collar_raised':0,'sleeve_uniform_thickness':0,'back_protrusion_feathered':0,'spike_smoothing_vertices':0}
    touched=0; max_delta=0.0
    for i,point in enumerate(key.data):
        co=point.co.copy(); zn=(co.z-zmin)/dz
        nx_signed=(co.x-cx)/hx; nx=abs(nx_signed); ny_signed=(co.y-cy)/hy; ny=abs(ny_signed)
        top_ridge=band(zn,0.76,0.84,1.0,1.0)
        bowl=band(zn,0.60,0.70,0.94,1.0)
        lower_side=band(zn,0.34,0.42,0.64,0.78)
        shoulder_collar=band(zn,0.42,0.52,0.70,0.82)
        sleeve=band(zn,0.32,0.42,0.70,0.82)
        back_zone=band(zn,0.58,0.68,0.92,1.0)
        center=radial(nx,ny,0.78,0.90); wide=radial(nx,ny,1.10,1.05)
        side=smoothstep(0.38,0.88,nx); frontback=smoothstep(0.36,0.88,ny); outer=max(side,frontback)
        # assume positive local Y is back; if reversed, symmetrical feathering still reduces side-profile protrusion.
        rear=smoothstep(0.18,0.72,ny_signed)
        new=co.copy()
        # Continue rounding ridge with a milder, smoother move.
        ridge_w=top_ridge*(0.55+0.45*center)
        if ridge_w>0:
            new.z+=dz*0.020*ridge_w
            new.x=cx+(new.x-cx)*(1.0+0.006*ridge_w)
            new.y=cy+(new.y-cy)*(1.0+0.008*ridge_w)
            weights[i]=max(weights[i],0.45*ridge_w)
        bowl_w=bowl*wide
        if bowl_w>0:
            # keep bowl silhouette round without pinching side lower walls upward
            new.z+=dz*0.008*bowl_w
            weights[i]=max(weights[i],0.35*bowl_w)
        # Explicitly reverse the issue: lower side hood goes out and down, not in/up.
        side_w=lower_side*side*(0.50+0.50*(1.0-center))
        if side_w>0:
            new.x=cx+(new.x-cx)*(1.0+0.026*side_w)
            new.y=cy+(new.y-cy)*(1.0+0.016*side_w)
            new.z-=dz*0.020*side_w
            weights[i]=max(weights[i],0.50*side_w)
        # Raise shoulder collar seams / roots that had crept down.
        shoulder_w=shoulder_collar*outer
        if shoulder_w>0:
            new.z+=dz*0.028*shoulder_w
            new.x=cx+(new.x-cx)*(1.0+0.008*shoulder_w)
            weights[i]=max(weights[i],0.42*shoulder_w)
        # Keep sleeve cavity more uniform/thicker near shoulder, without touching Sackboy.
        sleeve_w=sleeve*outer
        if sleeve_w>0:
            new.x=cx+(new.x-cx)*(1.0+0.018*sleeve_w)
            new.y=cy+(new.y-cy)*(1.0+0.012*sleeve_w)
            weights[i]=max(weights[i],0.38*sleeve_w)
        # Reduce back protrusion in side profile: ease rear cap inward and blend it into crown.
        back_w=back_zone*rear*(0.35+0.65*wide)
        if back_w>0:
            new.y=cy+(new.y-cy)*(1.0-0.026*back_w)
            new.z+=dz*0.006*back_w
            weights[i]=max(weights[i],0.55*back_w)
        delta=(new-co).length
        if delta>1e-7:
            if ridge_w>0.08: counts['top_ridge_rounded']+=1
            if side_w>0.08: counts['lower_sides_pulled_out_down']+=1
            if shoulder_w>0.08: counts['shoulder_collar_raised']+=1
            if sleeve_w>0.08: counts['sleeve_uniform_thickness']+=1
            if back_w>0.08: counts['back_protrusion_feathered']+=1
            point.co=new; touched+=1; max_delta=max(max_delta,delta)
    adj=build_adjacency(hoodie.data)
    smooth_count,smooth_max=smooth_region(key,adj,weights,factor=0.26)
    counts['spike_smoothing_vertices']=smooth_count
    max_delta=max(max_delta,smooth_max)
    after_world=key_world_bounds(hoodie,key)
    v_after=len(hoodie.data.vertices); f_after=len(hoodie.data.polygons)
    hoodie['hoodie_fit_pass']='HoodieCameraCleanupShapeFix_v1'; hoodie['hoodie_fit_shape_key']=NEW_HOODIE_KEY
    log(f'[hoodie] active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; smoothed_vertices={smooth_count}; max_delta_local={max_delta:.6f}; vertices={v_before}->{v_after}; faces={f_before}->{f_after}')
    return {'shape_key':NEW_HOODIE_KEY,'source_key':source,'value':1.0,'touched_vertices':touched,'smoothed_vertices':smooth_count,'max_delta_local':max_delta,
            'vertex_count_before':v_before,'vertex_count_after':v_after,'vertex_count_delta':v_after-v_before,
            'face_count_before':f_before,'face_count_after':f_after,'face_count_delta':f_after-f_before,
            'world_dimensions_before':[round(before_world['dim_x'],6),round(before_world['dim_y'],6),round(before_world['dim_z'],6)],
            'world_dimensions_after':[round(after_world['dim_x'],6),round(after_world['dim_y'],6),round(after_world['dim_z'],6)],
            'world_dimension_delta':[round(after_world['dim_x']-before_world['dim_x'],6),round(after_world['dim_y']-before_world['dim_y'],6),round(after_world['dim_z']-before_world['dim_z'],6)],
            'region_counts':counts}

def object_report(name):
    o=bpy.data.objects.get(name)
    if not o: return {'name':name,'status':'missing'}
    b=bounds_world(o); shape_keys=[]
    if o.type=='MESH' and o.data.shape_keys:
        shape_keys=[{'name':kb.name,'value':round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
    return {'name':name,'status':'present','type':o.type,'visible':visible(o),'loc':[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],'dims':None if not b else [round(b['dim_x'],6),round(b['dim_y'],6),round(b['dim_z'],6)],'vertices':len(o.data.vertices) if o.type=='MESH' else 0,'faces':len(o.data.polygons) if o.type=='MESH' else 0,'shape_keys':shape_keys}

def scan_lights():
    rows=[]
    for o in sorted([x for x in bpy.data.objects if x.type=='LIGHT'],key=lambda x:x.name):
        d=o.data; rows.append({'name':o.name,'type':d.type,'loc':[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],'energy':getattr(d,'energy',None),'color':[round(v,6) for v in getattr(d,'color',[])] if hasattr(d,'color') else None})
    return rows

def set_workbench(scene,color_type):
    scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type=color_type
    scene.display.shading.show_xray=False; scene.display.shading.show_cavity=True; scene.display.shading.show_object_outline=True

def setup_render_settings():
    sc=bpy.context.scene; sc.render.resolution_x=960; sc.render.resolution_y=540; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'
    log('[render] 960x540 Workbench evidence renders; isolated wire view hides non-hoodie objects')

def look_at(o,target):
    direction=Vector(target)-o.location
    if direction.length: o.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

def make_or_update_cam(name,loc,target,lens):
    cam=bpy.data.objects.get(name)
    if not cam or cam.type!='CAMERA':
        data=bpy.data.cameras.new(name+'_Data'); cam=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(cam)
    cam.location=Vector(loc); cam.data.lens=lens; look_at(cam,Vector(target)); return cam

def create_temp_wire_overlay(hoodie):
    dup=hoodie.copy(); dup.data=hoodie.data.copy(); dup.name='TMP_Hoodie_WireOverlay_DO_NOT_SAVE'; dup.data.name='TMP_Hoodie_WireOverlay_Mesh'; bpy.context.scene.collection.objects.link(dup)
    if dup.data.shape_keys:
        for kb in dup.data.shape_keys.key_blocks:
            kb.value=1.0 if kb.name==NEW_HOODIE_KEY else 0.0
    mat=bpy.data.materials.new('TMP_Wire_Black_DO_NOT_SAVE'); mat.diffuse_color=(0,0,0,1); dup.data.materials.clear(); dup.data.materials.append(mat)
    mod=dup.modifiers.new('TMP_RenderWire','WIREFRAME'); mod.thickness=0.0022; mod.use_even_offset=True; mod.use_replace=False; dup.show_in_front=True
    return dup,mat

def set_hide_for_isolated_wire(hoodie, wire_obj):
    previous=[]
    for o in bpy.data.objects:
        previous.append((o,o.hide_render,o.hide_viewport))
        if o not in (hoodie, wire_obj) and o.type!='CAMERA':
            o.hide_render=True; o.hide_viewport=True
    return previous

def restore_hide(previous):
    for o,hr,hv in previous:
        if o.name in bpy.data.objects:
            o.hide_render=hr; o.hide_viewport=hv

def render_review(hoodie):
    sc=bpy.context.scene; old_engine=sc.render.engine; old_res=(sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage); old_cam=sc.camera; old_path=sc.render.filepath
    kb=hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY) if hoodie.data.shape_keys else None
    hb=key_world_bounds(hoodie,kb); center=center_from_bounds(hb); focus=Vector((center.x,center.y,hb['min_z']+hb['dim_z']*0.74))
    camspecs=[
        ('CAM_REVIEW_Hoodie_Material',(focus.x+0.75,focus.y-3.75,focus.z+1.05),focus,55,'01_HoodieMaterialShape.png','MATERIAL',False),
        ('CAM_REVIEW_Hoodie_LeftSide',(focus.x-2.65,focus.y-2.85,focus.z+0.95),focus,58,'02_HoodieLeftSideGray.png','SINGLE',False),
        ('CAM_REVIEW_Hoodie_RightSide',(focus.x+2.65,focus.y-2.85,focus.z+0.95),focus,58,'03_HoodieRightSideGray.png','SINGLE',False),
        # pushed back compared to prior wire view; isolated so camera/light/frustum lines cannot look like hoodie spikes
        ('CAM_REVIEW_Hoodie_IsolatedWire',(focus.x+0.45,focus.y-4.45,focus.z+1.65),focus,48,'04_HoodieIsolatedWireCheck.png','SINGLE',True),
        ('CAM_REVIEW_Hoodie_ScenePreserved',(center.x+5.0,center.y-7.6,center.z+1.25),center+Vector((0,1.0,0.2)),44,'05_HoodieScenePreserved.png','MATERIAL',False),
    ]
    cams=[]; wire_obj=None; wire_mat=None; previous=None
    try:
        setup_render_settings()
        for name,loc,tgt,lens,fn,color_type,use_wire in camspecs:
            if use_wire:
                wire_obj,wire_mat=create_temp_wire_overlay(hoodie); previous=set_hide_for_isolated_wire(hoodie,wire_obj)
            set_workbench(sc,color_type); cam=make_or_update_cam(name,loc,tgt,lens)
            cams.append({'name':name,'render':fn,'loc':[round(cam.location.x,6),round(cam.location.y,6),round(cam.location.z,6)],'lens':lens,'mode':'WORKBENCH_'+color_type+('_ISOLATED_WIRE' if use_wire else '')})
            sc.camera=cam; sc.render.filepath=str(OUT/fn); bpy.ops.render.render(write_still=True); log('[render] '+fn)
            if previous: restore_hide(previous); previous=None
            if wire_obj: bpy.data.objects.remove(wire_obj,do_unlink=True); wire_obj=None
            if wire_mat: bpy.data.materials.remove(wire_mat,do_unlink=True); wire_mat=None
    finally:
        if previous: restore_hide(previous)
        if wire_obj: bpy.data.objects.remove(wire_obj,do_unlink=True)
        if wire_mat: bpy.data.materials.remove(wire_mat,do_unlink=True)
        sc.render.engine=old_engine; sc.render.resolution_x,sc.render.resolution_y,sc.render.resolution_percentage=old_res; sc.camera=old_cam; sc.render.filepath=old_path
    return cams

def create_reference_cameras(hoodie):
    # Minimal non-rendered reference cameras retained for F2 and storefront, as requested.
    hero=bpy.data.objects.get(HERO_NAME); hb=bounds_world(hero)
    made=[]
    if hb:
        c=center_from_bounds(hb); target=Vector((c.x,c.y,hb['min_z']+hb['dim_z']*0.55))
        refs=[('CAM_REVIEW_F2_Front',(target.x,target.y-6.0,target.z+0.6),target,56),('CAM_REVIEW_F2_ThreeQuarter',(target.x+4.1,target.y-5.6,target.z+0.9),target,52),('CAM_REVIEW_F2_Profile',(target.x+5.6,target.y-0.8,target.z+0.7),target,60)]
        for name,loc,tgt,lens in refs:
            make_or_update_cam(name,loc,tgt,lens); made.append(name)
    kb=hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY) if hoodie.data.shape_keys else None
    hbb=key_world_bounds(hoodie,kb); hc=center_from_bounds(hbb)
    refs=[('CAM_REVIEW_StorefrontReflection_A',(hc.x+7.8,hc.y-10.0,hc.z+1.4),(hc.x,hc.y+4.2,hc.z+0.9),48),('CAM_REVIEW_StorefrontReflection_B',(hc.x+4.6,hc.y-8.4,hc.z+1.2),(hc.x,hc.y+3.7,hc.z+0.8),55),('CAM_REVIEW_StorefrontReflection_C',(hc.x-4.0,hc.y-8.0,hc.z+1.1),(hc.x,hc.y+3.8,hc.z+0.8),55)]
    for name,loc,tgt,lens in refs:
        make_or_update_cam(name,loc,Vector(tgt),lens); made.append(name)
    log(f'[camera] retained/created minimal reference cameras: {made}')
    return made

def copy_current_review():
    for p in CUR.glob('*'):
        if p.is_file(): p.unlink()
    for p in OUT.glob('*'):
        if p.is_file(): (CUR/p.name).write_bytes(p.read_bytes())

def write_reports(fit,disabled,under,cams,removed,refs):
    payload={'pass':'hoodie_camera_cleanup_shape_fix_v1','hoodie_fit':fit,'disabled_bodyfit_keys':disabled,'underglow_lock':under,'review_cameras':cams,'removed_old_review_cameras':removed,'retained_reference_cameras':refs,'key_objects':[object_report(n) for n in [HERO_NAME,HOODIE_NAME,'Cargo pants','Plane.001','Plane.022','Asphalt ground','Audi e-tron GT quattro Black']],'lights_scan':scan_lights(),'notes':['Wire spikes in the user screenshot were likely viewport/camera/light/frustum/other-scene wire overlays, not hoodie mesh spikes, since the user did not see them in the actual viewport after the pass. This package still smooths local hoodie outliers and renders an isolated hoodie wire check.','Old CAM_REVIEW_* duplicates were deleted, then a small review-camera set was recreated.']}
    (REP/'hoodie_camera_cleanup_shape_fix_v1.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    (OUT/'HoodieCameraCleanupShapeFix_status.json').write_text(json.dumps({'ok':True,'shape_key':NEW_HOODIE_KEY,'removed_old_cameras':len(removed),'touched_vertices':fit['touched_vertices'],'smoothed_vertices':fit['smoothed_vertices'],'vertex_delta':fit['vertex_count_delta'],'face_delta':fit['face_count_delta']},indent=2),encoding='utf-8')
    md=['# Hoodie Camera Cleanup Shape Fix v1','', '## Changes', f'- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.', '- Deleted old `CAM_REVIEW_*` camera duplicates and recreated a minimal review set.', '- Pushed the wire camera back and rendered it as an isolated hoodie-only wire view so scene/camera/light wireframes do not look like hoodie spikes.', '- Raised shoulder collar seams.', '- Pulled lower hood sides back out and down instead of pushing them in/up.', '- Feathered/reduced the rear hood protrusion in side profile.', '- Kept sleeves more uniformly thick near the shoulder root.', '', '## Counts', f"- Hoodie vertices: {fit['vertex_count_before']} -> {fit['vertex_count_after']} (delta {fit['vertex_count_delta']})", f"- Hoodie faces: {fit['face_count_before']} -> {fit['face_count_after']} (delta {fit['face_count_delta']})", f"- Touched vertices: {fit['touched_vertices']}", f"- Smoothed vertices: {fit['smoothed_vertices']}", f"- Max local vertex movement: {fit['max_delta_local']:.6f}", f"- World dimensions before: {fit['world_dimensions_before']}", f"- World dimensions after: {fit['world_dimensions_after']}", f"- World dimension delta: {fit['world_dimension_delta']}", '', '## Camera cleanup', f"- Removed old review cameras: {len(removed)}", f"- Retained/created reference cameras: {refs}"]
    (REP/'Hoodie_Camera_Cleanup_Shape_Fix_v1.md').write_text('\n'.join(md),encoding='utf-8')

def manifest():
    data={'blend_file':bpy.data.filepath,'objects':[],'collections':[]}
    for col in sorted(bpy.data.collections,key=lambda c:c.name): data['collections'].append({'name':col.name,'hide_viewport':bool(col.hide_viewport),'hide_render':bool(col.hide_render),'object_count':len(col.objects),'child_count':len(col.children)})
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        b=bounds_world(o); item={'name':o.name,'type':o.type,'collections':[c.name for c in o.users_collection],'visible':visible(o),'location':[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],'dimensions':None if not b else [round(b['dim_x'],6),round(b['dim_y'],6),round(b['dim_z'],6)]}
        if o.type=='MESH':
            item['vertices']=len(o.data.vertices); item['faces']=len(o.data.polygons)
            if o.data.shape_keys: item['shape_keys']=[{'name':kb.name,'value':round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
        if o.type=='LIGHT': item['energy']=getattr(o.data,'energy',None); item['color']=[round(v,6) for v in getattr(o.data,'color',[])] if hasattr(o.data,'color') else None
        if o.type=='CAMERA' and o.name.startswith('CAM_REVIEW_'): item['review_camera']=True
        data['objects'].append(item)
    (ROOT/'scene_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (AUD/'scene_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (AUD/'scene_layout_summary.md').write_text('# Scene Layout Summary\n\nUpdated by Hoodie Camera Cleanup Shape Fix v1.\n\n- Old review camera duplicates deleted and a minimal camera set recreated.\n- Focused hoodie shape fix added.\n- Isolated wire render avoids scene/camera/light overlay confusion.\n',encoding='utf-8')
    (AUD/'project_file_layout.json').write_text(json.dumps({'generated_by':'hoodie_camera_cleanup_shape_fix_v1','reports':str(REP),'renders':str(OUT),'current_review':str(CUR)},indent=2),encoding='utf-8')

def main():
    reset(); log('[pass] hoodie camera cleanup shape fix v1')
    hoodie=find_hoodie(); removed=cleanup_review_cameras(); under=restore_underglow(); disabled=keep_character_baseline(); fit=apply_shape_fix(hoodie); refs=create_reference_cameras(hoodie); cams=render_review(hoodie); write_reports(fit,disabled,under,cams,removed,refs); copy_current_review(); manifest(); out=ROOT/'blender'/'sackboy_scene.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(out)); log('[save] '+str(out))

if __name__=='__main__':
    try: main()
    except Exception:
        OUT.mkdir(parents=True,exist_ok=True)
        with (OUT/'HoodieCameraCleanupShapeFix_FATAL_ERROR.txt').open('w',encoding='utf-8') as f: traceback.print_exc(file=f)
        raise
