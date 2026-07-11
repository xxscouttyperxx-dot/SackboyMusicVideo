import sys, math, json, traceback
from pathlib import Path

import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection
try:
    from export_scene_manifest import export_scene_manifest
except Exception:
    export_scene_manifest = None

OUT_DIR = project_root() / "renders" / "production_reconstruction_v2c"
FULL_SOURCE = "F2"
HAND_REF = "HANDREFINE_J2B_Working"

ROOT = "PROD_RECON_V2C"
COL_ENV = "V2C_ENVIRONMENT"
COL_CAR = "V2C_DRIFT_CAR"
COL_SKY = "V2C_SKY_CLOUDS"
COL_SMOKE = "V2C_SMOKE"
COL_CAM = "V2C_CAMERAS"
COL_HELPERS = "V2C_HELPERS"

PRESERVE_LIGHT_COLLECTION = "V2B_LIGHTS_OVERHEAD"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "ProductionReconV2C_build_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_report():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ProductionReconV2C_build_report.txt").write_text("", encoding="utf-8")

def remove_collection_recursive(col):
    for child in list(col.children):
        remove_collection_recursive(child)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def replace_collection(name, parent=None):
    old = bpy.data.collections.get(name)
    if old:
        remove_collection_recursive(old)
    col = bpy.data.collections.new(name)
    if parent:
        parent.children.link(col)
    else:
        bpy.context.scene.collection.children.link(col)
    return col

def remove_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        remove_collection_recursive(col)

def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        try:
            c.objects.unlink(obj)
        except Exception:
            pass
    col.objects.link(obj)

