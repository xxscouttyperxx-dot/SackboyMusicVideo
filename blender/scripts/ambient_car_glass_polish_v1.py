import sys, json, math, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root

OUT_DIR = project_root() / "renders" / "ambient_car_glass_polish_v1"
AUDI_COLLECTION = "Audi e-tron GT quattro Black"
STORE_COLLECTION = "HERO_STOREFRONT_REBUILD"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "AmbientCarGlassPolish_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "AmbientCarGlassPolish_report.txt").write_text("", encoding="utf-8")

def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = False
    col.hide_render = False
    return col

def remove_obj(obj):
    try:
        bpy.data.objects.remove(obj, do_unlink=True)
    except Exception:
        pass

def remove_collection_recursive(col):
    for child in list(col.children):
        remove_collection_recursive(child)
    for obj in list(col.objects):
        remove_obj(obj)
    bpy.data.collections.remove(col)

def replace_collection(name):
    old = bpy.data.collections.get(name)
    if old:
        remove_collection_recursive(old)
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    col.hide_viewport = False
    col.hide_render = False
    return col

def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        try:
            c.objects.unlink(obj)
        except Exception:
            pass
    col.objects.link(obj)

def world_bounds(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    except Exception:
        return None

def union_bounds(objects):
    boxes=[]
    for obj in objects:
        if obj.type == "MESH":
            b = world_bounds(obj)
            if b:
                boxes.append(b)
    if not boxes:
        return None
    return (
        min(b[0] for b in boxes), max(b[1] for b in boxes),
        min(b[2] for b in boxes), max(b[3] for b in boxes),
        min(b[4] for b in boxes), max(b[5] for b in boxes),
    )

def dims(b):
    return b[1]-b[0], b[3]-b[2], b[5]-b[4]

def center(b):
    return Vector(((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2))

def mat_principled(name, color, roughness=0.3, metallic=0.0, alpha=1.0, specular=0.7):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = specular
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.12
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if alpha < 1.0:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
        mat.show_transparent_back = True
    return mat

def mat_emission(name, color, strength=1.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, alpha)
    em.inputs["Strength"].default_value = strength
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    if alpha < 1.0:
        mat.blend_method = "BLEND"
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
        be.segments = 2
        obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
    return obj

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def get_f2_bounds():
    f2 = bpy.data.objects.get("F2")
    if not f2:
        return None
    f2.hide_viewport = False
    f2.hide_render = False
    for c in f2.users_collection:
        c.hide_viewport = False
        c.hide_render = False
    return world_bounds(f2)

def get_audi_objects_and_bounds():
    objs=[]
    col = bpy.data.collections.get(AUDI_COLLECTION)
    if col:
        col.hide_viewport = False
        col.hide_render = False
        objs.extend(list(col.objects))
    root_empty = bpy.data.objects.get(AUDI_COLLECTION)
    if root_empty:
        root_empty.hide_viewport = False
        root_empty.hide_render = False
        objs.append(root_empty)
        objs.extend(list(root_empty.children_recursive))
    for o in objs:
        o.hide_viewport = False
        o.hide_render = False
    b = union_bounds(objs)
    if not b:
        raise RuntimeError("Could not find hero Audi bounds.")
    return objs, b

def remove_only_scripted_sky_backdrop():
    # User fixed the sky manually; do not touch World settings.
    col = bpy.data.collections.get("HERO_SKY_BACKDROP")
    if col:
        remove_collection_recursive(col)
        log("[sky] removed scripted Hollywood-set sky backdrop; preserved user World/HDRI")
    for obj in list(bpy.data.objects):
        if obj.name.startswith("HERO_NightSky_Backdrop"):
            remove_obj(obj)

def add_car_amber_read(audi_bounds):
    # Add subtle warm helper lights whose only job is to make overhead amber read on the car.
    # Existing lamp positions and user manual edits are preserved.
    col = replace_collection("HERO_CAR_AMBER_READ")
    c = center(audi_bounds)
    xdim, ydim, zdim = dims(audi_bounds)

    specs = [
        ("HERO_CarAmberRoofRead", (c.x - xdim*0.10, c.y - ydim*0.10, audi_bounds[5] + zdim*0.95), c, 260, 1.05, 0.72),
        ("HERO_CarAmberHoodRead", (c.x + xdim*0.15, audi_bounds[2] - ydim*0.12, audi_bounds[5] + zdim*0.70), Vector((c.x, audi_bounds[2] + ydim*0.22, audi_bounds[4]+zdim*0.55)), 150, 0.95, 0.65),
        ("HERO_CarWarmSideGlint", (audi_bounds[0] - xdim*0.20, c.y, audi_bounds[4] + zdim*0.75), Vector((c.x, c.y, audi_bounds[4]+zdim*0.55)), 90, 0.85, 0.80),
    ]

    for name, loc, target, energy, spot_size, blend in specs:
        data = bpy.data.lights.new(name + "_Data", "SPOT")
        data.energy = energy
        data.color = (1.0, 0.38, 0.08)
        data.spot_size = spot_size
        data.spot_blend = blend
        data.shadow_soft_size = 1.25
        light = bpy.data.objects.new(name, data)
        light.location = loc
        look_at(light, target)
        col.objects.link(light)

    # Add subtle amber reflection cards above the car. They are small and dim so they read as glossy highlights, not new set pieces.
    card_mat = mat_emission("HERO_MAT_SubtleAmberCarReflection", (1.0, 0.33, 0.045), 0.18, 0.60)
    add_cube("HERO_CarAmberReflectionCard_Roof", (c.x, c.y-y_dim_safe(ydim,0.12), audi_bounds[5]+0.045), (xdim*0.26, 0.010, 0.010), col, card_mat, 0.002)
    add_cube("HERO_CarAmberReflectionCard_Hood", (c.x+xdim*0.05, audi_bounds[2]+ydim*0.22, audi_bounds[4]+zdim*0.64), (xdim*0.24, 0.010, 0.008), col, card_mat, 0.002)
    log("[car] added subtle amber read/helper lights and reflection cards for car roof/hood/body")

def y_dim_safe(ydim, factor):
    return ydim * factor

def polish_storefront_glass():
    col = replace_collection("HERO_WINDOW_TRAFFIC_REFLECTIONS")
    glass_mat = mat_principled("HERO_MAT_Glass_NightGlossy", (0.004, 0.010, 0.018), roughness=0.09, metallic=0.0, alpha=0.78, specular=0.95)
    frame_count = 0

    glass_objects = []
    for obj in bpy.data.objects:
        if obj.name.startswith("HERO_GlassStorefront_Bay_") and obj.type == "MESH":
            assign_mat(obj, glass_mat)
            glass_objects.append(obj)

    # emissive reflection streaks layered on front of glass, biased toward night traffic/street colors.
    amber = mat_emission("HERO_MAT_WindowReflection_Amber", (1.0, 0.46, 0.08), 0.23, 0.75)
    white = mat_emission("HERO_MAT_WindowReflection_White", (0.80, 0.86, 1.0), 0.14, 0.65)
    red = mat_emission("HERO_MAT_WindowReflection_Red", (1.0, 0.04, 0.015), 0.18, 0.65)
    blue = mat_emission("HERO_MAT_WindowReflection_Blue", (0.05, 0.28, 1.0), 0.10, 0.55)

    for idx, obj in enumerate(glass_objects):
        b = world_bounds(obj)
        if not b:
            continue
        xdim, ydim, zdim = dims(b)
        cx = (b[0]+b[1])/2
        y_front = b[2] - 0.010
        z_mid = (b[4]+b[5])/2

        add_cube(f"HERO_WindowTrafficAmberStreak_{idx}", (cx-xdim*0.10, y_front, z_mid+zdim*0.24), (xdim*0.34, 0.003, 0.012), col, amber, 0.002)
        add_cube(f"HERO_WindowTrafficWhiteStreak_{idx}", (cx+xdim*0.12, y_front, z_mid+zdim*0.06), (xdim*0.25, 0.003, 0.009), col, white, 0.002)
        add_cube(f"HERO_WindowTrafficRedStreak_{idx}", (cx-xdim*0.24, y_front, z_mid-zdim*0.18), (xdim*0.18, 0.003, 0.008), col, red, 0.002)
        if idx % 2 == 0:
            add_cube(f"HERO_WindowTrafficBlueStreak_{idx}", (cx+xdim*0.28, y_front, z_mid-zdim*0.03), (xdim*0.12, 0.003, 0.008), col, blue, 0.002)
        frame_count += 1

    log(f"[glass] polished {len(glass_objects)} glass bays and added night traffic reflection streaks to {frame_count} bays")

def render_review(f2_bounds, audi_bounds):
    col = replace_collection("HERO_REVIEW_CAMERAS")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    try:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "Medium High Contrast"
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
    except Exception:
        pass

    f2c = center(f2_bounds) if f2_bounds else Vector((0,0,1.2))
    car = center(audi_bounds)
    sx, sy, sz = dims(f2_bounds) if f2_bounds else (3.0,1.5,2.8)

    specs = [
        ("HERO_CAM_CarAmberRead", (car.x + 4.8, car.y - 6.2, car.z + 2.4), Vector((car.x, car.y, car.z + 0.75)), 44, "01_CarAmberRead.png"),
        ("HERO_CAM_WindowReflectionPolish", (2.5, 16.0, 2.6), Vector((0, 23.85, 2.1)), 50, "02_WindowReflectionPolish.png"),
        ("HERO_CAM_StableSceneMood", (f2c.x + 8.0, f2c.y - 9.0, f2c.z + 3.6), Vector((0, 8.0, 1.5)), 42, "03_StableSceneMood.png"),
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, loc, aim, lens, filename in specs:
        data = bpy.data.cameras.new(name + "_Data")
        cam = bpy.data.objects.new(name, data)
        cam.location = loc
        cam.data.lens = lens
        look_at(cam, aim)
        col.objects.link(cam)
        scene.camera = cam
        scene.render.filepath = str(OUT_DIR / filename)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {filename}")

    current = project_root() / "renders" / "current_review"
    current.mkdir(parents=True, exist_ok=True)
    for p in current.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (current / p.name).write_bytes(p.read_bytes())

def write_status(audi_bounds):
    status = {
        "manual_edits": "Preserved current user-adjusted lamp post and sidewalk/storefront positions; no rebuild of layout geometry.",
        "sky": "User World/HDRI preserved; scripted backdrop removed if present.",
        "car_lighting": "Added subtle amber helper spots and reflection cards aimed at hero car roof/hood/body.",
        "glass": "Replaced glass material with darker glossier night glass and added traffic/street reflection streaks.",
        "audi_bounds": {
            "xmin": audi_bounds[0], "xmax": audi_bounds[1],
            "ymin": audi_bounds[2], "ymax": audi_bounds[3],
            "zmin": audi_bounds[4], "zmax": audi_bounds[5],
        },
    }
    (OUT_DIR / "AmbientCarGlassPolish_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

def export_manifest():
    script = project_root() / "blender" / "scripts" / "export_project_layout_and_scene.py"
    if script.exists():
        ns = {"__file__": str(script), "__name__": "__main__"}
        exec(script.read_text(encoding="utf-8"), ns)

def main():
    reset_log()
    remove_only_scripted_sky_backdrop()
    f2_bounds = get_f2_bounds()
    audi_objects, audi_bounds = get_audi_objects_and_bounds()
    add_car_amber_read(audi_bounds)
    polish_storefront_glass()
    render_review(f2_bounds, audi_bounds)
    write_status(audi_bounds)
    export_manifest()
    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUT_DIR / "AmbientCarGlassPolish_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
