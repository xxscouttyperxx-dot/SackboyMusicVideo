import sys, math, json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root

OUT_DIR = project_root() / "renders" / "storefront_parking_v1c"
HDRI_DIR = project_root() / "NightSkyHDRI003_1K"
HDRI_EXR = HDRI_DIR / "NightSkyHDRI003_1K_HDR.exr"
HDRI_JPG = HDRI_DIR / "NightSkyHDRI003_1K_TONEMAPPED.jpg"
HDRI_PNG = HDRI_DIR / "NightSkyHDRI003.png"
HDRI_BLEND = HDRI_DIR / "NightSkyHDRI003_1K.blend"
HDRI_TRES = HDRI_DIR / "NightSkyHDRI003_1K.tres"
HDRI_USDC = HDRI_DIR / "NightSkyHDRI003_1K.usdc"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "StorefrontParkingV1C_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "StorefrontParkingV1C_report.txt").write_text("", encoding="utf-8")

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
        coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    except Exception:
        return None

def union_bounds(objects):
    boxes = []
    for obj in objects:
        if obj.type == "MESH":
            b = world_bounds(obj)
            if b:
                boxes.append(b)
    if not boxes:
        return None
    return (min(b[0] for b in boxes), max(b[1] for b in boxes),
            min(b[2] for b in boxes), max(b[3] for b in boxes),
            min(b[4] for b in boxes), max(b[5] for b in boxes))

def dims(b):
    return b[1]-b[0], b[3]-b[2], b[5]-b[4]

