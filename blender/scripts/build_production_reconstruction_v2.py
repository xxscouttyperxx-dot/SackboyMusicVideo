import sys, math, json, traceback
from pathlib import Path
import bpy
from mathutils import Vector
scripts_dir=Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path: sys.path.insert(0,str(scripts_dir))
from common import project_root
from export_scene_manifest import export_scene_manifest
ROOT="PROD_RECON_V2"; OUT_DIR=project_root()/"renders"/"production_reconstruction_v2"
FULL_CHARACTER_SOURCE="F2"; HAND_REFERENCE_SOURCE="HANDREFINE_J2B_Working"
def log(msg):
    print(msg); OUT_DIR.mkdir(parents=True,exist_ok=True)
    with (OUT_DIR/"ProductionReconstructionV2_build_report.txt").open('a',encoding='utf-8') as f: f.write(msg+'\n')
def remove_collection_recursive(col):
    for ch in list(col.children): remove_collection_recursive(ch)
    for obj in list(col.objects): bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(col)
def replace_collection(name,parent=None):
    old=bpy.data.collections.get(name)
    if old: remove_collection_recursive(old)
    col=bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(col)
    return col
def move_to_collection(obj,col):
    for c in list(obj.users_collection):
        try: c.objects.unlink(obj)
        except Exception: pass
    col.objects.link(obj)
def world_bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)
def dims(b): return (b[1]-b[0],b[3]-b[2],b[5]-b[4])
def look_at(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def mat_principled(name,color,roughness=.5,metallic=0,specular=.5):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name); mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links; nodes.clear(); out=nodes.new('ShaderNodeOutputMaterial'); bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value=(*color,1); bsdf.inputs['Roughness'].default_value=roughness; bsdf.inputs['Metallic'].default_value=metallic
    if 'Specular IOR Level' in bsdf.inputs: bsdf.inputs['Specular IOR Level'].default_value=specular
    elif 'Specular' in bsdf.inputs: bsdf.inputs['Specular'].default_value=specular
    links.new(bsdf.outputs['BSDF'],out.inputs['Surface']); return mat
def mat_emission(name,color,strength=1):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name); mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links; nodes.clear(); out=nodes.new('ShaderNodeOutputMaterial'); em=nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value=(*color,1); em.inputs['Strength'].default_value=strength; links.new(em.outputs['Emission'],out.inputs['Surface']); return mat
def mat_knit(name='PRV2_MAT_CrochetBrown'):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name); mat.use_nodes=True
    n=mat.node_tree.nodes; l=mat.node_tree.links; n.clear(); out=n.new('ShaderNodeOutputMaterial'); bsdf=n.new('ShaderNodeBsdfPrincipled'); coord=n.new('ShaderNodeTexCoord'); mapping=n.new('ShaderNodeMapping'); wave=n.new('ShaderNodeTexWave'); bump=n.new('ShaderNodeBump')
    bsdf.inputs['Base Color'].default_value=(0.215,0.095,0.043,1); bsdf.inputs['Roughness'].default_value=.88
    mapping.inputs['Scale'].default_value=(14,14,34); wave.wave_type='RINGS'; wave.inputs['Scale'].default_value=22; wave.inputs['Distortion'].default_value=7
    bump.inputs['Strength'].default_value=.34; bump.inputs['Distance'].default_value=.018
    l.new(coord.outputs['Generated'],mapping.inputs['Vector']); l.new(mapping.outputs['Vector'],wave.inputs['Vector']); l.new(wave.outputs['Color'],bump.inputs['Height']); l.new(bump.outputs['Normal'],bsdf.inputs['Normal']); l.new(bsdf.outputs['BSDF'],out.inputs['Surface']); return mat
def assign_mat(obj,mat):
    if hasattr(obj.data,'materials'): obj.data.materials.clear(); obj.data.materials.append(mat)
def add_uv(name,loc,scale,col,mat=None,segments=48,rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc); obj=bpy.context.object; obj.name=name; obj.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in obj.data.polygons: p.use_smooth=True
    move_to_collection(obj,col); assign_mat(obj,mat) if mat else None; return obj
def add_cube(name,loc,scale,col,mat=None,bevel=0):
    bpy.ops.mesh.primitive_cube_add(location=loc); obj=bpy.context.object; obj.name=name; obj.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); move_to_collection(obj,col)
    if mat: assign_mat(obj,mat)
    if bevel: obj.modifiers.new('bevel','BEVEL').width=bevel; obj.modifiers.new('weighted_normals','WEIGHTED_NORMAL')
    return obj
