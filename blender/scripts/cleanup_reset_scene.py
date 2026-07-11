import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

KEEP_CHARACTER_OBJECTS = {
    "F2",
    "HANDREFINE_J2B_Working",
}
KEEP_CHARACTER_COLLECTIONS = {
    "CHAR_Meshy_LeftCandidate_Refined",
    "CHAR_HandRefine_J2B",
    "BASE_Meshy_LeftCandidate_Source",
}

FINAL_LIGHTS = "FINAL_LIGHTS_Minimal"
FINAL_CAMERAS = "FINAL_CAMERAS"
FINAL_HELPERS = "FINAL_HELPERS"
OUT_DIR = project_root() / "renders" / "cleanup_reset_validation"

def log(msg):
    print(msg)

def remove_collection_recursive(col):
    for child in list(col.children):
        remove_collection_recursive(child)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)

def remove_named_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        remove_collection_recursive(col)

def delete_object(obj):
    bpy.data.objects.remove(obj, do_unlink=True)

def world_bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def look_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def cleanup_preview_and_diagnostics():
    # Integrated preview branch and all generated PP collections.
    for name in list(bpy.data.collections.keys()):
        if (
            name == "PRODUCTION_PREVIEW"
            or name.startswith("PP_")
            or name.startswith("DIAG_")
            or name.startswith("GUIDE_")
            or name in {
                "CHAR_HandRefine_J1",
                "CHAR_HandRefine_J2",
                "CHAR_HandRefine_J3",
                "CHAR_HandRefine_J4",
                "CHAR_HandRefine_Working",
                "CHECKPOINT_ManualProgress",
                "MESHY_CandidateGallery",
                "MESHY_Components",
                "MESHY_GalleryComponents",
            }
        ):
            col=bpy.data.collections.get(name)
            if col:
                log(f"[cleanup] removing collection {name}")
                remove_collection_recursive(col)

    # Remove obsolete character branch objects even if they became unlinked elsewhere.
    obsolete_prefixes=(
        "HANDREFINE_J1",
        "HANDREFINE_J2_Working",
        "HANDREFINE_J3",
        "HANDREFINE_J4",
        "GUIDE_",
        "PP_",
        "MANUAL_DIAG_",
        "HG_",
        "STRUCT_",
        "REFINE_",
        "ORANGE_TOPO_",
    )
    for obj in list(bpy.data.objects):
        if obj.name == "HANDREFINE_J2B_Working":
            continue
        if obj.name.startswith(obsolete_prefixes):
            log(f"[cleanup] removing object {obj.name}")
            delete_object(obj)

def cleanup_character_duplicates():
    # Keep only three meaningful character states:
    # 1) original extracted source collection
    # 2) F2 manual-cleaned baseline
    # 3) J2B best hand branch
    for name in list(bpy.data.collections.keys()):
        if name in KEEP_CHARACTER_COLLECTIONS:
            continue
        if (
            name.startswith("CHAR_Meshy_")
            or name.startswith("BASE_Meshy_")
            or name.startswith("CHAR_HandRefine_")
        ):
            col=bpy.data.collections.get(name)
            if col:
                log(f"[cleanup] pruning character collection {name}")
                remove_collection_recursive(col)

def clear_lights_and_cameras():
    for obj in list(bpy.data.objects):
        if obj.type in {"LIGHT","CAMERA"}:
            delete_object(obj)

    for name in [FINAL_LIGHTS, FINAL_CAMERAS, FINAL_HELPERS]:
        remove_named_collection(name)

def yarn_material():
    mat=bpy.data.materials.get("FINAL_MAT_CrochetYarn")
    if mat is None:
        mat=bpy.data.materials.new("FINAL_MAT_CrochetYarn")
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    nodes.clear()

    out=nodes.new("ShaderNodeOutputMaterial")
    bsdf=nodes.new("ShaderNodeBsdfPrincipled")
    tex=nodes.new("ShaderNodeTexCoord")
    mapping=nodes.new("ShaderNodeMapping")
    wave=nodes.new("ShaderNodeTexWave")
    noise=nodes.new("ShaderNodeTexNoise")
    mult=nodes.new("ShaderNodeMath")
    bump=nodes.new("ShaderNodeBump")

    bsdf.inputs["Base Color"].default_value=(0.23,0.095,0.035,1)
    bsdf.inputs["Roughness"].default_value=0.82

    mapping.inputs["Scale"].default_value=(18.0,18.0,45.0)

    wave.wave_type='BANDS'
    wave.bands_direction='Z'
    wave.inputs["Scale"].default_value=55.0
    wave.inputs["Distortion"].default_value=2.5
    wave.inputs["Detail"].default_value=4.0

    noise.inputs["Scale"].default_value=22.0
    noise.inputs["Detail"].default_value=4.0
    noise.inputs["Roughness"].default_value=0.72

    mult.operation='MULTIPLY'
    mult.inputs[1].default_value=0.65

    bump.inputs["Strength"].default_value=0.32
    bump.inputs["Distance"].default_value=0.018

    links.new(tex.outputs["Generated"],mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"],wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"],noise.inputs["Vector"])
    links.new(wave.outputs["Color"],mult.inputs[0])
    links.new(noise.outputs["Fac"],mult.inputs[1])
    links.new(mult.outputs[0],bump.inputs["Height"])
    links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"],out.inputs["Surface"])
    return mat

def assign_yarn():
    mat=yarn_material()
    for name in ["F2","HANDREFINE_J2B_Working"]:
        obj=bpy.data.objects.get(name)
        if obj and obj.type=='MESH':
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            log(f"[material] assigned crochet-yarn material to {name}")

