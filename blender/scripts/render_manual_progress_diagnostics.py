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

EXCLUDED_COLLECTION_PREFIXES = ("ENV_", "LGT_", "CAM_", "DIAG_", "MESHY_", "BASE_")
EXCLUDED_COLLECTION_NAMES = {
    "CHAR_SackDoll",
    "CHAR_Meshy_Working",
    "CHAR_Meshy_Isolated",
    "CHAR_Meshy_LeftCandidate_Working",
    "CHAR_Meshy_LeftCandidate_Repaired",
    "CHAR_Meshy_LeftCandidate_Refined",
    "CHAR_Meshy_LeftCandidate_Structural",
    "CHAR_Meshy_LeftCandidate_HandCompact",
}

def visible_in_viewlayer(obj):
    try:
        return obj.visible_get()
    except Exception:
        return not obj.hide_viewport

def collection_names(obj):
    return [c.name for c in obj.users_collection]

def excluded(obj):
    names = collection_names(obj)
    for name in names:
        if name in EXCLUDED_COLLECTION_NAMES:
            return True
        if any(name.startswith(p) for p in EXCLUDED_COLLECTION_PREFIXES):
            return True
    lowered = obj.name.lower()
    return any(t in lowered for t in ("floor", "asphalt", "plaza", "glass", "diag_", "camera", "light"))

def world_bounds(obj):
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def volume(obj):
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(obj)
    return max((xmax-xmin)*(ymax-ymin)*(zmax-zmin), 0.0)

def choose_target():
    active = bpy.context.view_layer.objects.active
    if active and active.type == 'MESH' and visible_in_viewlayer(active) and not excluded(active):
        print(f"[Step01M-I] Using active visible mesh: {active.name}")
        return active

    manual = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not visible_in_viewlayer(obj):
            continue
        blob = " ".join([obj.name] + collection_names(obj)).lower()
        if "manual" in blob and not excluded(obj):
            manual.append(obj)
    if manual:
        target = max(manual, key=volume)
        print(f"[Step01M-I] Using largest visible manual mesh: {target.name}")
        return target

    candidates = [
        obj for obj in bpy.context.scene.objects
        if obj.type == 'MESH' and visible_in_viewlayer(obj) and not excluded(obj)
    ]
    if not candidates:
        raise RuntimeError("No suitable visible manual mesh found. Select it and save the .blend, then rerun.")
    target = max(candidates, key=volume)
    print(f"[Step01M-I] Fallback selected largest visible mesh: {target.name}")
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
    print(f"[Step01M-I] Hidden checkpoint created: {dup.name}")

def write_inventory(target):
    out_dir = project_root() / "renders" / "manual_progress_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "Manual_progress_inventory.txt"
    xmin,xmax,ymin,ymax,zmin,zmax = world_bounds(target)
    mesh = target.data
    lines = [
        "Manual Progress Inventory\n",
        "=========================\n\n",
        f"Target object: {target.name}\n",
        f"Collections: {', '.join(collection_names(target))}\n",
        f"Vertices: {len(mesh.vertices)}\n",
        f"Edges: {len(mesh.edges)}\n",
        f"Polygons: {len(mesh.polygons)}\n",
        f"Bounds X: {xmin:.6f} .. {xmax:.6f}\n",
        f"Bounds Y: {ymin:.6f} .. {ymax:.6f}\n",
        f"Bounds Z: {zmin:.6f} .. {zmax:.6f}\n",
        f"Dimensions: {(xmax-xmin):.6f} x {(ymax-ymin):.6f} x {(zmax-zmin):.6f}\n",
        "\nVisible mesh candidates considered:\n",
    ]
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and visible_in_viewlayer(obj) and not excluded(obj):
            lines.append(f"- {obj.name} | collections={collection_names(obj)} | volume={volume(obj):.6f}\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"[Step01M-I] Wrote inventory: {path}")

def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def setup_studio():
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world.color=(0.92,0.92,0.94)

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
    return cam_col

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
    print(f"[Step01M-I] Rendered {path}")

def main():
    target=choose_target()
    make_checkpoint(target)
    write_inventory(target)

    xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(target)
    center=Vector(((xmin+xmax)/2,(ymin+ymax)/2,(zmin+zmax)/2))
    h=zmax-zmin; w=xmax-xmin; d=max(5.0,h*2.0)

    cam_col=setup_studio()
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
    render_camera(create_camera(cam_col,"DIAG_Manual_FaceCloseup",(0,-d*.58,zmin+h*.83),face_target,65),"Manual_FaceCloseup.png")

    hand_target=Vector((xmin+w*.085,ymin+(ymax-ymin)*0.28,zmin+h*.57))
    render_camera(create_camera(cam_col,"DIAG_Manual_LeftHandCloseup",(xmin-w*.05,-d*.50,zmin+h*.58),hand_target,65),"Manual_LeftHandCloseup.png")

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-I] Saved diagnostic cameras and checkpoint: {out}")

if __name__=="__main__":
    main()