def add_cyl(name,loc,radius,depth,col,mat=None,vertices=32,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc,rotation=rotation); obj=bpy.context.object; obj.name=name; move_to_collection(obj,col); assign_mat(obj,mat) if mat else None; return obj
def add_torus(name,loc,col,mat=None,major=.22,minor=.045,rotation=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=12, location=loc, rotation=rotation); obj=bpy.context.object; obj.name=name; move_to_collection(obj,col); assign_mat(obj,mat) if mat else None; return obj
def add_curve_poly(name,points,col,mat,bevel=.006):
    curve=bpy.data.curves.new(name+'_Curve','CURVE'); curve.dimensions='3D'; curve.bevel_depth=bevel; curve.bevel_resolution=2; sp=curve.splines.new('POLY'); sp.points.add(len(points)-1)
    for p,co in zip(sp.points,points): p.co=(co[0],co[1],co[2],1)
    obj=bpy.data.objects.new(name,curve); col.objects.link(obj); obj.data.materials.append(mat); return obj
def force_vis(obj):
    obj.hide_viewport=False; obj.hide_render=False
    for c in obj.users_collection: c.hide_viewport=False; c.hide_render=False
def duplicate_full(source,col):
    dup=source.copy(); dup.data=source.data.copy(); dup.name='PRV2_Meshy_ComparisonBody'; col.objects.link(dup); assign_mat(dup,mat_knit()); return dup
def create_clean_puppet(col,b):
    sx,sy,sz=dims(b); z0=b[4]; x0=sx*1.55; knit=mat_knit('PRV2_MAT_CleanPuppet_Crochet'); eye=mat_principled('PRV2_MAT_GlossyBlackEyes',(0.002,0.002,0.003),.08,0,1); mouth=mat_principled('PRV2_MAT_MouthDark',(0.004,0.001,0),.7,0); stitch=mat_principled('PRV2_MAT_StitchDark',(0.10,0.035,0.015),.9,0)
    add_uv('CLEANPUPPET_Torso',(x0,0,z0+sz*.38),(sx*.19,sy*.28,sz*.17),col,knit)
    head=add_cube('CLEANPUPPET_Head',(x0,0,z0+sz*.76),(sx*.34,sy*.36,sz*.22),col,knit,.16)
    add_cyl('CLEANPUPPET_Neck',(x0,0,z0+sz*.58),sx*.055,sz*.10,col,knit)
    for side,label in [(-1,'L'),(1,'R')]:
        add_cyl(f'CLEANPUPPET_UpperArm_{label}',(x0+side*sx*.26,0,z0+sz*.50),sx*.052,sx*.34,col,knit,32,(0,math.pi/2,0)); add_cyl(f'CLEANPUPPET_Forearm_{label}',(x0+side*sx*.43,0,z0+sz*.48),sx*.048,sx*.24,col,knit,32,(0,math.pi/2,0))
        add_uv(f'CLEANPUPPET_Hand_{label}',(x0+side*sx*.56,0,z0+sz*.47),(sx*.085,sy*.105,sz*.045),col,knit,32,16)
        for i,zz in enumerate([z0+sz*.495,z0+sz*.470,z0+sz*.445]): add_curve_poly(f'CLEANPUPPET_HandFingerShade_{label}_{i}',[(x0+side*sx*.60-side*sx*.035,-sy*.115,zz),(x0+side*sx*.60+side*sx*.020,-sy*.115,zz)],col,stitch,.003)
        add_uv(f'CLEANPUPPET_Thigh_{label}',(x0+side*sx*.10,0,z0+sz*.22),(sx*.085,sy*.14,sz*.16),col,knit,32,16); add_uv(f'CLEANPUPPET_Foot_{label}',(x0+side*sx*.10,-sy*.055,z0+sz*.04),(sx*.105,sy*.22,sz*.045),col,knit,32,16)
    yfront=-sy*.38; add_uv('CLEANPUPPET_Eye_L',(x0-sx*.105,yfront,z0+sz*.80),(sx*.035,sy*.018,sz*.025),col,eye,24,12); add_uv('CLEANPUPPET_Eye_R',(x0+sx*.105,yfront,z0+sz*.80),(sx*.035,sy*.018,sz*.025),col,eye,24,12)
    add_curve_poly('CLEANPUPPET_Smile',[(x0-sx*.16,yfront-.006,z0+sz*.705),(x0-sx*.07,yfront-.015,z0+sz*.690),(x0,yfront-.020,z0+sz*.688),(x0+sx*.07,yfront-.015,z0+sz*.690),(x0+sx*.16,yfront-.006,z0+sz*.705)],col,mouth,.010)
    for row in range(8):
        z=z0+sz*(.63+row*.035)
        for j in range(-5,6):
            x=x0+j*sx*.045+(row%2)*sx*.022; add_curve_poly(f'CLEANPUPPET_HeadKnit_{row}_{j}',[(x-sx*.015,yfront-.004,z+sz*.004),(x,yfront-.004,z-sz*.008),(x+sx*.015,yfront-.004,z+sz*.004)],col,stitch,.0025)
    return x0