def create_minimal_lighting(target):
    col=bpy.data.collections.new(FINAL_LIGHTS)
    bpy.context.scene.collection.children.link(col)

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h=zmax-zmin
    w=xmax-xmin

    specs=[
        ("FINAL_AMBER_KEY",(center.x-w*1.7, center.y-h*1.4, center.z+h*1.4), 420, 2.5),
        ("FINAL_AMBER_RIM",(center.x+w*1.9, center.y+h*1.5, center.z+h*1.5), 180, 2.0),
    ]
    for name,loc,energy,size in specs:
        data=bpy.data.lights.new(name+"_Data",type='AREA')
        data.energy=energy
        data.shape='DISK'
        data.size=size
        data.color=(1.0,0.30,0.055)
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        look_at(obj,center)
        col.objects.link(obj)

    log("[lighting] created exactly two amber area lights")

def create_clean_cameras(target):
    col=bpy.data.collections.new(FINAL_CAMERAS)
    bpy.context.scene.collection.children.link(col)

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h=zmax-zmin
    d=max(5.0,h*2.2)

    specs=[
        ("FINAL_CAM_HERO",(center.x+d*0.85,center.y-d*0.95,center.z+h*0.30),center,52),
        ("FINAL_CAM_LOW",(center.x+d*0.55,center.y-d*0.75,zmin+h*0.20),Vector((center.x,center.y,center.z+h*0.05)),44),
        ("FINAL_CAM_ORBIT",(center.x+d,center.y-d*0.55,center.z+h*0.45),center,55),
    ]
    cams={}
    for name,loc,aim,lens in specs:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.data.lens=lens
        cam.location=loc
        look_at(cam,aim)
        col.objects.link(cam)
        cams[name]=cam

    helper_col=bpy.data.collections.new(FINAL_HELPERS)
    bpy.context.scene.collection.children.link(helper_col)
    rig=bpy.data.objects.new("FINAL_ORBIT_RIG",None)
    rig.location=center
    helper_col.objects.link(rig)

    orbit=cams["FINAL_CAM_ORBIT"]
    orbit.parent=rig
    rig.rotation_euler=(0,0,0)
    rig.keyframe_insert(data_path="rotation_euler",frame=1)
    rig.rotation_euler=(0,0,1.35)
    rig.keyframe_insert(data_path="rotation_euler",frame=120)

    log("[camera] created exactly three cameras plus one orbit helper")
    return cams

def hide_old_environment_clutter():
    # Hide any remaining legacy environment collections without deleting user-authored scene data.
    for name in ["ENV_ParkingLot","LGT_Night","CAM_Rigs"]:
        col=bpy.data.collections.get(name)
        if col:
            col.hide_viewport=True
            col.hide_render=True

def configure_scene():
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.world.color=(0.0015,0.002,0.004)
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.frame_start=1
    scene.frame_end=120
    scene.render.fps=24

def render_validation(target,cams):
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene

    states={}
    for obj in bpy.context.scene.objects:
        states[obj.name]=obj.hide_render
        if obj.type=='MESH' and obj != target:
            obj.hide_render=True
    target.hide_render=False

    views=[
        ("FINAL_CAM_HERO","01_Clean_Hero.png"),
        ("FINAL_CAM_LOW","02_Clean_Low.png"),
        ("FINAL_CAM_ORBIT","03_Clean_Orbit.png"),
    ]
    for cam_name,fn in views:
        scene.camera=cams[cam_name]
        scene.render.filepath=str(OUT_DIR/fn)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {fn}")

    for name,state in states.items():
        obj=bpy.data.objects.get(name)
        if obj:
            obj.hide_render=state

def write_inventory():
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    path=OUT_DIR/"CleanupReset_inventory.txt"
    lights=[o.name for o in bpy.data.objects if o.type=='LIGHT']
    cams=[o.name for o in bpy.data.objects if o.type=='CAMERA']
    arms=[o.name for o in bpy.data.objects if o.type=='ARMATURE']
    char_cols=[c.name for c in bpy.data.collections if c.name.startswith(("CHAR_","BASE_Meshy_"))]
    lines=[
        "Cleanup Reset Inventory\n",
        "=======================\n\n",
        f"Lights ({len(lights)}): {lights}\n",
        f"Cameras ({len(cams)}): {cams}\n",
        f"Armatures ({len(arms)}): {arms}\n",
        f"Character collections ({len(char_cols)}): {char_cols}\n",
    ]
    path.write_text("".join(lines),encoding="utf-8")

def main():
    log("[cleanup] starting scene cleanup/reset")
    cleanup_preview_and_diagnostics()
    cleanup_character_duplicates()
    clear_lights_and_cameras()
    hide_old_environment_clutter()

    target=bpy.data.objects.get("F2")
    if not target or target.type!='MESH':
        raise RuntimeError("F2 manual-cleaned character baseline not found.")

    # F2 is the visible body baseline; J2B is retained as best hand reference branch.
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            obj.hide_render=True
            obj.hide_viewport=True
    target.hide_render=False
    target.hide_viewport=False

    j2b=bpy.data.objects.get("HANDREFINE_J2B_Working")
    if j2b:
        j2b.hide_render=True
        j2b.hide_viewport=True

    assign_yarn()
    configure_scene()
    create_minimal_lighting(target)
    cams=create_clean_cameras(target)
    render_validation(target,cams)
    write_inventory()

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__=="__main__":
    main()
