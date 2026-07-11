import sys, json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root

OUT_DIR = project_root() / "renders" / "lamp_sidewalk_sky_cleanup"
F2_NAME = "F2"
AUDI_COLLECTION = "Audi e-tron GT quattro Black"
LIGHT_COLLECTION = "V2B_LIGHTS_OVERHEAD"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "LampSidewalkSkyCleanup_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LampSidewalkSkyCleanup_report.txt").write_text("", encoding="utf-8")

def world_bounds(obj):
    if not hasattr(obj, "bound_box"):
        return None
    try:
        coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)
    except Exception:
        return None

def union_bounds(objects):
    boxes=[world_bounds(o) for o in objects if o.type == "MESH" and world_bounds(o)]
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

def ensure_collection(name):
    col=bpy.data.collections.get(name)
    if not col:
        col=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport=False
    col.hide_render=False
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

def remove_collection(name):
    col=bpy.data.collections.get(name)
    if col:
        log(f"[cleanup] removing collection {name}")
        remove_collection_recursive(col)

def mat_principled(name, color, roughness=0.5, metallic=0.0):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    nodes.clear()
    out=nodes.new("ShaderNodeOutputMaterial")
    bsdf=nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value=(*color,1.0)
    bsdf.inputs["Roughness"].default_value=roughness
    bsdf.inputs["Metallic"].default_value=metallic
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def mat_emission(name, color, strength=1.0):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    nodes.clear()
    out=nodes.new("ShaderNodeOutputMaterial")
    em=nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value=(*color,1.0)
    em.inputs["Strength"].default_value=strength
    links.new(em.outputs["Emission"], out.inputs["Surface"])
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
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    if mat:
        assign_mat(obj, mat)
    if bevel > 0:
        be=obj.modifiers.new("Bevel","BEVEL")
        be.width=bevel
        be.segments=3
        obj.modifiers.new("WeightedNormals","WEIGHTED_NORMAL")
    return obj

