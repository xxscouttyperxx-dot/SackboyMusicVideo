import sys
from pathlib import Path
import bpy
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

CAM_COLLECTION = "DIAG_ManualProgress_Cameras"
CHECKPOINT_COLLECTION = "CHECKPOINT_ManualProgress"
STUDIO_COLLECTION = "DIAG_ManualProgress_Studio"

HARD_EXCLUDE_NAME_TOKENS = (
    "floor", "asphalt", "plaza", "glass", "parking", "lamp", "light",
    "camera", "diag_", "checkpoint_", "mouth_cut_guide"
)

def visible_in_viewlayer(obj):
    try:
        return obj.visible_get()
    except Exception:
        return not obj.hide_viewport

def collection_names(obj):
    return [c.name for c in obj.users_collection]

def world_bounds(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def dimensions(obj):
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(obj)
    return xmax-xmin, ymax-ymin, zmax-zmin

def volume(obj):
    dx,dy,dz = dimensions(obj)
    return max(dx*dy*dz, 0.0)

def hard_excluded(obj):
    blob = " ".join([obj.name] + collection_names(obj)).lower()
    return any(token in blob for token in HARD_EXCLUDE_NAME_TOKENS)

def score_candidate(obj):
    dx,dy,dz = dimensions(obj)
    if dz <= 0:
        return -1e9

    blob = " ".join([obj.name] + collection_names(obj)).lower()
    score = volume(obj)

    # Strong preference for user's manual duplicate/checkpoint naming.
    if "manual" in blob:
        score *= 1000.0

    # Prefer character-like naming, but do NOT exclude older collections.
    for token in ("meshy", "sack", "character", "char_", "cleanup"):
        if token in blob:
            score *= 2.0

    # Penalize flat environmental geometry.
    flatness = dz / max(dx, dy, 1e-6)
    if flatness < 0.2:
        score *= 0.01

    return score

def choose_target():
    # 1) Explicit saved active object, even if it lives inside an older refined collection.
    active = bpy.context.view_layer.objects.active
    if active and active.type == 'MESH' and visible_in_viewlayer(active) and not hard_excluded(active):
        print(f"[Step01M-I2] Using active visible mesh: {active.name}")
        return active

    # 2) Any visible mesh whose object or collection name contains "manual".
    manual = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not visible_in_viewlayer(obj) or hard_excluded(obj):
            continue
        blob = " ".join([obj.name] + collection_names(obj)).lower()
        if "manual" in blob:
            manual.append(obj)
    if manual:
        target = max(manual, key=score_candidate)
        print(f"[Step01M-I2] Using best visible manual mesh: {target.name}")
        return target

    # 3) Fallback: score every visible non-environment mesh.
    candidates = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not visible_in_viewlayer(obj):
            continue
        if hard_excluded(obj):
            continue
        candidates.append(obj)

    if not candidates:
        raise RuntimeError(
            "No visible mesh candidate found. Make the manual character visible, "
            "select it, save the .blend, and rerun."
        )

    ranked = sorted(candidates, key=score_candidate, reverse=True)
    target = ranked[0]
    print(f"[Step01M-I2] Fallback selected: {target.name}")
    print("[Step01M-I2] Top candidates:")
    for obj in ranked[:8]:
        print(
            f"  {obj.name} | collections={collection_names(obj)} | "
            f"score={score_candidate(obj):.6f} | dims={dimensions(obj)}"
        )
    return target

def replace_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def make_checkpoint(target):
    col = replace_collection(CHECKPOINT_COLLECTION)
    dup = target.copy()
    if target.data:
        dup.data = target.data.copy()
    col.objects.link(dup)
    dup.name = "CHECKPOINT_" + target.name
    dup.hide_viewport = True
    dup.hide_render = True
    print(f"[Step01M-I2] Hidden checkpoint created: {dup.name}")

def write_inventory(target):
    out_dir = project_root() / "renders" / "manual_progress_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "Manual_progress_inventory.txt"

    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(target)
    mesh = target.data

    lines = [
        "Manual Progress Inventory\n",
        "=========================\n\n",
        f"TARGET OBJECT: {target.name}\n",
        f"TARGET COLLECTIONS: {', '.join(collection_names(target))}\n",
        f"Vertices: {len(mesh.vertices)}\n",
        f"Edges: {len(mesh.edges)}\n",
        f"Polygons: {len(mesh.polygons)}\n",
        f"Bounds X: {xmin:.6f} .. {xmax:.6f}\n",
        f"Bounds Y: {ymin:.6f} .. {ymax:.6f}\n",
        f"Bounds Z: {zmin:.6f} .. {zmax:.6f}\n",
        f"Dimensions: {(xmax-xmin):.6f} x {(ymax-ymin):.6f} x {(zmax-zmin):.6f}\n",
        "\nALL VISIBLE MESH CANDIDATES:\n",
    ]

    ranked = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and visible_in_viewlayer(obj):
            ranked.append(obj)

    for obj in sorted(ranked, key=score_candidate, reverse=True):
        lines.append(
            f"- {obj.name} | collections={collection_names(obj)} | "
            f"excluded={hard_excluded(obj)} | score={score_candidate(obj):.6f} | "
            f"dims={dimensions(obj)}\n"
        )

    path.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-I2] Wrote inventory: {path}")

