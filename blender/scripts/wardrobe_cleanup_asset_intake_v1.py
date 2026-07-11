import sys, json, math, traceback
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root

OUT_DIR = project_root() / "renders" / "wardrobe_cleanup_asset_intake_v1"
CLOTHING_ASSET_ROOT = project_root() / "blender" / "assets" / "models" / "clothing"
IMPORT_COLLECTION = "HERO_IMPORTED_CLOTHING_CANDIDATES"
CLEANUP_STATUS = "WardrobeCleanupAssetIntake_status.json"

def log(msg):
    print(msg)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "WardrobeCleanupAssetIntake_report.txt").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def reset_log():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "WardrobeCleanupAssetIntake_report.txt").write_text("", encoding="utf-8")

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
        coords=[obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    except Exception:
        return None

def union_bounds(objects):
    boxes=[]
    for obj in objects:
        if obj.type == "MESH":
            b=world_bounds(obj)
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

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z","Y").to_euler()

def mat_principled(name, color, roughness=0.5, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    nodes.clear()
    out=nodes.new("ShaderNodeOutputMaterial")
    bsdf=nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value=(*color, alpha)
    bsdf.inputs["Roughness"].default_value=roughness
    bsdf.inputs["Metallic"].default_value=metallic
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value=alpha
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if alpha < 1:
        mat.blend_method = "BLEND"
    return mat

def mat_emission(name, color, strength=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    nodes.clear()
    out=nodes.new("ShaderNodeOutputMaterial")
    em=nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value=(*color, 1.0)
    em.inputs["Strength"].default_value=strength
    links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat

def assign_mat(obj, mat):
    if hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)

def add_curve(name, points, col, mat, bevel=0.006):
    curve=bpy.data.curves.new(name+"_Curve","CURVE")
    curve.dimensions="3D"
    curve.resolution_u=3
    curve.bevel_depth=bevel
    curve.bevel_resolution=2
    sp=curve.splines.new("POLY")
    sp.points.add(len(points)-1)
    for p, co in zip(sp.points, points):
        p.co=(co[0],co[1],co[2],1)
    obj=bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def add_cube(name, loc, scale, col, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, col)
    if mat:
        assign_mat(obj, mat)
    if bevel > 0:
        be=obj.modifiers.new("Bevel","BEVEL")
        be.width=bevel
        be.segments=3
        obj.modifiers.new("WeightedNormals","WEIGHTED_NORMAL")
    return obj

def preserve_locked_scene():
    # Explicit no-op for lights/world/car. Only keep important collections visible.
    locked_visible = [
        "V2B_LIGHTS_OVERHEAD",
        "HERO_CAR_AMBER_READ",
        "HERO_VISIBLE_LAMPPOSTS",
        "HERO_CAR_UNDERGLOW",
        "Audi e-tron GT quattro Black",
        "HERO_STOREFRONT_REBUILD",
        "HERO_SIDEWALK_CURB_REBUILD",
        "HERO_H_PARKING_LAYOUT",
    ]
    for name in locked_visible:
        col=bpy.data.collections.get(name)
        if col:
            col.hide_viewport=False
            col.hide_render=False
    log("[lock] preserved current lights, car, world/HDRI, storefront, sidewalk, and parking without modification")

def get_f2_bounds():
    f2=bpy.data.objects.get("F2")
    if not f2:
        raise RuntimeError("F2 was not found.")
    f2.hide_viewport=False
    f2.hide_render=False
    for c in f2.users_collection:
        c.hide_viewport=False
        c.hide_render=False
    return f2, world_bounds(f2)

def hide_material_boxes_and_blocky_accents(f2_bounds):
    hidden=0
    # Hide material swatches: those are the floating boxes the user saw.
    col=bpy.data.collections.get("HERO_CHARACTER_MATERIAL_GUIDES")
    if col:
        col.hide_viewport=True
        col.hide_render=True
        hidden += len(col.objects)
    for obj in bpy.data.objects:
        if obj.name.startswith("HERO_MaterialSwatch_"):
            obj.hide_viewport=True
            obj.hide_render=True
            hidden += 1
        if "FlameAccent" in obj.name and obj.name.startswith("HERO_BlackSkateShoe_"):
            obj.hide_viewport=True
            obj.hide_render=True
            hidden += 1
    log(f"[cleanup] hid {hidden} material swatch/blocky shoe accent objects")

    # Add small curved shoe graphics instead of blocky cubes, but keep them subtle and easy to delete.
    col2=replace_collection("HERO_SHOE_GRAPHIC_GUIDES")
    sx, sy, sz=dims(f2_bounds)
    c=center(f2_bounds)
    zmin=f2_bounds[4]
    orange=mat_emission("HERO_MAT_ShoeGraphicSoftOrange",(1.0,0.22,0.02),0.35)
    yellow=mat_emission("HERO_MAT_ShoeGraphicSoftYellow",(1.0,0.70,0.05),0.28)
    for side,label in [(-1,"L"),(1,"R")]:
        shoe_x=c.x+side*sx*0.13
        shoe_y=c.y-sy*0.32
        shoe_z=zmin+sz*0.085
        outer_x=shoe_x+side*sx*0.18
        add_curve(f"HERO_ShoeGraphic_{label}_OrangeSweep",[
            (outer_x,shoe_y,shoe_z),
            (outer_x+side*sx*0.030,shoe_y+sy*0.035,shoe_z+sz*0.018),
            (outer_x+side*sx*0.055,shoe_y+sy*0.080,shoe_z+sz*0.010),
        ],col2,orange,0.005)
        add_curve(f"HERO_ShoeGraphic_{label}_YellowSweep",[
            (outer_x-side*sx*0.025,shoe_y+sy*0.020,shoe_z+sz*0.010),
            (outer_x+side*sx*0.015,shoe_y+sy*0.055,shoe_z+sz*0.025),
            (outer_x+side*sx*0.050,shoe_y+sy*0.095,shoe_z+sz*0.020),
        ],col2,yellow,0.0035)
    log("[cleanup] added subtle curved shoe graphic guides to replace blocky cube flame accents")

def soften_wardrobe_preview_materials():
    # Reduce red-speckle / z-fighting look by avoiding super transparent alpha on overlap guides.
    hoodie=bpy.data.materials.get("HERO_MAT_BlackHoodie_Cloth")
    denim=bpy.data.materials.get("HERO_MAT_BaggyDenim_DarkBlue")
    for mat in [hoodie, denim]:
        if not mat or not mat.use_nodes:
            continue
        bsdf=mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if "Alpha" in bsdf.inputs:
                bsdf.inputs["Alpha"].default_value=0.88
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value=0.82
        mat.blend_method="BLEND"
    # Keep current fit guides but make them less likely to render as weird red edge artifacts.
    for obj in bpy.data.objects:
        if obj.name.startswith("HERO_Hoodie_") or obj.name.startswith("HERO_BaggyJean_"):
            obj.show_transparent=True
    log("[wardrobe] softened wardrobe preview material alpha/roughness to reduce overlap edge artifacts")

def ensure_clothing_asset_folders():
    folders=["hoodie","jeans","sneakers","misc"]
    for folder in folders:
        p=CLOTHING_ASSET_ROOT/folder
        p.mkdir(parents=True,exist_ok=True)
        readme=p/"PUT_GLB_OR_FBX_HERE.txt"
        if not readme.exists():
            readme.write_text(
                "Put downloaded clothing model files here. Preferred: .glb. Also supported by the import script: .gltf, .fbx, .blend.\\n"
                "The script will import candidate models into HERO_IMPORTED_CLOTHING_CANDIDATES for comparison; it will not replace the current clothing guides automatically.\\n",
                encoding="utf-8"
            )
    log(f"[assets] ensured clothing asset intake folders at {CLOTHING_ASSET_ROOT}")

def import_clothing_assets(f2_bounds):
    col=replace_collection(IMPORT_COLLECTION)
    supported={".glb",".gltf",".fbx",".blend"}
    files=[]
    if CLOTHING_ASSET_ROOT.exists():
        for p in CLOTHING_ASSET_ROOT.rglob("*"):
            if p.is_file() and p.suffix.lower() in supported:
                files.append(p)
    imported_groups=[]
    base_c=center(f2_bounds)
    sx,sy,sz=dims(f2_bounds)
    x_offset=sx*1.25
    y_offset=sy*1.10
    idx=0

    for path in files:
        before=set(bpy.data.objects)
        try:
            if path.suffix.lower() in {".glb",".gltf"}:
                bpy.ops.import_scene.gltf(filepath=str(path))
            elif path.suffix.lower()==".fbx":
                bpy.ops.import_scene.fbx(filepath=str(path))
            elif path.suffix.lower()==".blend":
                with bpy.data.libraries.load(str(path), link=False) as (data_from, data_to):
                    data_to.objects = list(data_from.objects)
                for obj in data_to.objects:
                    if obj:
                        bpy.context.scene.collection.objects.link(obj)
            after=set(bpy.data.objects)
            new_objs=[o for o in after-before if o]
            if not new_objs:
                continue

            parent=bpy.data.objects.new(f"HERO_ImportedClothing_{idx}_{path.stem}", None)
            col.objects.link(parent)
            parent.location=(base_c.x+x_offset, base_c.y+idx*y_offset, f2_bounds[4])
            for obj in new_objs:
                try:
                    move_to_collection(obj,col)
                except Exception:
                    pass
                obj.parent=parent
                obj.hide_viewport=False
                obj.hide_render=False
            # Scale to approximate Sackboy height if possible.
            b=union_bounds(new_objs)
            if b:
                _,_,h=dims(b)
                if h > 0:
                    target_h=sz*0.72
                    scale=max(0.02,min(5.0,target_h/h))
                    parent.scale=(scale,scale,scale)
            imported_groups.append({"file":str(path.relative_to(project_root())),"objects":len(new_objs)})
            idx += 1
        except Exception as e:
            log(f"[assets] failed to import {path}: {e}")

    if imported_groups:
        log(f"[assets] imported {len(imported_groups)} clothing candidate file(s)")
    else:
        log("[assets] no clothing asset files found yet; folders are ready for hoodie/jeans/sneaker downloads")
    return imported_groups

def write_manual_notes(imported_groups):
    notes_dir=project_root()/"reports"/"wardrobe_asset_notes"
    notes_dir.mkdir(parents=True,exist_ok=True)
    notes=(notes_dir/"Wardrobe_Asset_Intake_Notes.txt")
    notes.write_text(
        "WARDROBE ASSET INTAKE NOTES\\n"
        "===========================\\n\\n"
        "Preferred downloadable model format: .glb. It is usually easiest because it can carry mesh, materials, and textures together.\\n"
        "Put clothing candidates into:\\n"
        "  blender/assets/models/clothing/hoodie/\\n"
        "  blender/assets/models/clothing/jeans/\\n"
        "  blender/assets/models/clothing/sneakers/\\n\\n"
        "Material Preview reflection note:\\n"
        "If the storefront glass shows a different studio/HDRI image in Material Preview, use Rendered mode for the true scene world, or open the Material Preview dropdown and enable Scene World / Scene Lights if available. Material Preview often uses its own preview lighting, so it can show reflections that are not the final render environment.\\n\\n"
        "Red specks note:\\n"
        "Red/colored edge specks in Rendered view are usually caused by overlapping transparent preview objects, z-fighting, or bright emissive/glossy artifacts at edges. This pass hides material swatches and blocky shoe accent cubes and softens wardrobe guide materials to reduce that effect.\\n\\n"
        f"Imported clothing candidates this run: {json.dumps(imported_groups, indent=2)}\\n",
        encoding="utf-8"
    )
    log(f"[notes] wrote {notes}")

def render_review(f2_bounds, imported_groups):
    col=replace_collection("HERO_REVIEW_CAMERAS")
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False

    c=center(f2_bounds)
    sx,sy,sz=dims(f2_bounds)
    specs=[
        ("HERO_CAM_WardrobeCleanupFront",(c.x+sx*1.45,c.y-sz*2.2,c.z+sz*0.45),Vector((c.x,c.y,c.z+sz*0.1)),70,"01_WardrobeCleanupFront.png"),
        ("HERO_CAM_ShoeGraphicCleanup",(c.x+sx*0.85,c.y-sz*1.10,f2_bounds[4]+sz*0.25),Vector((c.x,c.y,f2_bounds[4]+sz*0.09)),75,"02_ShoeGraphicCleanup.png"),
        ("HERO_CAM_ImportedClothingCandidates",(c.x+sx*3.2,c.y-sz*2.7,c.z+sz*0.65),Vector((c.x+sx*1.1,c.y+sy*0.8,c.z)),55,"03_ImportedClothingCandidates.png"),
    ]
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    for name,loc,aim,lens,filename in specs:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.location=loc
        cam.data.lens=lens
        look_at(cam,aim)
        col.objects.link(cam)
        scene.camera=cam
        scene.render.filepath=str(OUT_DIR/filename)
        bpy.ops.render.render(write_still=True)
        log(f"[render] {filename}")

    current=project_root()/"renders"/"current_review"
    current.mkdir(parents=True,exist_ok=True)
    for p in current.glob("*"):
        if p.is_file():
            p.unlink()
    for p in OUT_DIR.glob("*"):
        if p.is_file():
            (current/p.name).write_bytes(p.read_bytes())

def write_status(imported_groups):
    status={
        "lights":"LOCKED - no lights/world/car/storefront layout modified",
        "material_boxes":"HERO_CHARACTER_MATERIAL_GUIDES hidden; material swatch boxes hidden",
        "shoe_cubes":"blocky flame accent cubes hidden; subtle curved shoe graphic guides added",
        "wardrobe_guides":"current hoodie/jeans/shoe guides preserved as reference",
        "clothing_asset_folders":str(CLOTHING_ASSET_ROOT),
        "imported_clothing_candidates":imported_groups,
        "reflection_note":"Material Preview may use preview studio lighting; use Rendered mode or enable Scene World/Scene Lights to inspect actual HDRI/world reflections.",
    }
    (OUT_DIR/CLEANUP_STATUS).write_text(json.dumps(status,indent=2),encoding="utf-8")

def export_manifest():
    script=project_root()/"blender"/"scripts"/"export_project_layout_and_scene.py"
    if script.exists():
        ns={"__file__":str(script),"__name__":"__main__"}
        exec(script.read_text(encoding="utf-8"), ns)

def main():
    reset_log()
    preserve_locked_scene()
    f2, f2_bounds=get_f2_bounds()
    hide_material_boxes_and_blocky_accents(f2_bounds)
    soften_wardrobe_preview_materials()
    ensure_clothing_asset_folders()
    imported=import_clothing_assets(f2_bounds)
    write_manual_notes(imported)
    render_review(f2_bounds, imported)
    write_status(imported)
    export_manifest()
    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log(f"[save] {out}")

if __name__=="__main__":
    try:
        main()
    except Exception:
        OUT_DIR.mkdir(parents=True,exist_ok=True)
        with (OUT_DIR/"WardrobeCleanupAssetIntake_FATAL_ERROR.txt").open("w",encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