def add_cyl(name, loc, radius, depth, col, mat=None, vertices=32, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj=bpy.context.object
    obj.name=name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    if mat:
        assign_mat(obj, mat)
    return obj

def look_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()

def get_f2_bounds():
    f2=bpy.data.objects.get(F2_NAME)
    if not f2:
        raise RuntimeError("F2 not found.")
    f2.hide_viewport=False
    f2.hide_render=False
    for col in f2.users_collection:
        col.hide_viewport=False
        col.hide_render=False
    return world_bounds(f2)

def get_audi_bounds():
    col=bpy.data.collections.get(AUDI_COLLECTION)
    objs=[]
    if col:
        col.hide_viewport=False
        col.hide_render=False
        objs.extend(list(col.objects))
    empty=bpy.data.objects.get(AUDI_COLLECTION)
    if empty:
        empty.hide_viewport=False
        empty.hide_render=False
        objs.append(empty)
        objs.extend(list(empty.children_recursive))
    return union_bounds(objs)

def delete_old_sky_duplicates():
    # Remove V2B/V2C scripted sky objects and collections. HDRI world remains.
    for name in ["V2B_SKY", "V2C_SKY_CLOUDS", "V2C_SMOKE"]:
        remove_collection(name)
    prefixes=("V2B_Moon","V2B_Cloud","V2B_Star","V2C_Moon","V2C_SmokeCloud","V2C_Star","V2C_Cloud")
    count=0
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            remove_obj(obj)
            count+=1
    log(f"[sky] removed {count} old moon/cloud/star duplicate objects")

def remove_old_lamp_geometry():
    prefixes=("V2B_LampPole","V2B_LampArm","V2B_LampFixture","V2C_LampPole","V2C_LampArm","V2C_LampFixture")
    count=0
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            remove_obj(obj)
            count+=1
    log(f"[lighting] removed {count} old lamp geometry objects")

def reposition_overhead_lights(f2_bounds):
    sx, sy, sz=dims(f2_bounds)
    zmin=f2_bounds[4]
    col=ensure_collection(LIGHT_COLLECTION)
    # Use existing light objects when possible, but move them to new visible overhead positions.
    light_specs=[
        ("V2B_OverheadAmber_0", (-sx*0.85, 2.10, zmin+sz*1.86), 520, 2.05),
        ("V2B_OverheadAmber_1", ( sx*0.95, 2.75, zmin+sz*1.86), 260, 2.00),
    ]
    lights=[]
    for name, loc, energy, size in light_specs:
        obj=bpy.data.objects.get(name)
        if not obj:
            data=bpy.data.lights.new(name+"_Data","AREA")
            obj=bpy.data.objects.new(name,data)
            col.objects.link(obj)
        if obj.name not in col.objects:
            try:
                col.objects.link(obj)
            except Exception:
                pass
        obj.hide_viewport=False
        obj.hide_render=False
        obj.location=loc
        obj.data.energy=energy
        obj.data.color=(1.0,0.37,0.055)
        obj.data.shape="DISK"
        obj.data.size=size
        lights.append(obj)
    log("[lighting] overhead amber lights moved to visible pole positions")
    return lights

def rebuild_lamp_posts(lights, f2_bounds):
    sx, sy, sz=dims(f2_bounds)
    zmin=f2_bounds[4]
    col=ensure_collection("HERO_VISIBLE_LAMPPOSTS")
    for obj in list(col.objects):
        remove_obj(obj)
    metal=mat_principled("HERO_MAT_LampPostDarkMetal",(0.035,0.035,0.035),0.35,0.65)
    amber=mat_emission("HERO_MAT_LampGlassAmber",(1.0,0.34,0.055),0.8)
    for i, light in enumerate(lights):
        x,y,z=light.location
        pole_height=z-zmin
        add_cyl(f"HERO_LampPole_{i}",(x,y,zmin+pole_height/2),0.042,pole_height,col,metal,28)
        # small extended tube toward the parking lot
        add_cyl(f"HERO_LampArm_{i}",(x,y-0.26,z),0.024,0.52,col,metal,18,rotation=(1.57079632679,0,0))
        add_cube(f"HERO_LampFixture_{i}",(x,y-0.56,z),(0.34,0.15,0.055),col,metal,0.018)
        add_cube(f"HERO_LampGlass_{i}",(x,y-0.56,z-0.035),(0.30,0.12,0.012),col,amber,0.010)
    log("[lighting] rebuilt visible lamp posts/arms/fixtures at overhead light positions")

def widen_sidewalk_and_clean_lines(f2_bounds):
    sx, sy, sz=dims(f2_bounds)
    concrete=mat_principled("HERO_MAT_WideConcrete",(0.24,0.23,0.21),0.78,0)
    paint=mat_principled("HERO_MAT_FlatParkingPaint",(0.80,0.74,0.55),0.86,0)
    env=ensure_collection("HERO_ENV_CORRECTIONS")

    # Hide existing narrow sidewalk/curb objects rather than deleting all store geometry.
    hidden=0
    for obj in bpy.data.objects:
        if obj.name.startswith(("V2C_Sidewalk","V2C_Curb","V2B_Sidewalk","V2B_Curb")):
            obj.hide_viewport=True
            obj.hide_render=True
            hidden+=1
    log(f"[sidewalk] hid {hidden} old narrow sidewalk/curb objects")

    # Determine storefront front-ish y from existing strip mall objects.
    y_front=18.85
    ys=[obj.location.y for obj in bpy.data.objects if obj.name.startswith(("V2C_StripMall","V2C_GlassPanel","V2C_GlassDoor"))]
    if ys:
        y_front=min(ys)-0.55

    add_cube("HERO_WideSidewalk",(0,y_front,0.025),(sx*5.8,0.95,0.045),env,concrete,0.018)
    add_cube("HERO_WideCurb",(0,y_front-0.62,0.055),(sx*5.8,0.085,0.070),env,concrete,0.010)

    # Hide old raised parking lines and rebuild flat double-thick review lines.
    old=0
    for obj in bpy.data.objects:
        if obj.name.startswith(("V2C_ParkingLine","V2C_BackParkingLine","V2B_ParkingLine","V2B_BackParkingLine")):
            obj.hide_viewport=True
            obj.hide_render=True
            old+=1
    log(f"[parking] hid {old} old parking line objects")

    line_z=0.004
    for i,x in enumerate([-sx*2.7,-sx*1.8,-sx*0.9,0,sx*0.9,sx*1.8,sx*2.7]):
        add_cube(f"HERO_FlatParkingLine_{i}",(x,0.85,line_z),(0.075,sz*1.10,0.0025),env,paint,0.000)
    add_cube("HERO_FlatBackParkingLine",(-sx*1.60,2.95,line_z),(sx*1.05,0.075,0.0025),env,paint,0.000)

def render_review(f2_bounds, audi_bounds):
    cams_col=ensure_collection("HERO_REVIEW_CAMERAS")
    # clear only cameras in this collection
    for obj in list(cams_col.objects):
        remove_obj(obj)
    target=center(f2_bounds)
    if audi_bounds:
        car=center(audi_bounds)
        target=Vector((target.x*0.78+car.x*0.22, target.y*0.78+car.y*0.22, target.z*0.85))
    sx,sy,sz=dims(f2_bounds)
    specs=[
        ("HERO_CAM_LampSidewalkReview",(sx*2.9,-sz*2.7,sz*1.25),target,45,"01_LampSidewalk_Hero.png"),
        ("HERO_CAM_LampVisibility",(sx*1.1,-sz*2.1,sz*1.85),Vector((0,2.4,sz*1.05)),42,"02_LampVisibility.png"),
        ("HERO_CAM_HighLayout",(sx*3.2,-sz*2.5,sz*2.2),Vector((0,4.8,sz*0.75)),38,"03_HighLayout.png"),
    ]
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    cams={}
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    for name,loc,aim,lens,fn in specs:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.location=loc
        cam.data.lens=lens
        look_at(cam,aim)
        cams_col.objects.link(cam)
        cams[name]=cam
        scene.camera=cam
        scene.render.filepath=str(OUT_DIR/fn)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {fn}")
    # copy current review
    cur=project_root()/ "renders" / "current_review"
    cur.mkdir(parents=True,exist_ok=True)
    for p in cur.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (cur/p.name).write_bytes(p.read_bytes())

def write_status():
    status={
        "lamp_posts":"Moved/rebuilt visible lamp posts and fixtures at overhead amber light positions",
        "sidewalk":"Old narrow sidewalk hidden; wider sidewalk/curb added",
        "sky_duplicates":"Old V2B/V2C moon/cloud/star geometry removed; HDRI world left intact",
        "parking_lines":"Old raised lines hidden; double-thick flat lines added",
        "git_cleanup":"Publish script now stages package-file deletions and current package utilities"
    }
    (OUT_DIR/"LampSidewalkSkyCleanup_status.json").write_text(json.dumps(status,indent=2),encoding="utf-8")

def export_manifest():
    script=project_root()/"blender"/"scripts"/"export_project_layout_and_scene.py"
    if script.exists():
        ns={"__file__":str(script),"__name__":"__main__"}
        exec(script.read_text(encoding="utf-8"), ns)

def main():
    reset_log()
    delete_old_sky_duplicates()
    remove_old_lamp_geometry()
    f2_bounds=get_f2_bounds()
    audi_bounds=get_audi_bounds()
    lights=reposition_overhead_lights(f2_bounds)
    rebuild_lamp_posts(lights,f2_bounds)
    widen_sidewalk_and_clean_lines(f2_bounds)
    render_review(f2_bounds,audi_bounds)
    write_status()
    export_manifest()
    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with (OUT_DIR/"LampSidewalkSkyCleanup_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