def create_clothes(col,b,x0):
    sx,sy,sz=dims(b); z0=b[4]; black=mat_principled('PRV2_MAT_BlackHoodie',(0.006,0.006,0.007),.85,0); denim=mat_principled('PRV2_MAT_Denim',(0.035,0.115,0.235),.78,0); shoe_black=mat_principled('PRV2_MAT_ShoeBlack',(0.003,0.003,0.004),.4,0); white=mat_principled('PRV2_MAT_ShoeWhite',(0.82,0.82,0.78),.45,0); flame=mat_principled('PRV2_MAT_ShoeFlameOrange',(1,.20,.01),.55,0)
    add_uv('CLEANPUPPET_HoodieTorso',(x0,0,z0+sz*.40),(sx*.215,sy*.32,sz*.18),col,black); add_uv('CLEANPUPPET_Hood',(x0,0,z0+sz*.78),(sx*.39,sy*.42,sz*.24),col,black)
    for side,label in [(-1,'L'),(1,'R')]:
        add_cyl(f'CLEANPUPPET_Sleeve_{label}',(x0+side*sx*.36,0,z0+sz*.50),sx*.075,sx*.39,col,black,32,(0,math.pi/2,0)); add_uv(f'CLEANPUPPET_JeanLeg_{label}',(x0+side*sx*.10,0,z0+sz*.18),(sx*.095,sy*.18,sz*.17),col,denim,32,16)
        add_uv(f'CLEANPUPPET_BlackSkateShoe_{label}',(x0+side*sx*.10,-sy*.08,z0+sz*.035),(sx*.13,sy*.25,sz*.045),col,shoe_black,40,18); add_uv(f'CLEANPUPPET_ShoeWhiteToe_{label}',(x0+side*sx*.10,-sy*.20,z0+sz*.045),(sx*.07,sy*.055,sz*.022),col,white,24,12); add_cube(f'CLEANPUPPET_ShoeWhiteSole_{label}',(x0+side*sx*.10,-sy*.08,z0+sz*.010),(sx*.14,sy*.26,sz*.012),col,white,.01)
        for k in range(3): add_cube(f'CLEANPUPPET_ShoeFlame_{label}_{k}',(x0+side*sx*(.07+.02*k),-sy*.23,z0+sz*(.04+.015*k)),(sx*.012,sy*.012,sz*.022),col,flame,.005)
def create_env(col_env,col_car,col_lights,b):
    sx,sy,sz=dims(b); z0=b[4]; asphalt=mat_principled('PRV2_MAT_AsphaltDark',(.015,.016,.017),.96,0); facade=mat_principled('PRV2_MAT_WarmFacade',(.135,.095,.055),.68,0); glass=mat_principled('PRV2_MAT_DarkStoreGlass',(.003,.006,.009),.12,.2); metal=mat_principled('PRV2_MAT_DarkMetal',(.025,.025,.027),.35,.6)
    add_cube('PRV2_Asphalt_Lot',(0,2.3,z0-.08),(sx*4,sz*2.8,.06),col_env,asphalt,.02); add_cube('PRV2_StripMall_Body',(0,4.9,z0+sz*.72),(sx*3.5,.35,sz*.70),col_env,facade,.03)
    for i,x in enumerate([-sx*1.35,-sx*.45,sx*.45,sx*1.35]): add_cube(f'PRV2_StoreGlass_{i}',(x,4.58,z0+sz*.62),(sx*.32,.035,sz*.38),col_env,glass,.01)
    for idx,x in enumerate([-sx*1.05,sx*1.20]):
        add_cyl(f'PRV2_LampPole_{idx}',(x,1.15,z0+sz*.95),.035,sz*1.8,col_env,metal,24); add_cube(f'PRV2_LampHead_{idx}',(x,1.15,z0+sz*1.86),(.22,.14,.06),col_env,metal,.02)
        data=bpy.data.lights.new(f'PRV2_OverheadAmber_{idx}_Data','AREA'); data.energy=450 if idx==0 else 230; data.color=(1,.35,.055); data.shape='DISK'; data.size=2.2; light=bpy.data.objects.new(f'PRV2_OverheadAmber_{idx}',data); light.location=(x,1.15,z0+sz*1.78); col_lights.objects.link(light)
    create_car(col_car,col_lights,b)
