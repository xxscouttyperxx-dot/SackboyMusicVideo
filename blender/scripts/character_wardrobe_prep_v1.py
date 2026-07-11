import sys, json, math, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root

OUT_DIR = project_root() / "renders" / "character_wardrobe_prep_v1"
WARDROBE_COL = "HERO_CHARACTER_WARDROBE_V1"
MATERIAL_COL = "HERO_CHARACTER_MATERIAL_GUIDES"
CAM_COL = "HERO_REVIEW_CAMERAS"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "CharacterWardrobePrep_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "CharacterWardrobePrep_report.txt").write_text("", encoding="utf-8")

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

def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
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
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    except Exception:
        return None

def dims(b):
    return b[1]-b[0], b[3]-b[2], b[5]-b[4]

def center(b):
    return Vector(((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2))

def mat_principled(name, color, roughness=0.5, metallic=0.0, alpha=1.0, specular=0.5):
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
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if alpha < 1.0:
        mat.blend_method = "BLEND"
    return mat

def mat_emission(name, color, strength=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat

def mat_yarn(name="HERO_MAT_SackboyYarn_Procedural"):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    wave_bands = nodes.new("ShaderNodeTexWave")
    wave_rings = nodes.new("ShaderNodeTexWave")
    noise = nodes.new("ShaderNodeTexNoise")
    add = nodes.new("ShaderNodeMath")
    mult = nodes.new("ShaderNodeMath")
    bump = nodes.new("ShaderNodeBump")

    bsdf.inputs["Base Color"].default_value = (0.255, 0.125, 0.055, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.88

    mapping.inputs["Scale"].default_value = (12.0, 14.0, 30.0)
    wave_bands.wave_type = "BANDS"
    wave_bands.bands_direction = "Z"
    wave_bands.inputs["Scale"].default_value = 42.0
    wave_bands.inputs["Distortion"].default_value = 8.0

    wave_rings.wave_type = "RINGS"
    wave_rings.inputs["Scale"].default_value = 22.0
    wave_rings.inputs["Distortion"].default_value = 12.0

    noise.inputs["Scale"].default_value = 55.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.62

    add.operation = "ADD"
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = 0.45
    bump.inputs["Strength"].default_value = 0.23
    bump.inputs["Distance"].default_value = 0.018

    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave_bands.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave_rings.inputs["Vector"])
    links.new(wave_bands.outputs["Color"], add.inputs[0])
    links.new(wave_rings.outputs["Color"], add.inputs[1])
    links.new(add.outputs[0], mult.inputs[0])
    links.new(mult.outputs[0], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
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
        be.segments = 5
        obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
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

def add_cyl(name, loc, radius, depth, col, mat=None, vertices=32, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, col)
    if mat:
        assign_mat(obj, mat)
    return obj

def add_curve(name, points, col, mat, bevel=0.006):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    sp = curve.splines.new("POLY")
    sp.points.add(len(points)-1)
    for p, co in zip(sp.points, points):
        p.co = (co[0], co[1], co[2], 1)
    obj = bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def get_f2():
    f2 = bpy.data.objects.get("F2")
    if not f2:
        raise RuntimeError("F2 source object was not found.")
    f2.hide_viewport = False
    f2.hide_render = False
    for c in f2.users_collection:
        c.hide_viewport = False
        c.hide_render = False
    return f2, world_bounds(f2)

def preserve_locked_scene():
    # Do not touch lighting collections, world, car, storefront, sidewalk, parking, or user-managed sky.
    locked = [
        "V2B_LIGHTS_OVERHEAD",
        "HERO_CAR_AMBER_READ",
        "HERO_VISIBLE_LAMPPOSTS",
        "Audi e-tron GT quattro Black",
        "HERO_STOREFRONT_REBUILD",
        "HERO_SIDEWALK_CURB_REBUILD",
        "HERO_H_PARKING_LAYOUT",
        "HERO_CAR_UNDERGLOW",
    ]
    for name in locked:
        col = bpy.data.collections.get(name)
        if col:
            col.hide_viewport = False
            col.hide_render = False
    log("[lock] scene layout, car, sky/world, and lighting preserved; no light edits made")

def apply_yarn_material(f2):
    yarn = mat_yarn()
    # Apply to F2 only. No geometry changes.
    if hasattr(f2.data, "materials"):
        if not f2.data.materials:
            f2.data.materials.append(yarn)
        else:
            f2.data.materials[0] = yarn
    log("[character] applied procedural yarn material to F2 material slot 0")

def build_wardrobe_guides(f2_bounds):
    col = replace_collection(WARDROBE_COL)
    guides = ensure_collection(MATERIAL_COL)
    sx, sy, sz = dims(f2_bounds)
    c = center(f2_bounds)
    zmin = f2_bounds[4]

    hoodie = mat_principled("HERO_MAT_BlackHoodie_Cloth", (0.006, 0.006, 0.007), 0.82, 0.0, 0.72, 0.35)
    denim = mat_principled("HERO_MAT_BaggyDenim_DarkBlue", (0.030, 0.080, 0.155), 0.78, 0.0, 0.72, 0.25)
    shoe_black = mat_principled("HERO_MAT_BlackSkateShoe", (0.004, 0.004, 0.005), 0.42, 0.0, 1.0, 0.55)
    shoe_white = mat_principled("HERO_MAT_SkateShoeWhitePanels", (0.82, 0.82, 0.78), 0.48, 0.0, 1.0, 0.45)
    flame_orange = mat_principled("HERO_MAT_ShoeFlameOrangeYellow", (1.0, 0.26, 0.015), 0.50, 0.0, 1.0, 0.55)
    seam = mat_principled("HERO_MAT_ClothingSeams", (0.015, 0.015, 0.018), 0.88, 0.0)

    # Semi-transparent wardrobe fit guides so they do not destroy the current character read.
    torso_z = zmin + sz * 0.43
    head_z = zmin + sz * 0.73
    add_uv("HERO_Hoodie_Torso_FitGuide", (c.x, c.y, torso_z), (sx*0.27, sy*0.43, sz*0.18), col, hoodie, 48, 20)
    add_uv("HERO_Hoodie_Hood_FitGuide", (c.x, c.y-0.025, head_z), (sx*0.42, sy*0.46, sz*0.24), col, hoodie, 48, 20)

    # Sleeves around current arms, conservative and symmetrical.
    for side, label in [(-1, "L"), (1, "R")]:
        add_cyl(f"HERO_Hoodie_Sleeve_{label}_FitGuide", (c.x + side*sx*0.42, c.y, zmin + sz*0.47), sx*0.070, sx*0.40, col, hoodie, 32, rotation=(0, math.pi/2, 0))
        add_uv(f"HERO_BaggyJean_Leg_{label}_FitGuide", (c.x + side*sx*0.12, c.y, zmin + sz*0.18), (sx*0.12, sy*0.19, sz*0.17), col, denim, 36, 16)

        # Shoes are intentionally chunky black skate shoes with white toe/sole + flame/color accents.
        shoe_x = c.x + side*sx*0.13
        shoe_y = c.y - sy*0.07
        shoe_z = zmin + sz*0.035
        add_uv(f"HERO_BlackSkateShoe_{label}_Main", (shoe_x, shoe_y, shoe_z), (sx*0.17, sy*0.28, sz*0.055), col, shoe_black, 48, 16)
        add_uv(f"HERO_BlackSkateShoe_{label}_WhiteToe", (shoe_x, shoe_y - sy*0.19, shoe_z + sz*0.010), (sx*0.09, sy*0.060, sz*0.027), col, shoe_white, 32, 12)
        add_cube(f"HERO_BlackSkateShoe_{label}_WhiteSole", (shoe_x, shoe_y, shoe_z - sz*0.028), (sx*0.18, sy*0.29, sz*0.018), col, shoe_white, 0.012)

        # Side flame/graphic accents on outer side. Subtle, not copied from reference.
        outer_x = shoe_x + side*sx*0.14
        for k in range(3):
            add_cube(f"HERO_BlackSkateShoe_{label}_FlameAccent_{k}", (outer_x, shoe_y - sy*(0.03 + 0.035*k), shoe_z + sz*(0.005 + 0.014*k)), (sx*0.014, sy*0.030, sz*0.018), col, flame_orange, 0.006)

        # Simple lace guide lines.
        for k in range(4):
            y = shoe_y - sy*(0.05 + 0.035*k)
            add_curve(f"HERO_BlackSkateShoe_{label}_Lace_{k}", [(shoe_x-sx*0.055, y, shoe_z+sz*0.050), (shoe_x+sx*0.055, y+sy*0.012, shoe_z+sz*0.050)], col, shoe_white, 0.004)

    # Hoodie seam/zipper guide.
    add_curve("HERO_Hoodie_CenterZip_Guide", [(c.x, c.y-sy*0.41, zmin+sz*0.28), (c.x, c.y-sy*0.43, zmin+sz*0.61)], col, seam, 0.006)
    add_curve("HERO_Hoodie_Hem_Guide", [(c.x-sx*0.22, c.y-sy*0.42, zmin+sz*0.27), (c.x+sx*0.22, c.y-sy*0.42, zmin+sz*0.27)], col, seam, 0.006)

    # Material swatches off to the side for inspection.
    base_x = f2_bounds[1] + sx*0.35
    for i, (name, mat) in enumerate([
        ("Yarn", mat_yarn()),
        ("Hoodie", hoodie),
        ("Denim", denim),
        ("ShoeBlack", shoe_black),
        ("ShoeWhite", shoe_white),
        ("Flame", flame_orange),
    ]):
        add_cube(f"HERO_MaterialSwatch_{name}", (base_x, c.y + i*0.18, zmin+sz*0.12), (0.055,0.055,0.055), guides, mat, 0.006)

    log("[wardrobe] created non-destructive hoodie/jeans/black-skate-shoe fit guides and material swatches")

def render_review(f2_bounds):
    col = replace_collection(CAM_COL)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    c = center(f2_bounds)
    sx, sy, sz = dims(f2_bounds)

    specs = [
        ("HERO_CAM_CharacterWardrobeFront", (c.x+sx*1.45, c.y-sz*2.20, c.z+sz*0.45), Vector((c.x, c.y, c.z+sz*0.10)), 70, "01_CharacterWardrobeFront.png"),
        ("HERO_CAM_ShoeCloseup", (c.x+sx*0.85, c.y-sz*1.10, f2_bounds[4]+sz*0.25), Vector((c.x, c.y, f2_bounds[4]+sz*0.09)), 75, "02_ShoeCloseup.png"),
        ("HERO_CAM_WardrobeSceneContext", (c.x+8.0, c.y-9.0, c.z+3.6), Vector((0, 8.0, 1.5)), 42, "03_WardrobeSceneContext.png"),
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

def write_status():
    status = {
        "locked_scene": "Lighting, car, world/HDRI, storefront, sidewalk, and parking layout preserved.",
        "character": "F2 geometry preserved; procedural yarn material assigned to material slot 0.",
        "wardrobe": "Non-destructive fit-guide collection created for hoodie, jeans, black skate shoes, laces, white sole/toe, and flame accents.",
        "lights": "No lights added, removed, moved, or edited.",
        "hand": "No hand geometry edited.",
    }
    (OUT_DIR / "CharacterWardrobePrep_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

def export_manifest():
    script = project_root() / "blender" / "scripts" / "export_project_layout_and_scene.py"
    if script.exists():
        ns = {"__file__": str(script), "__name__": "__main__"}
        exec(script.read_text(encoding="utf-8"), ns)

def main():
    reset_log()
    preserve_locked_scene()
    f2, f2_bounds = get_f2()
    apply_yarn_material(f2)
    build_wardrobe_guides(f2_bounds)
    render_review(f2_bounds)
    write_status()
    export_manifest()
    out = project_root() / "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUT_DIR / "CharacterWardrobePrep_FATAL_ERROR.txt").open("w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
