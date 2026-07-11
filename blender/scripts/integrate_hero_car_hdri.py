import sys, math, json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root
try:
    from export_project_layout_and_scene import main as export_layout_main
except Exception:
    export_layout_main = None

OUT_DIR = project_root() / "renders" / "hero_car_hdri_integration"
HDRI_PATH = project_root() / "NightSkyHDRI003_1K" / "NightSkyHDRI003_1K_HDR.exr"
AUDI_COLLECTION = "Audi e-tron GT quattro Black"
AUDI_EMPTY = "Audi e-tron GT quattro Black"
OVERHEAD_LIGHT_COLLECTION = "V2B_LIGHTS_OVERHEAD"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "HeroCarHDRI_build_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "HeroCarHDRI_build_report.txt").write_text("", encoding="utf-8")

def world_bounds_object(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    except Exception:
        return None

def union_bounds(objects):
    boxes = []
    for obj in objects:
        if obj.type == "MESH":
            b = world_bounds_object(obj)
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

def remove_collection_recursive(col):
    for child in list(col.children):
        remove_collection_recursive(child)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def remove_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        log(f"[cleanup] removing collection {name}")
        remove_collection_recursive(col)

def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        try:
            c.objects.unlink(obj)
        except Exception:
            pass
    col.objects.link(obj)

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

def mat_principled(name, color, roughness=0.6, metallic=0.0, alpha=1.0):
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
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if alpha < 1.0:
        mat.blend_method = "BLEND"
    return mat

def add_cube(name, loc, scale, col, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, col)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    if bevel > 0:
        be = obj.modifiers.new("Bevel", "BEVEL")
        be.width = bevel
        be.segments = 3
        obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
    return obj

def remove_old_scripted_cars():
    # Remove generated/scripted car collections and object families.
    for name in ["V2C_DRIFT_CAR", "V2B_DRIFT_CAR", "PRV2_DRIFT_CAR"]:
        remove_collection(name)
    prefixes = (
        "V2C_Drift", "V2C_Tire", "V2C_Rim", "V2C_Underglow", "V2C_CyanUnderglow",
        "V2C_Tail", "V2C_ExhaustSmoke", "V2B_Drift", "PRV2_Drift", "PRV2_Car"
    )
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass
    log("[cleanup] old scripted car objects removed")

def get_audi_objects():
    col = bpy.data.collections.get(AUDI_COLLECTION)
    if col:
        objs = list(col.objects)
    else:
        empty = bpy.data.objects.get(AUDI_EMPTY)
        objs = []
        if empty:
            objs.append(empty)
            objs.extend(list(empty.children_recursive))
    if not objs:
        raise RuntimeError("Hero Audi collection/object not found. Expected collection/object named 'Audi e-tron GT quattro Black'.")
    for obj in objs:
        obj.hide_viewport = False
        obj.hide_render = False
    if col:
        col.hide_viewport = False
        col.hide_render = False
    return objs

def setup_hdri_world():
    if not HDRI_PATH.exists():
        log(f"[hdri] WARNING missing EXR: {HDRI_PATH}")
        return False
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("NightSkyHDRI003_World")
    world = scene.world
    world.name = "NightSkyHDRI003_World"
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(HDRI_PATH), check_existing=True)
    bg.inputs["Strength"].default_value = 0.08
    links.new(env.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])
    log(f"[hdri] world environment set to {HDRI_PATH}")
    return True

def preserve_overhead_lights():
    col = bpy.data.collections.get(OVERHEAD_LIGHT_COLLECTION)
    if not col:
        log("[lighting] WARNING V2B_LIGHTS_OVERHEAD not found; no changes made")
        return []
    col.hide_viewport = False
    col.hide_render = False
    lights = []
    for obj in col.objects:
        if obj.type == "LIGHT" and obj.name.startswith("V2B_OverheadAmber"):
            obj.hide_viewport = False
            obj.hide_render = False
            lights.append(obj)
    log(f"[lighting] preserved {len(lights)} overhead amber lights unchanged")
    return lights

def add_hero_car_underglow(audi_bounds):
    col = ensure_collection("HERO_CAR_UNDERGLOW")
    # clear prior underglow-only helpers
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    xdim, ydim, zdim = dims(audi_bounds)
    c = center(audi_bounds)
    z = audi_bounds[4] + max(0.035, zdim * 0.025)
    mat = mat_emission("HERO_MAT_CyanUnderglow", (0.0, 0.55, 1.0), 1.8)
    # hidden strips, not giant visible panel
    add_cube("HERO_Underglow_FrontHiddenStrip", (c.x, c.y - ydim*0.22, z), (xdim*0.30, 0.025, 0.008), col, mat, 0.002)
    add_cube("HERO_Underglow_RearHiddenStrip", (c.x, c.y + ydim*0.22, z), (xdim*0.30, 0.025, 0.008), col, mat, 0.002)
    data = bpy.data.lights.new("HERO_CyanUnderglow_Area_Data", "AREA")
    data.energy = 160
    data.color = (0.0, 0.55, 1.0)
    data.shape = "RECTANGLE"
    data.size = max(1.0, min(xdim, ydim) * 0.75)
    light = bpy.data.objects.new("HERO_CyanUnderglow_Area", data)
    light.location = (c.x, c.y, z + 0.02)
    col.objects.link(light)
    log(f"[underglow] added under hero Audi at center={tuple(round(v,3) for v in c)}")
    return col