def create_car(col_car,col_lights,b):
    sx,sy,sz=dims(b); z0=b[4]; cx=-sx*1.15; cy=2.45; cz=z0+.18; body=mat_principled('PRV2_MAT_IridescentBlackCar',(.005,.009,.014),.18,.75,.9); tire=mat_principled('PRV2_MAT_TireBlack',(.002,.002,.002),.85,0); rim=mat_principled('PRV2_MAT_BlackIridescentRim',(.005,.006,.010),.22,.9,1); cyan=mat_emission('PRV2_MAT_CyanUnderglow',(0,.65,1),1.6); red=mat_emission('PRV2_MAT_RedTail',(1,.02,0),2.5)
    add_cube('PRV2_DriftCar_LowBody',(cx,cy,cz+.34),(sx*.55,sy*.55,sz*.10),col_car,body,.12); add_cube('PRV2_DriftCar_LongHood',(cx,cy-.48,cz+.39),(sx*.44,sy*.34,sz*.06),col_car,body,.10); add_cube('PRV2_DriftCar_Cabin',(cx,cy+.12,cz+.58),(sx*.34,sy*.38,sz*.10),col_car,body,.10); add_cube('PRV2_DriftCar_RearSpoiler',(cx,cy+.68,cz+.63),(sx*.42,.035,.035),col_car,body,.02); add_cube('PRV2_DriftCar_CyanUnderglowMesh',(cx,cy,cz+.16),(sx*.48,sy*.48,.012),col_car,cyan,.03)
    data=bpy.data.lights.new('PRV2_CarUnderglow_Data','AREA'); data.energy=180; data.color=(0,.65,1); data.shape='RECTANGLE'; data.size=1.6; light=bpy.data.objects.new('PRV2_CarUnderglow',data); light.location=(cx,cy,cz+.12); col_lights.objects.link(light)
    for side in [-1,1]:
        for fa in [-1,1]:
            x=cx+side*sx*.42; y=cy+fa*sy*.44; add_torus(f'PRV2_DriftCar_Tire_{side}_{fa}',(x,y,cz+.23),col_car,tire,sx*.065,sx*.022); add_torus(f'PRV2_DriftCar_Rim_{side}_{fa}',(x,y,cz+.23),col_car,rim,sx*.040,sx*.006)
    for side in [-1,1]: add_cube(f'PRV2_DriftCar_TailLight_{side}',(cx+side*sx*.22,cy+sy*.58,cz+.38),(sx*.09,.016,sz*.025),col_car,red,.01)
def create_armature(col,b,x0):
    sx,sy,sz=dims(b); z0=b[4]; bpy.ops.object.armature_add(enter_editmode=True,location=(x0,0,z0)); arm=bpy.context.object; arm.name='PRV2_CleanPuppet_Armature'; move_to_collection(arm,col); eb=arm.data.edit_bones
    for b0 in list(eb): eb.remove(b0)
    def bone(name,head,tail,parent=None):
        b1=eb.new(name); b1.head=head; b1.tail=tail; b1.parent=parent if parent else None; return b1
    root=bone('root',(0,0,0),(0,0,sz*.08)); spine=bone('spine',(0,0,sz*.08),(0,0,sz*.58),root); neck=bone('neck',(0,0,sz*.58),(0,0,sz*.70),spine); head=bone('head',(0,0,sz*.70),(0,0,sz*.98),neck)
    for side,label in [(-1,'L'),(1,'R')]:
        ua=bone(f'upper_arm.{label}',(side*sx*.12,0,sz*.54),(side*sx*.32,0,sz*.50),spine); fa=bone(f'forearm.{label}',(side*sx*.32,0,sz*.50),(side*sx*.52,0,sz*.47),ua); th=bone(f'thigh.{label}',(side*sx*.08,0,sz*.30),(side*sx*.10,0,sz*.12),root); bone(f'shin.{label}',(side*sx*.10,0,sz*.12),(side*sx*.10,0,sz*.03),th)
    bpy.ops.object.mode_set(mode='OBJECT'); arm.show_in_front=True; return arm