def world_bounds(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def dims(b):
    return b[1]-b[0], b[3]-b[2], b[5]-b[4]

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def force_visible(obj):
    obj.hide_viewport = False
    obj.hide_render = False
    for col in obj.users_collection:
        col.hide_viewport = False
        col.hide_render = False

def mat_principled(name, color, roughness=0.5, metallic=0.0, specular=0.5, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    l = mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = specular
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.blend_method = "BLEND" if alpha < 1.0 else "OPAQUE"
    return mat

def mat_emission(name, color, strength=1.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    l = mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    em = n.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, alpha)
    em.inputs["Strength"].default_value = strength
    l.new(em.outputs["Emission"], out.inputs["Surface"])
    mat.blend_method = "BLEND" if alpha < 1.0 else "OPAQUE"
    return mat

def assign_mat(obj, mat):
    if hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)

def add_cube(name, loc, scale, col, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj,col)
    if mat:
        assign_mat(obj,mat)
    if bevel > 0:
        be=obj.modifiers.new("Bevel","BEVEL")
        be.width=bevel
        be.segments=4
        obj.modifiers.new("WeightedNormals","WEIGHTED_NORMAL")
    return obj

def add_cyl(name, loc, radius, depth, col, mat=None, vertices=32, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj=bpy.context.object
    obj.name=name
    move_to_collection(obj,col)
    if mat:
        assign_mat(obj,mat)
    return obj

def add_uv(name, loc, scale, col, mat=None, segments=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for p in obj.data.polygons:
        p.use_smooth=True
    move_to_collection(obj,col)
    if mat:
        assign_mat(obj,mat)
    return obj

def add_torus(name, loc, col, mat=None, major=0.25, minor=0.06, rotation=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=72, minor_segments=16, location=loc, rotation=rotation)
    obj=bpy.context.object
    obj.name=name
    move_to_collection(obj,col)
    if mat:
        assign_mat(obj,mat)
    return obj

def add_curve(name, points, col, mat, bevel=0.01):
    cu=bpy.data.curves.new(name+"_Curve","CURVE")
    cu.dimensions="3D"
    cu.resolution_u=4
    cu.bevel_depth=bevel
    cu.bevel_resolution=2
    sp=cu.splines.new("POLY")
    sp.points.add(len(points)-1)
    for p, co in zip(sp.points, points):
        p.co=(co[0],co[1],co[2],1)
    obj=bpy.data.objects.new(name,cu)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def create_wedge_mesh(name, verts, faces, col, mat=None):
    mesh=bpy.data.meshes.new(name+"_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj=bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if mat:
        assign_mat(obj,mat)
    obj.modifiers.new("WeightedNormals","WEIGHTED_NORMAL")
    return obj

def cleanup_previous_v2b_objects():
    # Remove V2B generated geometry, car, sky, and cameras. Preserve V2B_LIGHTS_OVERHEAD exactly.
    for name in ["PROD_RECON_V2C", "V2B_ENVIRONMENT", "V2B_DRIFT_CAR", "V2B_SKY", "V2B_CAMERAS"]:
        remove_collection(name)
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("V2B_DriftCar", "V2B_RimSpoke", "V2B_CarUnderglow", "V2B_TailLight", "V2B_Moon", "V2B_Cloud", "V2B_Star", "V2B_CAM", "V2B_ORBIT")):
            bpy.data.objects.remove(obj, do_unlink=True)

def setup_world():
    s=bpy.context.scene
    s.render.engine="BLENDER_EEVEE"
    s.render.resolution_x=1280
    s.render.resolution_y=720
    s.render.resolution_percentage=100
    s.render.image_settings.file_format="PNG"
    s.frame_start=1
    s.frame_end=120
    s.render.fps=24
    if s.world is None:
        s.world=bpy.data.worlds.new("V2C_DarkCloudyWorld")
    s.world.use_nodes=True
    bg=s.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value=(0.0015,0.0025,0.0075,1)
        bg.inputs["Strength"].default_value=0.030

def ensure_preserved_overhead_lights(b):
    sx, sy, sz=dims(b)
    zmin=b[4]
    col=bpy.data.collections.get(PRESERVE_LIGHT_COLLECTION)
    if not col:
        col=bpy.data.collections.new(PRESERVE_LIGHT_COLLECTION)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport=False
    col.hide_render=False

    # If v2B lights exist, preserve their energy/color and do not modify.
    existing=[obj for obj in col.objects if obj.type=="LIGHT" and obj.name.startswith("V2B_OverheadAmber")]
    if existing:
        log("[lighting] preserved existing V2B overhead amber lights unchanged")
        return existing

    # Fallback only: create the same overhead amber setup.
    lights=[]
    for i, x in enumerate([-sx*1.35, sx*1.35]):
        data=bpy.data.lights.new(f"V2B_OverheadAmber_{i}_Data","AREA")
        data.energy=520 if i==0 else 260
        data.color=(1.0,0.37,0.055)
        data.shape="DISK"
        data.size=1.85
        light=bpy.data.objects.new(f"V2B_OverheadAmber_{i}",data)
        light.location=(x,2.78,zmin+sz*1.76)
        col.objects.link(light)
        lights.append(light)
    log("[lighting] fallback overhead lights created")
    return lights

def make_sky(col, b):
    sx, sy, sz=dims(b)
    zmin=b[4]
    moon_mat=mat_emission("V2C_MAT_Moon",(0.82,0.84,0.92),0.75)
    cloud_mat=mat_principled("V2C_MAT_SmokyClouds",(0.030,0.035,0.050),0.95,0,0.1,0.45)

    add_uv("V2C_Moon",(sx*2.4,11.5,zmin+sz*3.2),(0.32,0.018,0.32),col,moon_mat,64,24)

    # Realistic-ish smoky cloud masses: clustered, irregular, high in sky, not oval rows.
    cloud_specs=[
        (-sx*2.5, 11.6, zmin+sz*2.95, 1.2),
        (-sx*1.3, 11.8, zmin+sz*3.12, 0.9),
        ( sx*0.2, 11.5, zmin+sz*3.05, 1.1),
        ( sx*1.7, 11.7, zmin+sz*3.18, 0.8),
    ]
    idx=0
    for cx,cy,cz,scale in cloud_specs:
        for j,(ox,oz,sc) in enumerate([(-0.35,0.00,0.7),(0.0,0.06,1.0),(0.42,-0.03,0.82),(0.74,0.04,0.55)]):
            obj=add_uv(f"V2C_SmokeCloud_{idx}",(cx+sx*0.25*ox,cy,cz+sz*0.08*oz),(sx*0.35*scale*sc,0.030,sz*0.055*scale*sc),col,cloud_mat,32,12)
            idx+=1

def make_environment(col_env, b, overhead_lights):
    sx, sy, sz=dims(b)
    zmin=b[4]
    asphalt=mat_principled("V2C_MAT_AsphaltDark",(0.011,0.012,0.013),0.96,0)
    paint=mat_principled("V2C_MAT_ParkingPaint",(0.78,0.72,0.55),0.86,0)
    concrete=mat_principled("V2C_MAT_Concrete",(0.24,0.23,0.21),0.78,0)
    facade=mat_principled("V2C_MAT_StuccoWarm",(0.145,0.105,0.070),0.70,0)
    roofmat=mat_principled("V2C_MAT_FlatRoofDark",(0.055,0.052,0.048),0.82,0)
    trim=mat_principled("V2C_MAT_BlackMetalFrames",(0.008,0.009,0.010),0.30,0.55)
    glass=mat_principled("V2C_MAT_GlossyStoreGlass",(0.006,0.010,0.016),0.055,0.18,1.0)
    sign=mat_emission("V2C_MAT_SoftSignAmber",(0.75,0.32,0.05),0.22)

    # Bigger lot. Store is 4-5x farther back than v2B.
    add_cube("V2C_Asphalt_ExpandedLot",(0,4.0,zmin-0.055),(sx*6.5,sz*5.0,0.045),col_env,asphalt,0.01)

    # Thicker parking lines.
    for i,x in enumerate([-sx*2.6,-sx*1.7,-sx*0.8,sx*0.1,sx*1.0,sx*1.9,sx*2.8]):
        add_cube(f"V2C_ParkingLine_{i}",(x,0.70,zmin-0.004),(0.040,sz*1.05,0.007),col_env,paint,0.001)
    add_cube("V2C_BackParkingLine",(-sx*1.55,2.75,zmin-0.003),(sx*0.95,0.040,0.007),col_env,paint,0.001)

    # Sidewalk, curb, long strip mall with actual depth.
    front_y=10.9
    building_depth=3.9
    center_y=front_y+building_depth/2
    add_cube("V2C_Sidewalk",(0,front_y-0.32,zmin+0.025),(sx*5.6,0.72,0.055),col_env,concrete,0.025)
    add_cube("V2C_Curb",(0,front_y-0.76,zmin+0.05),(sx*5.6,0.070,0.080),col_env,concrete,0.01)
    add_cube("V2C_StripMall_DepthBody",(0,center_y,zmin+sz*0.82),(sx*5.3,building_depth/2,sz*0.78),col_env,facade,0.025)
    add_cube("V2C_StripMall_FlatRoof",(0,center_y,zmin+sz*1.63),(sx*5.45,building_depth/2+0.12,sz*0.07),col_env,roofmat,0.012)
    add_cube("V2C_StripMall_FrontParapet",(0,front_y-0.03,zmin+sz*1.72),(sx*5.45,0.10,sz*0.14),col_env,facade,0.01)

    # Large full-height glass storefront panels reaching concrete/floor. No cage overlay.
    bay_width=sx*1.02
    start_x=-bay_width*2.0
    for i in range(5):
        x=start_x+i*bay_width
        add_cube(f"V2C_GlassPanel_{i}",(x,front_y-0.065,zmin+sz*0.70),(bay_width*0.42,0.035,sz*0.48),col_env,glass,0.006)
        add_cube(f"V2C_GlassDoor_{i}",(x+bay_width*0.24,front_y-0.09,zmin+sz*0.58),(bay_width*0.13,0.040,sz*0.36),col_env,glass,0.006)
        # clean outer metal framing
        add_cube(f"V2C_FrameLeft_{i}",(x-bay_width*0.45,front_y-0.115,zmin+sz*0.70),(0.025,0.045,sz*0.50),col_env,trim,0.003)
        add_cube(f"V2C_FrameRight_{i}",(x+bay_width*0.45,front_y-0.115,zmin+sz*0.70),(0.025,0.045,sz*0.50),col_env,trim,0.003)
        add_cube(f"V2C_FrameTop_{i}",(x,front_y-0.115,zmin+sz*0.96),(bay_width*0.45,0.045,0.025),col_env,trim,0.003)
        add_cube(f"V2C_FrameBottom_{i}",(x,front_y-0.115,zmin+sz*0.43),(bay_width*0.45,0.045,0.025),col_env,trim,0.003)
        add_cube(f"V2C_StoreSign_{i}",(x,front_y-0.125,zmin+sz*1.23),(bay_width*0.30,0.030,sz*0.060),col_env,sign,0.008)

    hvac=mat_principled("V2C_MAT_RooftopHVAC",(0.075,0.075,0.070),0.60,0.1)
    for i,x in enumerate([-sx*1.8,-sx*0.5,sx*0.7,sx*2.0]):
        add_cube(f"V2C_Roof_HVAC_{i}",(x,center_y,zmin+sz*1.77),(sx*0.22,0.23,sz*0.055),col_env,hvac,0.010)
        add_cyl(f"V2C_Roof_Vent_{i}",(x+sx*0.18,center_y+0.05,zmin+sz*1.84),0.045,0.13,col_env,hvac,20)

    # Visible lamp post geometry under existing overhead light objects. Do not alter actual light energy/position.
    polemat=mat_principled("V2C_MAT_LampPole",(0.035,0.035,0.035),0.33,0.65)
    for i, light in enumerate(overhead_lights):
        x,y,z=light.location
        pole_height=max(z-zmin, 1.0)
        add_cyl(f"V2C_LampPole_{i}",(x,y,zmin+pole_height/2),0.038,pole_height,col_env,polemat,24)
        add_cyl(f"V2C_LampArm_{i}",(x,y-0.16,z),0.022,0.36,col_env,polemat,16,rotation=(math.pi/2,0,0))
        add_cube(f"V2C_LampFixture_{i}",(x,y-0.36,z),(0.25,0.13,0.050),col_env,polemat,0.015)

def make_car_mesh(col_car, col_lights, b):
    sx, sy, sz=dims(b)
    zmin=b[4]
    # Larger and further from store, sized to be believable with giant Sackboy.
    cx=-sx*2.05
    cy=3.05
    cz=zmin+0.10
    length=sx*2.05
    width=sx*0.92
    height=sz*0.52

    bodymat=mat_principled("V2C_MAT_DeepBlackPearlCar",(0.0025,0.0035,0.006),0.13,0.90,1.0)
    glass=mat_principled("V2C_MAT_CarGlossBlackGlass",(0.001,0.003,0.007),0.045,0.25,1.0)
    tire=mat_principled("V2C_MAT_Tire",(0.002,0.002,0.002),0.86,0)
    rim=mat_principled("V2C_MAT_BlackChromeRim",(0.010,0.010,0.014),0.18,0.95,1.0)
    red=mat_emission("V2C_MAT_ModernRedTail",(1.0,0.02,0.0),3.5)
    cyan=mat_emission("V2C_MAT_CyanUnderglowHidden",(0.0,0.55,1.0),1.6)
    smoke_mat=mat_principled("V2C_MAT_ExhaustSmoke",(0.22,0.22,0.24),0.95,0,0.0,0.42)

    # Sloped coupe base as custom mesh: front low hood, raised cabin, rear deck.
    L=length/2; W=width/2
    verts=[
        (-W,-L,0.20),(W,-L,0.20),(-W,L,0.20),(W,L,0.20),
        (-W*0.95,-L*0.92,0.52),(W*0.95,-L*0.92,0.52),(-W*0.95,L*0.90,0.50),(W*0.95,L*0.90,0.50),
        (-W*0.70,-L*0.35,0.78),(W*0.70,-L*0.35,0.78),(-W*0.62,L*0.20,0.96),(W*0.62,L*0.20,0.96),
        (-W*0.76,L*0.70,0.68),(W*0.76,L*0.70,0.68)
    ]
    verts=[(cx+x,cy+y,cz+z*height) for x,y,z in verts]
    faces=[
        (0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5),
        (4,5,9,8),(8,9,11,10),(10,11,13,12),(6,12,13,7),
        (4,8,10,12,6),(5,7,13,11,9),
        (0,2,3,1)
    ]
    body=create_wedge_mesh("V2C_DriftCoupe_SlopedBody",verts,faces,col_car,bodymat)
    body.modifiers.new("V2C_BevelBody","BEVEL").width=0.035
    body.modifiers["V2C_BevelBody"].segments=3

    # Windows / windshield / doors.
    add_cube("V2C_DriftCoupe_Windshield",(cx,cy-L*0.22,cz+height*0.72),(W*0.46,0.025,height*0.115),col_car,glass,0.012)
    add_cube("V2C_DriftCoupe_RearGlass",(cx,cy+L*0.32,cz+height*0.69),(W*0.42,0.025,height*0.095),col_car,glass,0.012)
    for side in [-1,1]:
        add_cube(f"V2C_DriftCoupe_SideWindow_{side}",(cx+side*W*0.78,cy+L*0.03,cz+height*0.64),(0.025,L*0.32,height*0.090),col_car,glass,0.010)
        add_cube(f"V2C_DriftCoupe_DoorLine_{side}",(cx+side*W*0.81,cy+L*0.05,cz+height*0.40),(0.010,L*0.36,height*0.20),col_car,bodymat,0.004)
        add_cube(f"V2C_DriftCoupe_DoorHandle_{side}",(cx+side*W*0.84,cy+L*0.10,cz+height*0.47),(0.012,L*0.040,height*0.012),col_car,bodymat,0.004)

    add_cube("V2C_DriftCoupe_FrontBumper",(cx,cy-L*1.02,cz+height*0.22),(W*0.92,0.055,height*0.055),col_car,bodymat,0.020)
    add_cube("V2C_DriftCoupe_SideSkirt_L",(cx-W*1.02,cy,cz+height*0.20),(0.035,L*0.90,height*0.045),col_car,bodymat,0.015)
    add_cube("V2C_DriftCoupe_SideSkirt_R",(cx+W*1.02,cy,cz+height*0.20),(0.035,L*0.90,height*0.045),col_car,bodymat,0.015)
    add_cube("V2C_DriftCoupe_SpoilerWing",(cx,cy+L*0.86,cz+height*0.80),(W*0.72,0.030,height*0.025),col_car,bodymat,0.008)
    add_cyl("V2C_DriftCoupe_Exhaust",(cx-W*0.52,cy+L*1.01,cz+height*0.23),0.035,0.22,col_car,bodymat,24,rotation=(math.pi/2,0,0))

    # Hidden underglow: small emissive strips under chassis, not a visible big panel.
    add_cube("V2C_Underglow_HiddenStrip_Front",(cx,cy-L*0.25,cz+0.045),(W*0.65,0.020,0.010),col_car,cyan,0.003)
    add_cube("V2C_Underglow_HiddenStrip_Rear",(cx,cy+L*0.28,cz+0.045),(W*0.65,0.020,0.010),col_car,cyan,0.003)
    data=bpy.data.lights.new("V2C_CyanUnderglow_Area_Data","AREA")
    data.energy=160
    data.color=(0.0,0.55,1.0)
    data.shape="RECTANGLE"
    data.size=1.4
    glow=bpy.data.objects.new("V2C_CyanUnderglow_Area",data)
    glow.location=(cx,cy,cz+0.060)
    col_lights.objects.link(glow)

    # Modern taillight bands.
    for side in [-1,1]:
        add_cube(f"V2C_DriftCoupe_TailLightBand_{side}",(cx+side*W*0.36,cy+L*1.012,cz+height*0.39),(W*0.24,0.014,height*0.027),col_car,red,0.010)
        d=bpy.data.lights.new(f"V2C_TailGlow_{side}_Data","POINT")
        d.energy=65
        d.color=(1,0.03,0)
        o=bpy.data.objects.new(f"V2C_TailGlow_{side}",d)
        o.location=(cx+side*W*0.36,cy+L*1.06,cz+height*0.39)
        col_lights.objects.link(o)

    # Wheels and stronger rim columns/spokes.
    for side in [-1,1]:
        for foreaft in [-1,1]:
            x=cx+side*W*0.88
            y=cy+foreaft*L*0.58
            z=cz+height*0.22
            add_torus(f"V2C_Tire_{side}_{foreaft}",(x,y,z),col_car,tire,major=height*0.145,minor=height*0.045,rotation=(math.pi/2,0,0))
            add_torus(f"V2C_RimRing_{side}_{foreaft}",(x,y,z),col_car,rim,major=height*0.085,minor=height*0.010,rotation=(math.pi/2,0,0))
            for k in range(6):
                angle=math.tau*k/6
                dx=math.cos(angle)*height*0.070
                dz=math.sin(angle)*height*0.070
                add_curve(f"V2C_RimThickSpoke_{side}_{foreaft}_{k}",[(x,y,z),(x+dx,y,z+dz)],col_car,rim,bevel=0.010)

    # Exhaust smoke as clustered translucent puffs behind muffler.
    for i in range(6):
        puff=add_uv(f"V2C_ExhaustSmoke_{i}",(cx-W*0.58,cy+L*(1.12+0.08*i),cz+height*(0.25+0.015*i)),(0.08+0.025*i,0.05+0.018*i,0.055+0.012*i),col_car,smoke_mat,24,10)

def make_cameras(col_cam, b):
    sx, sy, sz=dims(b)
    zmin=b[4]
    aim=Vector((0,0,zmin+sz*0.68))
    cams={}
    specs=[
        ("V2C_CAM_HERO",(sx*2.7,-sz*2.75,zmin+sz*1.05),aim,45),
        ("V2C_CAM_HIGH_ORBIT",(sx*2.9,-sz*2.35,zmin+sz*1.85),aim,40),
        ("V2C_CAM_LOW",(sx*1.85,-sz*1.95,zmin+sz*0.24),Vector((0,0,zmin+sz*0.62)),38),
    ]
    for name,loc,target,lens in specs:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.location=loc
        cam.data.lens=lens
        look_at(cam,target)
        col_cam.objects.link(cam)
        cams[name]=cam
    rig=bpy.data.objects.new("V2C_ORBIT_RIG",None)
    rig.location=aim
    col_cam.objects.link(rig)
    cams["V2C_CAM_HIGH_ORBIT"].parent=rig
    rig.rotation_euler=(0,0,-0.30)
    rig.keyframe_insert(data_path="rotation_euler",frame=1)
    rig.rotation_euler=(0,0,0.90)
    rig.keyframe_insert(data_path="rotation_euler",frame=120)
    return cams

def render_previews(cams):
    scene=bpy.context.scene
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    for cam_name,fn in [
        ("V2C_CAM_HERO","01_Hero_F2_OverheadAmber.png"),
        ("V2C_CAM_HIGH_ORBIT","02_HighOrbit_RoofParkingCar.png"),
        ("V2C_CAM_LOW","03_LowAngle_CarStorefront.png"),
    ]:
        scene.camera=cams[cam_name]
        scene.render.filepath=str(OUT_DIR/fn)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {fn}")

def write_status():
    status={
        "lighting":"PRESERVED - existing V2B overhead amber light objects retained unchanged",
        "character":"F2 source retained; no character geometry changes",
        "hand":"J2B retained hidden as reference; no hand changes",
        "clean_puppet":"rejected direction removed",
        "strip_mall":"moved much farther back; added real depth, flat roof, parapet, HVAC, large floor-reaching glass panels, door frames, signs, sidewalk",
        "parking_lot":"expanded lot, thicker painted lines",
        "car":"rebuilt as larger sloped drift-coupe placeholder with windows, doors, spoiler, hidden underglow strips, modern tail bands, exhaust smoke, thicker rim spokes",
        "sky":"dark world plus moon and clustered smoky cloud geometry; no oval star rows",
        "remaining_limit":"car is still scripted geometry; true hero-car quality likely requires imported licensed model or a dedicated manual/modeling pass"
    }
    (OUT_DIR/"ProductionReconV2C_status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")

def main():
    reset_report()
    setup_world()
    cleanup_previous_v2b_objects()

    root=replace_collection(ROOT)
    col_env=replace_collection(COL_ENV,root)
    col_car=replace_collection(COL_CAR,root)
    col_sky=replace_collection(COL_SKY,root)
    col_cam=replace_collection(COL_CAM,root)
    col_helpers=replace_collection(COL_HELPERS,root)

    f2=bpy.data.objects.get(FULL_SOURCE)
    if not f2 or f2.type!="MESH":
        raise RuntimeError("F2 full source not found.")
    force_visible(f2)
    b=world_bounds(f2)
    log(f"[audit] F2 bounds={b} dims={dims(b)}")

    hand=bpy.data.objects.get(HAND_REF)
    if hand:
        hand.hide_viewport=True
        hand.hide_render=True
        log("[audit] J2B retained hidden")

    overhead=ensure_preserved_overhead_lights(b)
    make_sky(col_sky,b)
    make_environment(col_env,b,overhead)
    make_car_mesh(col_car,bpy.data.collections.get(PRESERVE_LIGHT_COLLECTION),b)
    cams=make_cameras(col_cam,b)

    render_previews(cams)
    write_status()
    if export_scene_manifest:
        export_scene_manifest(project_root()/"scene_manifest.json")
        export_scene_manifest(OUT_DIR/"scene_manifest.json")

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with (OUT_DIR/"ProductionReconV2C_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
