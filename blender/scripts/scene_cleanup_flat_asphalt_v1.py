import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'renders'/'scene_cleanup_flat_asphalt_v1'
REP=ROOT/'reports'/'scene_cleanup_flat_asphalt_v1'
CUR=ROOT/'renders'/'current_review'
AUD=ROOT/'reports'/'project_workflow_audit'
def log(s):
    print(s); OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'SceneCleanupFlatAsphalt_report.txt').open('a',encoding='utf-8') as f:f.write(s+'\n')
def reset():
    OUT.mkdir(parents=True,exist_ok=True); REP.mkdir(parents=True,exist_ok=True); AUD.mkdir(parents=True,exist_ok=True)
    (OUT/'SceneCleanupFlatAsphalt_report.txt').write_text('',encoding='utf-8')
def vis(o): return (not o.hide_viewport) and (not o.hide_render)
def bnd(o):
    if not o or not hasattr(o,'bound_box'): return None
    cs=[o.matrix_world@Vector(c) for c in o.bound_box]; xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    return dict(min_x=min(xs),max_x=max(xs),min_y=min(ys),max_y=max(ys),min_z=min(zs),max_z=max(zs),dim_x=max(xs)-min(xs),dim_y=max(ys)-min(ys),dim_z=max(zs)-min(zs))
def ctr(b): return Vector(((b['min_x']+b['max_x'])/2,(b['min_y']+b['max_y'])/2,(b['min_z']+b['max_z'])/2))
def counts(o): return {'vertices':len(o.data.vertices),'faces':len(o.data.polygons)} if o and o.type=='MESH' else {'vertices':0,'faces':0}
def col(name,hide=False):
    c=bpy.data.collections.get(name)
    if not c:
        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    c.hide_viewport=hide; c.hide_render=hide; return c
def link(o,c):
    try:
        if o.name not in c.objects: c.objects.link(o)
    except Exception: pass
def backup(o,label):
    c=col('SCENE_CLEANUP_BACKUPS_HIDDEN',True); safe=o.name.replace(' ','_').replace('(','').replace(')','').replace('.','_')
    n=f'SCENE_BACKUP_{label}_{safe}'
    if bpy.data.objects.get(n): return bpy.data.objects[n]
    me=o.data.copy(); me.name=n+'_Mesh'; bo=bpy.data.objects.new(n,me); bo.matrix_world=o.matrix_world.copy(); bo.hide_viewport=True; bo.hide_render=True
    bo['backup_for']=o.name; bo['backup_reason']=label; link(bo,c); return bo
def transfer(src,dst):
    if not src or not dst or src.type!='MESH' or dst.type!='MESH' or len(src.material_slots)<1: return False
    while len(dst.material_slots)>0: dst.data.materials.pop(index=0)
    for s in src.material_slots:
        if s.material: dst.data.materials.append(s.material)
    return True
def flatten(o,z):
    inv=o.matrix_world.inverted()
    for v in o.data.vertices:
        w=o.matrix_world@v.co; w.z=z; v.co=inv@w
    o.data.update()
def paint_objs():
    out=[]; seen=set()
    for o in bpy.data.objects:
        if o.type!='MESH': continue
        t=(o.name+' '+' '.join(c.name for c in o.users_collection)).lower()
        if any(x in t for x in ['asphalt','ground','lamp','sign','sidewalk','curb','storefront','camera']): continue
        if any(x in t for x in ['hparking','stripe','strip','paint','line','divider','spine','parking']):
            if o.name not in seen: seen.add(o.name); out.append(o)
    return out
def prep_asphalt():
    env=bpy.data.objects.get('ENV_Asphalt'); imp=bpy.data.objects.get('Asphalt ground')
    seen=sorted({o.name for o in bpy.data.objects if o.type=='MESH' and any(k in (o.name+' '+' '.join(c.name for c in o.users_collection)).lower() for k in ['asphalt','parkinglot','parking lot'])})
    if not env:
        mesh=bpy.data.meshes.new('ENV_Asphalt_Mesh'); s=36; mesh.from_pydata([(-s/2,-s/2,0),(s/2,-s/2,0),(s/2,s/2,0),(-s/2,s/2,0)],[],[(0,1,2,3)]); mesh.update(); env=bpy.data.objects.new('ENV_Asphalt',mesh); bpy.context.scene.collection.objects.link(env); log('[asphalt] created ENV_Asphalt')
    backup(env,'before_flatten')
    changes={'asphalt_objects_seen':seen}
    if imp and imp.type=='MESH':
        backup(imp,'hidden_imported_asphalt'); changes['material_transferred_from_imported_asphalt']=transfer(imp,env); imp.hide_viewport=True; imp.hide_render=True; changes['imported_asphalt_hidden']=imp.name; log('[asphalt] hid bumpy imported Asphalt ground')
    eb=bnd(env); z=eb['max_z'] if eb else 0.0; flatten(env,z); env['scene_cleanup_flattened']=True; env['scene_cleanup_flatten_plane_z']=z
    if not env.modifiers.get('FLAT_ASPHALT_VISUAL_THICKNESS'):
        try:
            m=env.modifiers.new('FLAT_ASPHALT_VISUAL_THICKNESS','SOLIDIFY'); m.thickness=.04; m.offset=-1; m.show_viewport=True; m.show_render=True
        except Exception: pass
    rows=[]; off=.004
    for o in paint_objs():
        for m in list(o.modifiers):
            if m.name=='PARKING_TO_ASPHALT_PREVIEW': o.modifiers.remove(m)
        ob=bnd(o)
        if not ob: continue
        old=o.location.z; o.location.z += (z+off)-ob['min_z']; nb=bnd(o); o['scene_cleanup_paint_snapped_to']=env.name; o['scene_cleanup_paint_offset']=off
        rows.append({'name':o.name,'old_location_z':round(old,6),'new_location_z':round(o.location.z,6),'new_min_z':None if not nb else round(nb['min_z'],6)})
    changes.update(flat_asphalt_target=env.name,flat_plane_z=z,paint_objects_adjusted=len(rows),paint_objects=rows)
    log(f'[paint] flattened {env.name} at z={z:.6f}; adjusted {len(rows)} paint objects')
    return changes
