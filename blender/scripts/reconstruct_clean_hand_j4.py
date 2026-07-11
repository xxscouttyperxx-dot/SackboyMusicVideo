import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_NAME = "HANDREFINE_J2B_Working"
BODY_NAME = "HANDREFINE_J4_BodyCore"
HAND_NAME = "HANDREFINE_J4_CleanHand"
OUT_COLLECTION = "CHAR_HandRefine_J4"
META_NAME = "J4_HandMeta"
CAM_COLLECTION = "DIAG_HandRefine_J4_Cameras"
LIGHT_COLLECTION = "DIAG_HandRefine_J4_Lights"

# Geometry coordinates measured from the J2A/J2B arm-hand region.
WRIST_X0 = -0.88
PALM_X0 = -1.06
HAND_CENTER_Y = 0.085
HAND_CENTER_Z = 1.445

def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def world_bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def look_at(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def duplicate_body_core(source, col):
    dup=source.copy()
    dup.data=source.data.copy()
    dup.name=BODY_NAME
    col.objects.link(dup)
    source.hide_viewport=True
    source.hide_render=True
    dup.hide_viewport=False
    dup.hide_render=False
    return dup

def bury_old_hand(body):
    """Collapse the old distal hand inward so the new clean hand visually replaces it."""
    mw=body.matrix_world
    imw=mw.inverted()

    bm=bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()

    moved=0
    for v in bm.verts:
        p=mw @ v.co
        x,y,z=p.x,p.y,p.z

        if x > PALM_X0 + 0.04:
            continue
        if not (-0.65 <= y <= 0.75 and 1.00 <= z <= 1.85):
            continue

        # Weight increases toward the old fingertips.
        t=max(0.0,min(1.0,(PALM_X0+0.04-x)/0.48))

        # Pull distal geometry back toward palm/wrist center.
        target_x=PALM_X0 + 0.035
        x = x*(1.0-0.78*t) + target_x*(0.78*t)
        y = HAND_CENTER_Y + (y-HAND_CENTER_Y)*(1.0-0.78*t)
        z = HAND_CENTER_Z + (z-HAND_CENTER_Z)*(1.0-0.72*t)

        v.co=imw @ Vector((x,y,z))
        moved += 1

    bm.normal_update()
    bm.to_mesh(body.data)
    body.data.update()
    bm.free()
    print(f"[Step01M-J4] Buried {moved} old-hand vertices inside replacement volume.")

def add_meta_element(meta_obj, co, radius, stiffness=2.0):
    elem=meta_obj.data.elements.new()
    elem.co=co
    elem.radius=radius
    elem.stiffness=stiffness
    return elem

def build_clean_hand(col):
    meta_data=bpy.data.metaballs.new(META_NAME+"_Data")
    meta_data.resolution=0.025
    meta_data.render_resolution=0.018
    meta_data.threshold=0.62

    meta_obj=bpy.data.objects.new(META_NAME, meta_data)
    col.objects.link(meta_obj)

    # Wrist / connector chain.
    wrist_points=[
        (-0.92, HAND_CENTER_Y, HAND_CENTER_Z, 0.105),
        (-1.00, HAND_CENTER_Y, HAND_CENTER_Z, 0.112),
        (-1.08, HAND_CENTER_Y, HAND_CENTER_Z, 0.118),
    ]
    for x,y,z,r in wrist_points:
        add_meta_element(meta_obj,(x,y,z),r)

    # Compact rounded palm.
    palm_points=[
        (-1.12, HAND_CENTER_Y, HAND_CENTER_Z, 0.145),
        (-1.18, HAND_CENTER_Y, HAND_CENTER_Z, 0.138),
        (-1.14, HAND_CENTER_Y+0.045, HAND_CENTER_Z, 0.115),
        (-1.14, HAND_CENTER_Y-0.045, HAND_CENTER_Z, 0.115),
    ]
    for x,y,z,r in palm_points:
        add_meta_element(meta_obj,(x,y,z),r)

    # Three rounded fingers. Each is a short capsule made from overlapping spheres.
    finger_specs=[
        (1.515, 0.052, 0.000),  # upper finger
        (1.445, 0.056, 0.000),  # middle finger
        (1.375, 0.052, 0.000),  # lower finger
    ]
    for zc,rad,yoff in finger_specs:
        for x in (-1.22,-1.29,-1.36,-1.42):
            taper=1.0 - 0.10*max(0.0,(-1.36-x)/0.06)
            add_meta_element(meta_obj,(x,HAND_CENTER_Y+yoff,zc),rad*taper,2.2)

    # Small rounded thumb below palm, not drooping.
    thumb_points=[
        (-1.16, HAND_CENTER_Y-0.055, 1.345, 0.060),
        (-1.22, HAND_CENTER_Y-0.060, 1.325, 0.055),
    ]
    for x,y,z,r in thumb_points:
        add_meta_element(meta_obj,(x,y,z),r,2.1)

    # Convert metaball union to mesh.
    bpy.context.view_layer.objects.active=meta_obj
    meta_obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    hand=bpy.context.object
    hand.name=HAND_NAME

    # Smooth shading.
    for poly in hand.data.polygons:
        poly.use_smooth=True

    # Gentle corrective smooth modifier.
    smooth=hand.modifiers.new(name="J4_CorrectiveSmooth", type='CORRECTIVE_SMOOTH')
    smooth.factor=0.22
    smooth.iterations=4

    # Small subdivision for roundness.
    sub=hand.modifiers.new(name="J4_Subdivision", type='SUBSURF')
    sub.levels=1
    sub.render_levels=1

    print("[Step01M-J4] Built clean rounded three-finger hand replacement.")
    return hand

def make_material(obj):
    mat=bpy.data.materials.get("MAT_J4_HandDiagnostic")
    if mat is None:
        mat=bpy.data.materials.new("MAT_J4_HandDiagnostic")
        mat.diffuse_color=(0.72,0.72,0.72,1)
        mat.roughness=0.6
    obj.data.materials.clear()
    obj.data.materials.append(mat)

def render_views(body, hand):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.image_settings.file_format='PNG'
    scene.render.resolution_percentage=100
    scene.world.color=(0.02,0.02,0.025)

    states={}
    keep={body.name,hand.name}
    for obj in bpy.context.scene.objects:
        states[obj.name]=obj.hide_render
        if obj.type=='MESH':
            obj.hide_render=obj.name not in keep
    body.hide_render=False
    hand.hide_render=False

    cam_col=replace_collection(CAM_COLLECTION)
    light_col=replace_collection(LIGHT_COLLECTION)

    focus=Vector((-1.20,HAND_CENTER_Y,HAND_CENTER_Z))
    arm_focus=Vector((-0.95,HAND_CENTER_Y,1.47))

    def area(name,loc,energy,size,aim):
        data=bpy.data.lights.new(name+"_Data",type='AREA')
        data.energy=energy
        data.shape='DISK'
        data.size=size
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        look_at(obj,aim)
        light_col.objects.link(obj)

    area("J4_Key",(-2.4,-3.0,2.35),700,2.2,focus)
    area("J4_Fill",(-0.6,-1.2,1.8),150,3.2,focus)
    area("J4_Rim",(-1.0,2.8,2.1),280,2.0,focus)

    out_dir=project_root()/"renders"/"hand_refine_j4"
    out_dir.mkdir(parents=True,exist_ok=True)

    views=[
        ("J4_Hand_Frontish",(-1.63,-2.22,1.46),focus,80,"J4_Hand_Frontish.png"),
        ("J4_Hand_Backish",(-1.63,2.22,1.46),focus,80,"J4_Hand_Backish.png"),
        ("J4_Hand_Side",(-1.95,HAND_CENTER_Y,1.46),focus,76,"J4_Hand_Side.png"),
        ("J4_Arm_ThreeQuarter",(-0.92,-3.4,1.76),arm_focus,68,"J4_Arm_ThreeQuarter.png"),
    ]

    for name,loc,aim,lens,fn in views:
        data=bpy.data.cameras.new(name+"_Data")
        cam=bpy.data.objects.new(name,data)
        cam.data.lens=lens
        cam.location=loc
        look_at(cam,aim)
        cam_col.objects.link(cam)
        scene.camera=cam
        scene.render.resolution_x=1280
        scene.render.resolution_y=1280
        scene.render.filepath=str(out_dir/fn)
        bpy.ops.render.render(write_still=True)
        print(f"[Step01M-J4] Rendered {out_dir/fn}")

    for name,state in states.items():
        obj=bpy.data.objects.get(name)
        if obj:
            obj.hide_render=state

def write_report(body, hand):
    out_dir=project_root()/"renders"/"hand_refine_j4"
    out_dir.mkdir(parents=True,exist_ok=True)

    bb=world_bounds(hand)
    report=out_dir/"J4_CleanHand_Report.txt"
    report.write_text(
        "Step01M-J4 Clean Hand Reconstruction\n"
        "====================================\n\n"
        "Strategy:\n"
        "- preserved J2B source\n"
        "- created duplicate body core\n"
        "- collapsed old distal hand inside replacement volume\n"
        "- built a new clean rounded hand from metaball geometry\n"
        "- kept new hand as a separate object for future rigging/mirroring flexibility\n\n"
        f"Body object: {body.name}\n"
        f"Hand object: {hand.name}\n"
        f"Hand vertices: {len(hand.data.vertices)}\n"
        f"Hand polygons: {len(hand.data.polygons)}\n"
        f"Hand bounds: {bb}\n\n"
        "Design target:\n"
        "- three clearly rounded finger forms\n"
        "- compact palm\n"
        "- small rounded thumb\n"
        "- smooth sleeve-friendly wrist connector\n"
        "- no sharp carved finger tips\n",
        encoding='utf-8'
    )

def main():
    source=bpy.data.objects.get(SOURCE_NAME)
    if not source or source.type!='MESH':
        raise RuntimeError("HANDREFINE_J2B_Working not found. Run J2B first.")

    col=replace_collection(OUT_COLLECTION)
    body=duplicate_body_core(source,col)
    bury_old_hand(body)
    hand=build_clean_hand(col)
    make_material(hand)
    render_views(body,hand)
    write_report(body,hand)

    scene=bpy.context.scene
    scene["active_character_body"]=BODY_NAME
    scene["active_character_left_hand"]=HAND_NAME
    scene["hand_refine_version"]="Step01M-J4"

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J4] Saved clean-hand reconstruction branch: {out}")

if __name__=="__main__":
    main()