def center(b):
    return Vector(((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2))

def mat_principled(name, color, roughness=0.5, metallic=0.0, alpha=1.0):
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
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if alpha < 1:
        mat.blend_method = "BLEND"
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

def mat_image_emission(name, image_path, strength=0.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    l = mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    em = n.new("ShaderNodeEmission")
    tex = n.new("ShaderNodeTexImage")
    if image_path.exists():
        tex.image = bpy.data.images.load(str(image_path), check_existing=True)
    em.inputs["Strength"].default_value = strength
    l.new(tex.outputs["Color"], em.inputs["Color"])
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

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def get_f2_bounds():
    f2 = bpy.data.objects.get("F2")
    if not f2:
        raise RuntimeError("F2 not found.")
    f2.hide_viewport = False
    f2.hide_render = False
    for col in f2.users_collection:
        col.hide_viewport = False
        col.hide_render = False
    return world_bounds(f2)

def get_audi_bounds():
    col = bpy.data.collections.get("Audi e-tron GT quattro Black")
    objs = []
    if col:
        col.hide_viewport = False
        col.hide_render = False
        objs.extend(list(col.objects))
    empty = bpy.data.objects.get("Audi e-tron GT quattro Black")
    if empty:
        objs.append(empty)
        objs.extend(list(empty.children_recursive))
    return union_bounds(objs)

def hide_and_remove_old():
    removed = 0
    hidden = 0
    # Remove older scripted environment collections outright so only the new rebuild remains visible.
    old_collections = [
        "V2B_SKY", "V2C_SKY_CLOUDS", "V2C_SMOKE", "HERO_SKY_BACKDROP",
        "V2C_DRIFT_CAR", "V2B_LIGHTS_OVERHEAD", "HERO_STOREFRONT_REBUILD_OLD",
        "V2B_STRIPMALL", "V2C_STRIPMALL", "V2C_STOREFRONT", "V2C_STORE_REBUILD"
    ]
    for cname in old_collections:
        col = bpy.data.collections.get(cname)
        if col:
            remove_collection_recursive(col)
            removed += 1

    kill_prefixes = (
        "V2B_", "V2C_", "HERO_NightSky_Backdrop", "HERO_StoreSign", "V2C_StoreSign",
        "HERO_WideSidewalk", "HERO_WideCurb", "HERO_FlatParkingLine", "HERO_FlatBackParkingLine"
    )
    kill_contains = (
        "StoreSign", "OldStripMall", "OldStore", "BackdropSky"
    )
    preserve_exact = {"F2", "HANDREFINE_J2B_Working"}
    preserve_prefix = ("Audi e-tron GT quattro Black",)

    for obj in list(bpy.data.objects):
        if obj.name in preserve_exact or obj.name.startswith(preserve_prefix):
            continue
        if obj.name.startswith(kill_prefixes) or any(tok in obj.name for tok in kill_contains):
            remove_obj(obj)
            removed += 1

    # Also hide any stray non-HERO storefront/parking meshes left behind from earlier passes.
    stray_tokens = ("StoreMall", "Storefront", "GlassPanel", "GlassDoor", "ParkingLine", "Sidewalk", "Curb")
    for obj in list(bpy.data.objects):
        if obj.name.startswith("HERO_") or obj.name in preserve_exact or obj.name.startswith(preserve_prefix):
            continue
        if any(tok in obj.name for tok in stray_tokens):
            obj.hide_viewport = True
            obj.hide_render = True
            hidden += 1

    log(f"[cleanup] removed {removed} old scripted environment items and hid {hidden} stray legacy objects")

def setup_sky(f2_bounds, front_y):
    # User already configured the world sky/HDRI manually. Preserve it untouched.
    log("[sky] existing user-managed world sky/HDRI preserved unchanged")


def build_storefront_sidewalk(f2_bounds):

    sx, sy, sz = dims(f2_bounds)
    col_store = replace_collection("HERO_STOREFRONT_REBUILD")
    col_side = replace_collection("HERO_SIDEWALK_CURB_REBUILD")
    stucco = mat_principled("HERO_MAT_StoreStucco", (0.13,0.12,0.105), 0.72, 0)
    roof = mat_principled("HERO_MAT_FlatRoof", (0.075,0.075,0.070), 0.82, 0)
    frame = mat_principled("HERO_MAT_ConjoinedBlackMetalFrames", (0.006,0.007,0.008), 0.28, 0.65)
    glass = mat_principled("HERO_MAT_GlossyFloorGlass", (0.004,0.010,0.018), 0.035, 0.22, 0.72)
    concrete = mat_principled("HERO_MAT_SidewalkConcrete", (0.24,0.23,0.21), 0.78, 0)
    groove = mat_principled("HERO_MAT_SidewalkGroove", (0.07,0.07,0.068), 0.90, 0)

    front_y = 24.0
    depth = 6.0
    center_y = front_y + depth/2
    width = sx * 9.2
    body_h = sz * 2.1
    roof_h = sz * 0.14

    add_cube("HERO_StoreMall_DeepBody", (0, center_y, body_h/2), (width/2, depth/2, body_h/2), col_store, stucco, 0.02)
    add_cube("HERO_StoreMall_FlatRoof", (0, center_y, body_h+roof_h/2), (width/2+0.4, depth/2+0.25, roof_h/2), col_store, roof, 0.01)
    add_cube("HERO_StoreMall_FrontParapet", (0, front_y-0.08, body_h+roof_h+sz*0.12), (width/2+0.45, 0.10, sz*0.12), col_store, stucco, 0.01)

    bay_count = 4
    bay_w = sx * 1.50
    bay_gap = sx * 0.45
    total = bay_count*bay_w + (bay_count-1)*bay_gap
    start = -total/2 + bay_w/2
    bottom = 0.06
    top = sz * 1.43
    y = front_y - 0.13
    fd = 0.05
    t = 0.035

    add_cube("HERO_Storefront_ContinuousTopFrame", (0,y-0.035,top), (total/2+0.1,fd,t), col_store, frame, 0.003)
    add_cube("HERO_Storefront_ContinuousBottomFrame", (0,y-0.035,bottom), (total/2+0.1,fd,t), col_store, frame, 0.003)

    for i in range(bay_count):
        cx = start + i*(bay_w+bay_gap)
        h = top-bottom
        add_cube(f"HERO_GlassStorefront_Bay_{i}", (cx,y,bottom+h/2), (bay_w/2,0.018,h/2), col_store, glass, 0.004)
        add_cube(f"HERO_Storefront_LeftVertical_{i}", (cx-bay_w/2,y-0.035,bottom+h/2), (t/2,fd,h/2), col_store, frame, 0.002)
        add_cube(f"HERO_Storefront_RightVertical_{i}", (cx+bay_w/2,y-0.035,bottom+h/2), (t/2,fd,h/2), col_store, frame, 0.002)
        add_cube(f"HERO_Storefront_MidHorizontal_{i}", (cx,y-0.035,bottom+h*0.50), (bay_w/2,fd,t/2), col_store, frame, 0.002)
        if i in (1,2):
            door_h = sz * 1.18
            door_w = bay_w * 0.34
            dz = bottom + door_h/2
            add_cube(f"HERO_DoubleDoor_LeftSide_{i}", (cx-door_w,y-0.055,dz), (t/2,fd*1.25,door_h/2), col_store, frame, 0.002)
            add_cube(f"HERO_DoubleDoor_CenterMeet_{i}", (cx,y-0.058,dz), (t/2,fd*1.30,door_h/2), col_store, frame, 0.002)
            add_cube(f"HERO_DoubleDoor_RightSide_{i}", (cx+door_w,y-0.055,dz), (t/2,fd*1.25,door_h/2), col_store, frame, 0.002)
            add_cube(f"HERO_DoubleDoor_TopFrame_{i}", (cx,y-0.058,bottom+door_h), (door_w,fd*1.30,t/2), col_store, frame, 0.002)
        else:
            add_cube(f"HERO_Storefront_CenterMullion_{i}", (cx,y-0.035,bottom+h/2), (t/2,fd,h/2), col_store, frame, 0.002)

    hvac = mat_principled("HERO_MAT_RooftopHVAC", (0.08,0.08,0.076), 0.58, 0.15)
    for i,x in enumerate([-width*0.32,-width*0.10,width*0.12,width*0.34]):
        add_cube(f"HERO_Rooftop_HVAC_{i}", (x,center_y,body_h+roof_h+sz*0.06), (sx*0.20,0.24,sz*0.060), col_store, hvac, 0.010)
        add_cyl(f"HERO_Rooftop_Vent_{i}", (x+sx*0.18,center_y+0.06,body_h+roof_h+sz*0.14), 0.045, 0.13, col_store, hvac, 20)

    sidewalk_depth = sy * 3.35
    sidewalk_y = front_y - sidewalk_depth/2
    curb_y = front_y - sidewalk_depth - 0.035
    add_cube("HERO_Sidewalk_WideTop", (0,sidewalk_y,0.020), (width/2+0.65, sidewalk_depth/2, 0.040), col_side, concrete, 0.010)
    add_cube("HERO_Curb_VerticalFace", (0,curb_y,0.005), (width/2+0.65, 0.040, 0.075), col_side, concrete, 0.004)
    add_cube("HERO_Curb_TopLip", (0,curb_y+0.055,0.050), (width/2+0.65, 0.085, 0.018), col_side, concrete, 0.004)
    for j in range(1,8):
        x = -width/2 + j*(width/8)
        add_cube(f"HERO_Sidewalk_ExpansionJoint_X_{j}", (x,sidewalk_y,0.046), (0.018, sidewalk_depth/2, 0.004), col_side, groove, 0)
    add_cube("HERO_Sidewalk_CurbIndentLine", (0,curb_y+0.12,0.060), (width/2+0.55,0.012,0.004), col_side, groove, 0)

    log("[storefront] rebuilt larger storefronts, conjoined frames, double-door frame sections, moderately wide sidewalk and curb")
    return {"front_y": front_y, "width": width, "body_height": body_h, "sidewalk_depth": sidewalk_depth}

def build_h_parking_and_lamps(f2_bounds):
    sx, sy, sz = dims(f2_bounds)
    parking = replace_collection("HERO_H_PARKING_LAYOUT")
    lamps = replace_collection("HERO_VISIBLE_LAMPPOSTS")
    paint = mat_principled("HERO_MAT_ParkingLinePaint", (0.82,0.76,0.56), 0.86, 0)
    metal = mat_principled("HERO_MAT_LampPostDarkMetal", (0.035,0.035,0.035), 0.35, 0.65)
    amber = mat_emission("HERO_MAT_LampGlassAmber", (1.0,0.34,0.055), 0.9)
    stall_w = sx * 0.95
    stall_d = sy * 2.35
    cols = 7
    total_w = stall_w * cols
    start_x = -total_w/2
    row_y = [1.15, 4.15]
    z = 0.0045
    line_w = 0.075
    # Build a cleaner H-like parking layout: vertical stall dividers with one center spine line,
    # no outer front/back caps that make the stalls read like boxes.
    for row,yc in enumerate(row_y):
        for c in range(cols+1):
            x = start_x + c*stall_w
            add_cube(f"HERO_HParking_Row{row}_Divider_{c}", (x,yc,z), (line_w/2,stall_d/2,0.0025), parking, paint, 0)
    center_y = sum(row_y)/len(row_y)
    add_cube("HERO_HParking_CenterSpine", (0,center_y,z), (total_w/2,line_w/2,0.0025), parking, paint, 0)

    # Quarter intersections of the parking layout
    positions = [(-total_w*0.25, row_y[0]+stall_d/2, sz*1.92), (total_w*0.25, row_y[1]-stall_d/2, sz*1.92)]
    light_col = ensure_collection("V2B_LIGHTS_OVERHEAD")
    for i,(x,y,lz) in enumerate(positions):
        name=f"V2B_OverheadAmber_{i}"
        obj=bpy.data.objects.get(name)
        if not obj:
            data=bpy.data.lights.new(name+"_Data","AREA")
            obj=bpy.data.objects.new(name,data)
            light_col.objects.link(obj)
        obj.location=(x,y,lz)
        obj.hide_viewport=False
        obj.hide_render=False
        obj.data.energy=520 if i==0 else 300
        obj.data.color=(1.0,0.37,0.055)
        obj.data.shape="DISK"
        obj.data.size=2.2
        try:
            move_to_collection(obj, light_col)
        except Exception:
            pass
        add_cyl(f"HERO_LampPole_{i}", (x,y,lz/2), 0.045, lz, lamps, metal, 28)
        direction = -1 if i==0 else 1
        add_cyl(f"HERO_LampArm_{i}", (x,y+direction*0.32,lz), 0.026, 0.64, lamps, metal, 18, rotation=(math.pi/2,0,0))
        add_cube(f"HERO_LampFixture_{i}", (x,y+direction*0.66,lz), (0.42,0.17,0.060), lamps, metal, 0.018)
        add_cube(f"HERO_LampGlass_{i}", (x,y+direction*0.66,lz-0.04), (0.36,0.13,0.014), lamps, amber, 0.010)
    log("[parking] cleaner H-like spaces with quarter-intersection lamp posts rebuilt")
    return {"total_width": total_w, "row_y": row_y, "stall_width": stall_w, "stall_depth": stall_d}

def render_review(f2_bounds, audi_bounds, store_info):
    col = replace_collection("HERO_REVIEW_CAMERAS")
    target = center(f2_bounds)
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
    except Exception:
        pass
    specs=[
        ("HERO_CAM_StorefrontScale",(target.x+8.5,target.y-8.5,target.z+3.2),Vector((0,store_info["front_y"]-1.5,store_info["body_height"]*0.65)),42,"01_StorefrontScale.png"),
        ("HERO_CAM_ParkingLampLayout",(target.x+9.0,target.y-8.5,target.z+6.0),Vector((0,3.0,1.0)),36,"02_ParkingLampLayout.png"),
        ("HERO_CAM_SkyStoreHero",(target.x+7.8,target.y-9.5,target.z+4.0),Vector((0,store_info["front_y"],store_info["body_height"]*1.05)),40,"03_SkyStoreHero.png")
    ]
    for name, loc, aim, lens, fn in specs:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.location=loc
        cam.data.lens=lens
        look_at(cam,aim)
        col.objects.link(cam)
        scene.camera=cam
        scene.render.filepath=str(OUT_DIR/fn)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {fn}")
    current=project_root()/ "renders" / "current_review"
    current.mkdir(parents=True,exist_ok=True)
    for p in current.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (current/p.name).write_bytes(p.read_bytes())

def write_status(store, parking):
    data={"storefront":"rebuilt large floor-to-sidewalk glass with conjoined frames and double-door frame sections",
          "signs":"removed", "sidewalk":"wide sidewalk with curb face/lip and indent grooves",
          "parking":"cleaner H-like layout with no boxed stall caps", "lamp_posts":"quarter intersections",
          "sky":"user-managed existing world sky preserved", "store_info":store, "parking_info":parking}
    (OUT_DIR/"StorefrontParkingV1C_status.json").write_text(json.dumps(data,indent=2), encoding="utf-8")

def export_manifest():
    script=project_root()/ "blender" / "scripts" / "export_project_layout_and_scene.py"
    if script.exists():
        ns={"__file__":str(script),"__name__":"__main__"}
        exec(script.read_text(encoding="utf-8"), ns)

def main():
    reset_log()
    hide_and_remove_old()
    f2_bounds=get_f2_bounds()
    audi_bounds=get_audi_bounds()
    store=build_storefront_sidewalk(f2_bounds)
    parking=build_h_parking_and_lamps(f2_bounds)
    setup_sky(f2_bounds, store["front_y"])
    render_review(f2_bounds, audi_bounds, store)
    write_status(store, parking)
    export_manifest()
    out=project_root()/ "blender" / "sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with (OUT_DIR/"StorefrontParkingV1C_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