def cleanup_cams():
    removed=[]
    for cname in ['HERO_REVIEW_CAMERAS_MESH_AUDIT','HERO_REVIEW_CAMERAS']:
        c=bpy.data.collections.get(cname)
        if not c: continue
        for o in list(c.objects):
            if o.type=='CAMERA' and (o.name.startswith('HERO_CAM_') or 'Audit' in o.name or 'Review' in o.name): removed.append(o.name); bpy.data.objects.remove(o,do_unlink=True)
        if len(c.objects)==0 and len(c.children)==0:
            try:bpy.data.collections.remove(c)
            except Exception:pass
    log(f'[cleanup] removed {len(removed)} temp review cameras'); return removed
def scan_lights():
    rows=[]
    for o in sorted([x for x in bpy.data.objects if x.type=='LIGHT'],key=lambda x:x.name):
        d=o.data; rows.append({'name':o.name,'light_type':d.type,'location':[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],'rotation':[round(v,6) for v in o.rotation_euler],'energy':getattr(d,'energy',None),'color':[round(v,6) for v in getattr(d,'color',[])],'size':getattr(d,'size',None),'spot_size':getattr(d,'spot_size',None) if d.type=='SPOT' else None,'spot_blend':getattr(d,'spot_blend',None) if d.type=='SPOT' else None})
    return rows
def scan_decimate():
    rows=[]
    for n in ['Apricot Pullover Hoodie','Utility Box (Photoscanned)','Lid.001']:
        o=bpy.data.objects.get(n)
        if not o: rows.append({'name':n,'status':'missing'}); continue
        c=counts(o); m=o.modifiers.get('OPT_PREVIEW_DECIMATE'); rows.append({'name':n,'vertices':c['vertices'],'faces':c['faces'],'decimate_modifier_present':bool(m),'ratio':None if not m else m.ratio,'show_viewport':None if not m else m.show_viewport,'show_render':None if not m else m.show_render})
    return rows