def adjust_strip_mall_and_parking():
    # Move storefront/sidewalk/roof farther back without touching character/car/lights.
    # Use conservative object-name targeting.
    move_keywords = [
        "StripMall", "Store", "GlassPanel", "GlassDoor", "Frame", "Sidewalk",
        "Curb", "Roof", "Parapet", "HVAC", "Vent"
    ]
    moved = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if obj.name.startswith("V2C_") and any(k in obj.name for k in move_keywords):
            obj.location.y += 8.0
            moved += 1
    log(f"[stripmall] moved {moved} strip mall/sidewalk/roof objects back +8.0 on Y")

    # Thicken and flatten parking lines.
    edited = 0
    for obj in bpy.data.objects:
        if obj.type == "MESH" and (obj.name.startswith("V2C_ParkingLine") or obj.name == "V2C_BackParkingLine"):
            # Dimensions are applied mesh dimensions; scale local object after apply is 1.
            # Scale around current origin to double width and make thinner vertically.
            obj.scale.x *= 2.0
            obj.scale.z *= 0.25
            edited += 1
    log(f"[parking] doubled width and flattened {edited} parking line objects")

def make_review_cameras(audi_bounds):
    # Keep cameras lean: remove V2C/old camera collection, create current review cameras.
    for name in ["HERO_REVIEW_CAMERAS"]:
        col_old = bpy.data.collections.get(name)
        if col_old:
            remove_collection_recursive(col_old)
    col = ensure_collection("HERO_REVIEW_CAMERAS")
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    f2 = bpy.data.objects.get("F2")
    if f2:
        fb = world_bounds_object(f2)
        target = center(fb)
    else:
        target = center(audi_bounds)
    # Aim between character and car for the first render.
    car_c = center(audi_bounds)
    mixed = Vector(((target.x*0.65 + car_c.x*0.35), (target.y*0.70 + car_c.y*0.30), target.z*0.75))
    xdim, ydim, zdim = dims(audi_bounds)

    specs = [
        ("HERO_CAM_CurrentReview", (target.x+7.5, target.y-8.0, target.z+2.6), mixed, 45),
        ("HERO_CAM_CarUnderglow", (car_c.x+4.0, car_c.y-5.2, car_c.z+1.2), Vector((car_c.x, car_c.y, car_c.z+0.55)), 42),
        ("HERO_CAM_HighLayout", (target.x+9.0, target.y-8.0, target.z+5.0), Vector((target.x, target.y+3.0, target.z+0.6)), 38),
    ]
    cams = {}
    for name, loc, aim, lens in specs:
        data = bpy.data.cameras.new(name + "_Data")
        cam = bpy.data.objects.new(name, data)
        cam.location = loc
        cam.data.lens = lens
        cam.rotation_euler = (Vector(aim) - cam.location).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(cam)
        cams[name] = cam
    return cams

def render_current_review(cams):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.frame_start = 1
    scene.frame_end = 120
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for cam_name, filename in [
        ("HERO_CAM_CurrentReview", "01_CurrentReview_Hero.png"),
        ("HERO_CAM_CarUnderglow", "02_CurrentReview_CarUnderglow.png"),
        ("HERO_CAM_HighLayout", "03_CurrentReview_HighLayout.png"),
    ]:
        scene.camera = cams[cam_name]
        scene.render.filepath = str(OUT_DIR / filename)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {filename}")

def write_status(audi_bounds):
    status = {
        "hero_car": "Preserved user-placed Audi e-tron GT quattro Black collection/object",
        "old_scripted_car": "Removed",
        "underglow": "Rebuilt under hero Audi using hidden strips + cyan area light",
        "hdri": str(HDRI_PATH),
        "overhead_lighting": "V2B overhead amber lights preserved unchanged",
        "strip_mall": "Existing V2C strip mall/sidewalk/roof/frame objects moved farther back +8 Y",
        "parking_lines": "V2C parking lines doubled in width and flattened vertically",
        "audi_bounds": {
            "xmin": audi_bounds[0], "xmax": audi_bounds[1],
            "ymin": audi_bounds[2], "ymax": audi_bounds[3],
            "zmin": audi_bounds[4], "zmax": audi_bounds[5],
        }
    }
    (OUT_DIR / "HeroCarHDRI_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

def export_manifest_if_available():
    # Reuse permanent audit script if present.
    script = project_root() / "blender" / "scripts" / "export_project_layout_and_scene.py"
    if script.exists():
        ns = {"__file__": str(script), "__name__": "__main__"}
        exec(script.read_text(encoding="utf-8"), ns)
    else:
        log("[manifest] audit script not found; skipping")

def main():
    reset_log()
    setup_hdri_world()
    preserve_overhead_lights()

    f2 = bpy.data.objects.get("F2")
    if f2:
        f2.hide_viewport = False
        f2.hide_render = False
        for c in f2.users_collection:
            c.hide_viewport = False
            c.hide_render = False

    hand = bpy.data.objects.get("HANDREFINE_J2B_Working")
    if hand:
        hand.hide_viewport = True
        hand.hide_render = True

    audi_objs = get_audi_objects()
    audi_bounds = union_bounds(audi_objs)
    if not audi_bounds:
        raise RuntimeError("Could not calculate hero Audi bounds.")
    log(f"[audi] bounds={audi_bounds} dims={dims(audi_bounds)}")

    remove_old_scripted_cars()
    add_hero_car_underglow(audi_bounds)
    adjust_strip_mall_and_parking()
    cams = make_review_cameras(audi_bounds)
    render_current_review(cams)
    write_status(audi_bounds)
    export_manifest_if_available()

    # Copy review renders into current_review for Git.
    current = project_root() / "renders" / "current_review"
    current.mkdir(parents=True, exist_ok=True)
    for old in current.glob("*"):
        if old.is_file():
            old.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (current / p.name).write_bytes(p.read_bytes())

    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUT_DIR / "HeroCarHDRI_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