def setup_world():
    s=bpy.context.scene; s.render.engine='BLENDER_EEVEE'; s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.frame_start=1; s.frame_end=120; s.render.fps=24
    if s.world is None: s.world=bpy.data.worlds.new('PRV2_World')
    s.world.use_nodes=True; bg=s.world.node_tree.nodes.get('Background')
    if bg: bg.inputs['Color'].default_value=(.001,.002,.006,1); bg.inputs['Strength'].default_value=.025
def create_cameras(col,b):
    sx,sy,sz=dims(b); z0=b[4]; aim=Vector((0,0,z0+sz*.68)); specs=[('PRV2_CAM_COMPARE',(sx*3.2,-sz*2.8,z0+sz*1.15),Vector((sx*.75,0,z0+sz*.58)),42),('PRV2_CAM_HERO',(sx*2.0,-sz*2.1,z0+sz*.78),aim,50),('PRV2_CAM_LOW',(sx*1.4,-sz*1.7,z0+sz*.22),Vector((0,0,z0+sz*.58)),38)]
    cams={}
    for name,loc,target,lens in specs:
        data=bpy.data.cameras.new(name+'_Data'); cam=bpy.data.objects.new(name,data); cam.location=loc; cam.data.lens=lens; look_at(cam,target); col.objects.link(cam); cams[name]=cam
    empty=bpy.data.objects.new('PRV2_ORBIT_RIG',None); empty.location=aim; col.objects.link(empty); cams['PRV2_CAM_HERO'].parent=empty; empty.rotation_euler=(0,0,-.25); empty.keyframe_insert(data_path='rotation_euler',frame=1); empty.rotation_euler=(0,0,.95); empty.keyframe_insert(data_path='rotation_euler',frame=120); return cams
def render_preview(cams):
    s=bpy.context.scene; OUT_DIR.mkdir(parents=True,exist_ok=True)
    for name,fn in [('PRV2_CAM_COMPARE','01_Compare_Meshy_vs_CleanPuppet.png'),('PRV2_CAM_HERO','02_Hero_DarkLot.png'),('PRV2_CAM_LOW','03_LowAngle_DarkLot.png')]:
        s.camera=cams[name]; s.render.filepath=str(OUT_DIR/fn); bpy.ops.render.render(write_still=True); log('[render] '+fn)
def main():
    OUT_DIR.mkdir(parents=True,exist_ok=True); (OUT_DIR/'ProductionReconstructionV2_build_report.txt').write_text('',encoding='utf-8')
    root=replace_collection(ROOT); col_compare=replace_collection('PRV2_COMPARE_CLEAN_PUPPET',root); col_env=replace_collection('PRV2_ENVIRONMENT',root); col_car=replace_collection('PRV2_DRIFT_CAR',root); col_lights=replace_collection('PRV2_LIGHTS_PRODUCTION',root); col_cam=replace_collection('PRV2_CAMERAS',root); col_rig=replace_collection('PRV2_RIG',root)
    setup_world(); full=bpy.data.objects.get(FULL_CHARACTER_SOURCE)
    if not full or full.type!='MESH': raise RuntimeError('F2 full-character source not found.')
    force_vis(full); b=world_bounds(full); log(f'[audit] full={full.name} bounds={b} dims={dims(b)}')
    hand=bpy.data.objects.get(HAND_REFERENCE_SOURCE)
    if hand: force_vis(hand); hand.hide_render=True; hand.hide_viewport=True; log(f'[audit] hand reference retained hidden: {hand.name}')
    m=duplicate_full(full,col_compare); m.location.x-=dims(b)[0]*1.55
    x0=create_clean_puppet(col_compare,b); create_clothes(col_compare,b,x0); create_armature(col_rig,b,x0); log('[clean_puppet] created')
    create_env(col_env,col_car,col_lights,b); log('[environment] created')
    cams=create_cameras(col_cam,b); render_preview(cams)
    status={'full_character_source':full.name,'hand_reference_source':hand.name if hand else None,'hand_gate':'ACTIVE - J2B retained as direction/reference','clean_puppet_branch':'CREATED for comparison','shoes':'black skate-shoe inspired prototype','car':'drift coupe placeholder with underglow','manifest':'scene_manifest.json written'}
    (OUT_DIR/'ProductionReconstructionV2_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    export_scene_manifest(project_root()/'scene_manifest.json'); export_scene_manifest(OUT_DIR/'scene_manifest.json')
    out=project_root()/'blender'/'sackboy_scene.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(out)); log('[save] '+str(out))
if __name__=='__main__':
    try: main()
    except Exception:
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with (OUT_DIR/'ProductionReconstructionV2_FATAL_ERROR.txt').open('w',encoding='utf-8') as f: traceback.print_exc(file=f)
        raise