def reports(asph,rm,lights,dec):
    payload={'asphalt_and_paint':asph,'removed_temp_review_cameras':rm,'lights_scanned_preserved':lights,'decimate_targets_verified':dec,'reflection_plan_note':'Colored off-scene spotlights for window reflections should be a later dedicated package; none added here.','locked':{'lights':'scanned only, not modified','car':'not modified','storefront':'not modified','sky_world_hdri':'not modified','character_hands':'not modified'}}
    (REP/'scene_cleanup_flat_asphalt_v1.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    lines=['# Scene Cleanup / Flat Asphalt v1','', 'This pass scans the newly tuned lighting, cleans temporary review cameras, flattens the parking asphalt, and places paint strips directly on the flat surface.','', '## Asphalt / Paint',f"- Flat asphalt target: **{asph.get('flat_asphalt_target')}**",f"- Flat plane z: **{asph.get('flat_plane_z')}**",f"- Paint objects adjusted: **{asph.get('paint_objects_adjusted')}**"]
    if asph.get('imported_asphalt_hidden'): lines.append(f"- Hidden bumpy imported asphalt: **{asph.get('imported_asphalt_hidden')}**")
    lines += ['','## Decimate Preview Verification']+[f"- **{r.get('name')}** | modifier={r.get('decimate_modifier_present')} | ratio={r.get('ratio')} | faces={r.get('faces')}" for r in dec]
    lines += ['','## Current Light Scan']+[f"- **{l['name']}** | type={l['light_type']} | loc={l['location']} | energy={l['energy']} | color={l['color']} | spot_size={l.get('spot_size')} | spot_blend={l.get('spot_blend')}" for l in lights]
    lines += ['','## Reflection Lighting Plan','- Colored off-scene spotlights for glossy storefront reflections are a good idea, but should be added in a separate controlled package because they intentionally add lights.','- No new reflection lights were added here.']
    (REP/'Scene_Cleanup_Flat_Asphalt_v1.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'SceneCleanupFlatAsphalt_status.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
def manifest():
    data={'blend_file':bpy.data.filepath,'objects':[],'collections':[]}
    for c in sorted(bpy.data.collections,key=lambda x:x.name): data['collections'].append({'name':c.name,'hide_viewport':bool(c.hide_viewport),'hide_render':bool(c.hide_render),'object_count':len(c.objects),'child_count':len(c.children)})
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        bb=bnd(o); e={'name':o.name,'type':o.type,'collections':[c.name for c in o.users_collection],'visible':vis(o),'location':[round(o.location.x,6),round(o.location.y,6),round(o.location.z,6)],'rotation':[round(v,6) for v in o.rotation_euler],'scale':[round(o.scale.x,6),round(o.scale.y,6),round(o.scale.z,6)],'dimensions':None if not bb else [round(bb['dim_x'],6),round(bb['dim_y'],6),round(bb['dim_z'],6)],'modifiers':[{'name':m.name,'type':m.type} for m in o.modifiers]}
        if o.type=='MESH': e.update(counts(o))
        if o.type=='LIGHT': e.update({'energy':getattr(o.data,'energy',None),'color':[round(v,6) for v in getattr(o.data,'color',[])]})
        data['objects'].append(e)
    (ROOT/'scene_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8'); (AUD/'scene_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (AUD/'scene_layout_summary.md').write_text('# Scene Layout Summary\n\nUpdated by Scene Cleanup / Flat Asphalt v1.\n\n- Current lights scanned and preserved.\n- Parking asphalt flattened and paint snapped.\n- Temporary review cameras cleaned.\n',encoding='utf-8')
    (AUD/'project_file_layout.json').write_text(json.dumps({'generated_by':'scene_cleanup_flat_asphalt_v1','reports':str(REP),'renders':str(OUT),'current_review':str(CUR)},indent=2),encoding='utf-8')
def look(cam,target): cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
def tempcam(n,loc,aim,lens):
    d=bpy.data.cameras.new(n+'_Data'); c=bpy.data.objects.new(n,d); c.location=loc; c.data.lens=lens; look(c,aim); bpy.context.scene.collection.objects.link(c); return c
def render():
    sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=1280; sc.render.resolution_y=720; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.render.film_transparent=False
    env=bpy.data.objects.get('ENV_Asphalt'); eb=bnd(env) or {'min_x':-18,'max_x':18,'min_y':-18,'max_y':18,'min_z':0,'max_z':0,'dim_x':36,'dim_y':36,'dim_z':.1}; cc=ctr(eb); hero=bpy.data.objects.get('F2'); hb=bnd(hero) or eb; hc=ctr(hb)
    cams=[tempcam('TMP_Render_FlatPaintCheck',Vector((cc.x+eb['dim_x']*.18,cc.y-eb['dim_y']*.32,eb['max_z']+9)),Vector((cc.x,cc.y,eb['max_z']+.02)),42),tempcam('TMP_Render_DecimatePreviewCheck',Vector((hc.x+2.5,hc.y-6,hc.z+1.5)),Vector((hc.x,hc.y,hc.z+.4)),55)]
    orig=sc.camera; outs=[(cams[0],'01_FlatAsphaltPaintCheck.png'),(cams[1],'02_DecimatePreviewCheck.png')]
    ex=bpy.data.objects.get('Camera') or orig
    if ex and ex.type=='CAMERA': outs.append((ex,'03_CurrentSceneCamera.png'))
    for c,fn in outs:
        sc.camera=c; sc.render.filepath=str(OUT/fn); bpy.ops.render.render(write_still=True); log('[render] '+fn)
    sc.camera=orig
    for c in cams: bpy.data.objects.remove(c,do_unlink=True)
    CUR.mkdir(parents=True,exist_ok=True)
    for p in CUR.glob('*'):
        if p.is_file(): p.unlink()
    for p in OUT.glob('*'):
        if p.is_file(): (CUR/p.name).write_bytes(p.read_bytes())
def main():
    reset(); log('[lock] scanning current light changes; not modifying lights'); rm=cleanup_cams(); asph=prep_asphalt(); lights=scan_lights(); dec=scan_decimate(); reports(asph,rm,lights,dec); manifest(); render(); out=ROOT/'blender'/'sackboy_scene.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(out)); log('[save] '+str(out))
if __name__=='__main__':
    try: main()
    except Exception:
        OUT.mkdir(parents=True,exist_ok=True)
        with (OUT/'SceneCleanupFlatAsphalt_FATAL_ERROR.txt').open('w',encoding='utf-8') as f: traceback.print_exc(file=f)
        raise
