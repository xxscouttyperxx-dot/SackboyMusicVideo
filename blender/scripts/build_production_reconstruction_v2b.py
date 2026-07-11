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

OUT_DIR = project_root() / "renders" / "production_reconstruction_v2b"
FULL_SOURCE = "F2"
HAND_REF = "HANDREFINE_J2B_Working"

ROOT = "PROD_RECON_V2B"
COL_ENV = "V2B_ENVIRONMENT"
COL_CAR = "V2B_DRIFT_CAR"
COL_LIGHTS = "V2B_LIGHTS_OVERHEAD"
COL_CAM = "V2B_CAMERAS"
COL_SKY = "V2B_SKY"
COL_HELPERS = "V2B_HELPERS"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "ProductionReconV2B_build_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_report():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ProductionReconV2B_build_report.txt").write_text("", encoding="utf-8")

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

def hide_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        col.hide_viewport = True
        col.hide_render = True

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

def center(b):
    return Vector(((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2))

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def mat_principled(name, color, roughness=0.5, metallic=0.0, specular=0.5):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    l = mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = specular
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def mat_emission(name, color, strength=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    l = mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    em = n.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    l.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat

def assign_mat(obj, mat):
    if hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)

def add_cube(name, loc, scale, col, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, col)
    if mat:
        assign_mat(obj, mat)
    if bevel > 0:
        be = obj.modifiers.new("Bevel", "BEVEL")
        be.width = bevel
        be.segments = 3
        obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
    return obj

def add_cyl(name, loc, radius, depth, col, mat=None, vertices=32, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, col)
    if mat:
        assign_mat(obj, mat)
    return obj

def add_uv(name, loc, scale, col, mat=None, segments=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for p in obj.data.polygons:
        p.use_smooth = True
    move_to_collection(obj, col)
    if mat:
        assign_mat(obj, mat)
    return obj

def add_torus(name, loc, col, mat=None, major=0.22, minor=0.045, rotation=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=64, minor_segments=14, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, col)
    if mat:
        assign_mat(obj, mat)
    return obj

def add_curve(name, points, col, mat, bevel=0.01):
    cu = bpy.data.curves.new(name + "_Curve", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 3
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(points)-1)
    for p, co in zip(sp.points, points):
        p.co = (co[0], co[1], co[2], 1)
    obj = bpy.data.objects.new(name, cu)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def force_visible(obj):
    obj.hide_viewport = False
    obj.hide_render = False
    for col in obj.users_collection:
        col.hide_viewport = False
        col.hide_render = False

def cleanup_bad_preview():
    # Remove failed V2 procedural puppet branch; keep any old baseline character collections.
    for name in [
        "PROD_RECON_V2",
        "PRV2_COMPARE_CLEAN_PUPPET",
        "PRV2_ENVIRONMENT",
        "PRV2_DRIFT_CAR",
        "PRV2_LIGHTS_PRODUCTION",
        "PRV2_LIGHTS_DIAGNOSTIC",
        "PRV2_CAMERAS",
        "PRV2_RIG",
    ]:
        col = bpy.data.collections.get(name)
        if col:
            log(f"[cleanup] removing {name}")
            remove_collection_recursive(col)
    # Remove all cameras and PRV2/V2B lights so viewport is readable.
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA" or obj.type == "LIGHT" or obj.name.startswith("PRV2_") or obj.name.startswith("CLEANPUPPET_"):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass

def setup_world():
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x = 1280
    s.render.resolution_y = 720
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.frame_start = 1
    s.frame_end = 120
    s.render.fps = 24
    if s.world is None:
        s.world = bpy.data.worlds.new("V2B_DarkCloudyWorld")
    s.world.use_nodes = True
    bg = s.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.002, 0.004, 0.011, 1)
        bg.inputs["Strength"].default_value = 0.035

def make_sky(col_sky, b):
    sx, sy, sz = dims(b)
    zmin = b[4]
    moon_mat = mat_emission("V2B_MAT_Moon", (0.78, 0.82, 0.95), 1.1)
    cloud_mat = mat_principled("V2B_MAT_DimClouds", (0.035, 0.040, 0.055), 0.9, 0)
    star_mat = mat_emission("V2B_MAT_MinimalStars", (0.55, 0.62, 0.80), 0.30)

    add_uv("V2B_Moon", (sx*2.2, 5.8, zmin+sz*2.6), (0.20,0.015,0.20), col_sky, moon_mat, 48, 20)
    for i, (x,y,z,scale) in enumerate([
        (-sx*2.0, 6.0, zmin+sz*2.3, 0.8),
        (sx*0.2, 5.9, zmin+sz*2.45, 1.0),
        (sx*1.8, 6.1, zmin+sz*2.25, 0.9),
    ]):
        add_uv(f"V2B_Cloud_{i}", (x,y,z), (sx*0.55*scale, 0.025, sz*0.075*scale), col_sky, cloud_mat, 32, 12)
    for i in range(12):
        x = -sx*2.4 + (i % 6) * sx*0.85
        z = zmin + sz*(2.0 + 0.12*(i//6))
        add_uv(f"V2B_Star_{i}", (x, 6.05, z), (0.012,0.004,0.012), col_sky, star_mat, 12, 6)

def make_environment(col_env, col_lights, b):
    sx, sy, sz = dims(b)
    zmin = b[4]
    asphalt = mat_principled("V2B_MAT_Asphalt", (0.013,0.014,0.015), 0.95, 0)
    paint = mat_principled("V2B_MAT_ParkingLine", (0.75,0.70,0.55), 0.82, 0)
    curb = mat_principled("V2B_MAT_SidewalkConcrete", (0.25,0.23,0.20), 0.75, 0)
    facade = mat_principled("V2B_MAT_StripMallStucco", (0.16,0.12,0.075), 0.65, 0)
    trim = mat_principled("V2B_MAT_DarkStoreTrim", (0.018,0.018,0.020), 0.38, 0.4)
    glass = mat_principled("V2B_MAT_DarkGlass", (0.004,0.008,0.013), 0.10, 0.25)
    sign_mat = mat_emission("V2B_MAT_SignDim", (0.8,0.45,0.12), 0.35)

    # Larger lot, store farther back, character in open space.
    add_cube("V2B_Asphalt_LargeLot", (0, 1.1, zmin-0.055), (sx*5.2, sz*3.5, 0.045), col_env, asphalt, 0.01)

    # Parking lines angled/straight.
    for i, x in enumerate([-sx*2.0, -sx*1.2, -sx*0.4, sx*0.4, sx*1.2, sx*2.0]):
        add_cube(f"V2B_ParkingLine_{i}", (x, -0.25, zmin-0.005), (0.018, sz*0.72, 0.006), col_env, paint, 0.001)
    add_cube("V2B_ParkingStopLine", (-sx*1.15, 2.2, zmin-0.003), (sx*0.65, 0.018, 0.006), col_env, paint, 0.001)

    # Sidewalk and curb.
    add_cube("V2B_Sidewalk", (0, 4.22, zmin+0.025), (sx*4.4, 0.50, 0.055), col_env, curb, 0.02)
    add_cube("V2B_Curb", (0, 3.72, zmin+0.045), (sx*4.4, 0.055, 0.075), col_env, curb, 0.01)

    # Strip mall with roof, parapet, frames, doors.
    add_cube("V2B_StripMall_Main", (0, 5.05, zmin+sz*0.76), (sx*4.2, 0.38, sz*0.72), col_env, facade, 0.025)
    add_cube("V2B_StripMall_Roof", (0, 5.10, zmin+sz*1.48), (sx*4.35, 0.52, sz*0.08), col_env, trim, 0.02)
    add_cube("V2B_StripMall_Parapet", (0, 4.75, zmin+sz*1.58), (sx*4.35, 0.12, sz*0.13), col_env, facade, 0.015)

    for i, x in enumerate([-sx*1.55, -sx*0.52, sx*0.52, sx*1.55]):
        add_cube(f"V2B_Store_Window_{i}", (x, 4.64, zmin+sz*0.74), (sx*0.37, 0.035, sz*0.38), col_env, glass, 0.008)
        add_cube(f"V2B_Store_Door_{i}", (x+sx*0.27, 4.61, zmin+sz*0.59), (sx*0.12, 0.04, sz*0.33), col_env, glass, 0.006)
        add_cube(f"V2B_Store_Frame_Top_{i}", (x, 4.58, zmin+sz*0.97), (sx*0.42, 0.045, 0.018), col_env, trim, 0.004)
        add_cube(f"V2B_Store_Frame_Bottom_{i}", (x, 4.58, zmin+sz*0.50), (sx*0.42, 0.045, 0.018), col_env, trim, 0.004)
        add_cube(f"V2B_Store_Frame_Left_{i}", (x-sx*0.42, 4.58, zmin+sz*0.74), (0.018, 0.045, sz*0.25), col_env, trim, 0.004)
        add_cube(f"V2B_Store_Frame_Right_{i}", (x+sx*0.42, 4.58, zmin+sz*0.74), (0.018, 0.045, sz*0.25), col_env, trim, 0.004)
        add_cube(f"V2B_Store_Sign_{i}", (x, 4.55, zmin+sz*1.19), (sx*0.34, 0.030, sz*0.055), col_env, sign_mat, 0.01)

    # Roof AC boxes/vents visible from high orbit.
    hvac_mat = mat_principled("V2B_MAT_RooftopHVAC", (0.08,0.08,0.075), 0.55, 0.2)
    for i, x in enumerate([-sx*1.1, sx*0.1, sx*1.25]):
        add_cube(f"V2B_Rooftop_HVAC_{i}", (x,5.10,zmin+sz*1.70), (sx*0.18,0.18,sz*0.045), col_env, hvac_mat, 0.012)
        add_cyl(f"V2B_Rooftop_Vent_{i}", (x+sx*0.16,5.10,zmin+sz*1.77), 0.035, 0.10, col_env, hvac_mat, 20)

    # Overhead lamp poles closer to store, with arm and fixture head.
    pole_mat = mat_principled("V2B_MAT_LampPole", (0.045,0.045,0.045), 0.35, 0.7)
    for i, x in enumerate([-sx*1.35, sx*1.35]):
        pole_z = zmin+sz*0.95
        add_cyl(f"V2B_LampPole_{i}", (x,3.18,pole_z), 0.035, sz*1.82, col_env, pole_mat, 24)
        arm = add_cyl(f"V2B_LampArm_{i}", (x,3.00,zmin+sz*1.84), 0.025, 0.36, col_env, pole_mat, 16, rotation=(math.pi/2,0,0))
        head = add_cube(f"V2B_LampFixture_{i}", (x,2.78,zmin+sz*1.84), (0.20,0.10,0.045), col_env, pole_mat, 0.015)
        data = bpy.data.lights.new(f"V2B_OverheadAmber_{i}_Data", "AREA")
        data.energy = 520 if i == 0 else 260
        data.color = (1.0,0.37,0.055)
        data.shape = "DISK"
        data.size = 1.85
        light = bpy.data.objects.new(f"V2B_OverheadAmber_{i}", data)
        light.location = (x,2.78,zmin+sz*1.76)
        light.rotation_euler = (0,0,0)
        col_lights.objects.link(light)

def make_drift_car(col_car, col_lights, b):
    sx, sy, sz = dims(b)
    zmin = b[4]
    # Scaled for the large Sackboy: car sits well behind/left and is large enough.
    car_x = -sx*1.65
    car_y = 2.20
    car_z = zmin+0.18
    car_len = sx*1.55
    car_width = sx*0.72
    car_height = sz*0.30

    body = mat_principled("V2B_MAT_ChameleonBlackCar", (0.004,0.006,0.010), 0.16, 0.88, 1.0)
    glass = mat_principled("V2B_MAT_CarBlackGlass", (0.001,0.003,0.006), 0.08, 0.25)
    tire = mat_principled("V2B_MAT_Tire", (0.002,0.002,0.002), 0.87, 0)
    rim = mat_principled("V2B_MAT_BlackIridescentRims", (0.006,0.007,0.011), 0.21, 0.9, 1)
    cyan = mat_emission("V2B_MAT_CyanUnderglow", (0.0,0.55,1.0), 1.8)
    red = mat_emission("V2B_MAT_ModernRedTail", (1.0,0.02,0.0), 3.2)

    add_cube("V2B_DriftCar_LowCoupeBody", (car_x,car_y,car_z+car_height*0.48), (car_len*0.50,car_width*0.50,car_height*0.18), col_car, body, 0.11)
    add_cube("V2B_DriftCar_LongHood", (car_x,car_y-car_width*0.46,car_z+car_height*0.56), (car_len*0.38,car_width*0.24,car_height*0.09), col_car, body, 0.09)
    add_cube("V2B_DriftCar_RearDeck", (car_x,car_y+car_width*0.43,car_z+car_height*0.55), (car_len*0.34,car_width*0.20,car_height*0.08), col_car, body, 0.08)
    add_cube("V2B_DriftCar_SlopedCabin", (car_x,car_y+car_width*0.03,car_z+car_height*0.83), (car_len*0.28,car_width*0.30,car_height*0.16), col_car, glass, 0.08)
    add_cube("V2B_DriftCar_FrontBumper", (car_x,car_y-car_width*0.72,car_z+car_height*0.34), (car_len*0.50,car_width*0.045,car_height*0.08), col_car, body, 0.04)
    add_cube("V2B_DriftCar_RearSpoiler", (car_x,car_y+car_width*0.76,car_z+car_height*0.86), (car_len*0.34,0.035,0.035), col_car, body, 0.02)
    add_cube("V2B_DriftCar_UnderglowPanel", (car_x,car_y,car_z+0.06), (car_len*0.42,car_width*0.38,0.009), col_car, cyan, 0.02)

    data = bpy.data.lights.new("V2B_CarUnderglow_Data", "AREA")
    data.energy = 160
    data.color = (0.0,0.55,1.0)
    data.shape = "RECTANGLE"
    data.size = 2.0
    under = bpy.data.objects.new("V2B_CarUnderglow", data)
    under.location = (car_x,car_y,car_z+0.04)
    col_lights.objects.link(under)

    for side in [-1,1]:
        for foreaft in [-1,1]:
            x = car_x + side*car_len*0.36
            y = car_y + foreaft*car_width*0.42
            add_torus(f"V2B_DriftCar_Tire_{side}_{foreaft}", (x,y,car_z+car_height*0.26), col_car, tire, major=car_len*0.055, minor=car_len*0.018, rotation=(math.pi/2,0,0))
            add_torus(f"V2B_DriftCar_Rim_{side}_{foreaft}", (x,y,car_z+car_height*0.26), col_car, rim, major=car_len*0.033, minor=car_len*0.0045, rotation=(math.pi/2,0,0))
            for k in range(8):
                angle = math.tau*k/8
                dx = math.cos(angle)*car_len*0.030
                dz = math.sin(angle)*car_len*0.030
                add_curve(f"V2B_RimSpoke_{side}_{foreaft}_{k}", [(x,y,car_z+car_height*0.26), (x+dx,y,car_z+car_height*0.26+dz)], col_car, rim, bevel=0.0035)

    for side in [-1,1]:
        add_cube(f"V2B_DriftCar_TailLightModern_{side}", (car_x+side*car_len*0.24, car_y+car_width*0.71, car_z+car_height*0.50), (car_len*0.075,0.018,car_height*0.035), col_car, red, 0.012)
        d = bpy.data.lights.new(f"V2B_TailLightGlow_{side}_Data","POINT")
        d.energy = 70
        d.color = (1,0.02,0)
        o = bpy.data.objects.new(f"V2B_TailLightGlow_{side}", d)
        o.location = (car_x+side*car_len*0.24, car_y+car_width*0.78, car_z+car_height*0.50)
        col_lights.objects.link(o)

def make_cameras(col_cam, b):
    sx, sy, sz = dims(b)
    zmin = b[4]
    aim = Vector((0,0,zmin+sz*0.60))
    specs = [
        ("V2B_CAM_HERO", (sx*2.5,-sz*2.65,zmin+sz*0.95), aim, 48),
        ("V2B_CAM_HIGH_ORBIT", (sx*2.7,-sz*2.25,zmin+sz*1.55), aim, 45),
        ("V2B_CAM_LOW", (sx*1.75,-sz*1.90,zmin+sz*0.22), Vector((0,0,zmin+sz*0.58)), 38),
    ]
    cams={}
    for name, loc, target, lens in specs:
        data = bpy.data.cameras.new(name+"_Data")
        cam = bpy.data.objects.new(name, data)
        cam.location = loc
        cam.data.lens = lens
        look_at(cam, target)
        col_cam.objects.link(cam)
        cams[name] = cam
    rig = bpy.data.objects.new("V2B_ORBIT_RIG", None)
    rig.location = aim
    col_cam.objects.link(rig)
    cams["V2B_CAM_HIGH_ORBIT"].parent = rig
    rig.rotation_euler = (0,0,-0.35)
    rig.keyframe_insert(data_path="rotation_euler", frame=1)
    rig.rotation_euler = (0,0,0.95)
    rig.keyframe_insert(data_path="rotation_euler", frame=120)
    return cams

def render_previews(cams):
    scene = bpy.context.scene
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for cam_name, fn in [
        ("V2B_CAM_HERO", "01_Hero_F2_DarkLot.png"),
        ("V2B_CAM_HIGH_ORBIT", "02_HighOrbit_Roof_Lot.png"),
        ("V2B_CAM_LOW", "03_LowAngle_F2_Storefront.png"),
    ]:
        scene.camera = cams[cam_name]
        scene.render.filepath = str(OUT_DIR / fn)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {fn}")

def write_status():
    status = {
        "clean_puppet": "REJECTED/REMOVED - user prefers Meshy/manual F2",
        "full_source": "F2",
        "hand_reference": "HANDREFINE_J2B retained hidden, not modified",
        "lighting": "two overhead amber pole fixtures + car lights; no side diagnostic lights",
        "sky": "dark blue-black world + moon/cloud/star geometry",
        "environment": "larger strip mall, sidewalk, curb, parking lines, roof/parapet/HVAC/signs/window frames",
        "car": "larger drift-coupe placeholder with cyan underglow, modern red tails, black iridescent material, rim spokes",
        "cameras": "3 cameras only plus orbit rig",
        "next": "If approved, refine car and strip-mall details; if not, inspect manifest and adjust dimensions."
    }
    (OUT_DIR / "ProductionReconV2B_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

def write_manifest():
    if export_scene_manifest:
        export_scene_manifest(project_root() / "scene_manifest.json")
        export_scene_manifest(OUT_DIR / "scene_manifest.json")
    else:
        (OUT_DIR / "scene_manifest_note.txt").write_text("export_scene_manifest unavailable", encoding="utf-8")

def main():
    reset_report()
    setup_world()
    cleanup_bad_preview()

    root = replace_collection(ROOT)
    col_env = replace_collection(COL_ENV, root)
    col_car = replace_collection(COL_CAR, root)
    col_lights = replace_collection(COL_LIGHTS, root)
    col_cam = replace_collection(COL_CAM, root)
    col_sky = replace_collection(COL_SKY, root)
    col_helpers = replace_collection(COL_HELPERS, root)

    f2 = bpy.data.objects.get(FULL_SOURCE)
    if not f2 or f2.type != "MESH":
        raise RuntimeError("F2 full character source was not found.")
    force_visible(f2)
    b = world_bounds(f2)
    log(f"[audit] F2 bounds={b} dims={dims(b)}")

    hand = bpy.data.objects.get(HAND_REF)
    if hand:
        hand.hide_viewport = True
        hand.hide_render = True
        log("[audit] J2B hand reference retained hidden")

    make_sky(col_sky, b)
    make_environment(col_env, col_lights, b)
    make_drift_car(col_car, col_lights, b)
    cams = make_cameras(col_cam, b)

    render_previews(cams)
    write_status()
    write_manifest()

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUT_DIR / "ProductionReconV2B_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