def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def setup_studio(target):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world.color=(0.92,0.92,0.94)

    # Hide every mesh except target during diagnostics, but preserve original hide states.
    visibility_state = {}
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            visibility_state[obj.name] = (obj.hide_viewport, obj.hide_render)
            if obj != target:
                obj.hide_render = True

    target.hide_render = False

    cam_col=replace_collection(CAM_COLLECTION)
    studio=replace_collection(STUDIO_COLLECTION)

    bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
    floor=bpy.context.object
    floor.name="MANUAL_DIAG_Floor"
    floor.scale=(8,8,8)
    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    studio.objects.link(floor)

    mat=bpy.data.materials.get("MAT_ManualDiagFloor") or bpy.data.materials.new("MAT_ManualDiagFloor")
    mat.diffuse_color=(0.95,0.95,0.96,1)
    floor.data.materials.clear()
    floor.data.materials.append(mat)

    def area(name,loc,energy,size):
        data=bpy.data.lights.new(name=name+"_Data",type='AREA')
        data.energy=energy; data.shape='DISK'; data.size=size
        obj=bpy.data.objects.new(name,data)
        obj.location=loc
        studio.objects.link(obj)

    area("MANUAL_DIAG_Key",(4,-4,5),1900,3.5)
    area("MANUAL_DIAG_Fill",(-4,-2,3),900,4.0)
    area("MANUAL_DIAG_Rim",(0,4,4),1000,3.5)

    return cam_col, visibility_state

def restore_visibility(state):
    for name, (hide_viewport, hide_render) in state.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_viewport = hide_viewport
            obj.hide_render = hide_render

def create_camera(cam_col,name,loc,target,lens=55):
    data=bpy.data.cameras.new(name+"_Data")
    cam=bpy.data.objects.new(name,data)
    data.lens=lens
    cam.location=loc
    look_at(cam,target)
    cam_col.objects.link(cam)
    return cam

def render_camera(cam,filename):
    scene=bpy.context.scene
    scene.render.resolution_x=1280
    scene.render.resolution_y=1280
    scene.camera=cam
    out_dir=project_root()/"renders"/"manual_progress_diagnostics"
    out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/filename
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[Step01M-I2] Rendered {path}")

def main():
    target=choose_target()
    make_checkpoint(target)
    write_inventory(target)

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h=zmax-zmin; w=xmax-xmin; d=max(5.0,h*2.0)

    cam_col, vis_state = setup_studio(target)

    views=[
        ("DIAG_Manual_Front",(0,-d,center.z),"Manual_Front.png"),
        ("DIAG_Manual_Side",(d,0,center.z),"Manual_Side.png"),
        ("DIAG_Manual_Back",(0,d,center.z),"Manual_Back.png"),
        ("DIAG_Manual_ThreeQuarterFront",(d*.78,-d*.78,center.z+.15),"Manual_ThreeQuarterFront.png"),
        ("DIAG_Manual_ThreeQuarterRear",(-d*.78,d*.78,center.z+.15),"Manual_ThreeQuarterRear.png"),
    ]
    for name,loc,fn in views:
        render_camera(create_camera(cam_col,name,loc,center),fn)

    face_target=Vector((center.x,ymin+(ymax-ymin)*0.12,zmin+h*0.82))
    render_camera(
        create_camera(cam_col,"DIAG_Manual_FaceCloseup",(0,-d*.58,zmin+h*.83),face_target,65),
        "Manual_FaceCloseup.png"
    )

    hand_target=Vector((xmin+w*.085,ymin+(ymax-ymin)*0.28,zmin+h*.57))
    render_camera(
        create_camera(cam_col,"DIAG_Manual_LeftHandCloseup",(xmin-w*.05,-d*.50,zmin+h*.58),hand_target,65),
        "Manual_LeftHandCloseup.png"
    )

    restore_visibility(vis_state)

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-I2] Saved diagnostic cameras and checkpoint: {out}")

if __name__=="__main__":
    main()
