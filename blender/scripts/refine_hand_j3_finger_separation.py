import sys, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from common import project_root, ensure_collection

SOURCE_NAME = "HANDREFINE_J2B_Working"
OUT_NAME = "HANDREFINE_J3_Working"
OUT_COLLECTION = "CHAR_HandRefine_J3"
CAM_COLLECTION = "DIAG_HandRefine_J3_Cameras"
LIGHT_COLLECTION = "DIAG_HandRefine_J3_Lights"

# Hand/arm orientation derived from previous diagnostics.
X_TIP_END   = -1.50
X_FINGER_END= -1.31
X_PALM_END  = -1.05
X_WRIST_END = -0.88
Y_CENTER    = 0.085
Z_CENTER    = 1.445

# Finger lobe centers and valleys in local vertical silhouette space.
LOBE_CENTERS = [1.525, 1.455, 1.385]
VALLEY_CENTERS = [1.490, 1.420]

def smoothstep(a,b,x):
    if a == b:
        return 0.0
    t=max(0.0, min(1.0, (x-a)/(b-a)))
    return t*t*(3-2*t)

def gaussian(x, mu, sigma):
    return math.exp(-((x-mu)**2)/(2*sigma*sigma))

def replace_collection(name):
    col=bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    return ensure_collection(name)

def world_bounds(obj):
    coords=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

def pick_source():
    obj=bpy.data.objects.get(SOURCE_NAME)
    if not obj or obj.type!='MESH':
        raise RuntimeError("HANDREFINE_J2B_Working not found. Run J2B first.")
    return obj

def duplicate_source(source):
    col=replace_collection(OUT_COLLECTION)
    dup=source.copy()
    dup.data=source.data.copy()
    dup.name=OUT_NAME
    col.objects.link(dup)
    source.hide_viewport=True
    source.hide_render=True
    dup.hide_viewport=False
    dup.hide_render=False
    return dup

def target_half_y(x):
    if x <= X_FINGER_END:
        t=smoothstep(X_TIP_END, X_FINGER_END, x)
        return 0.17 + 0.05*t
    if x <= X_PALM_END:
        t=smoothstep(X_FINGER_END, X_PALM_END, x)
        return 0.22 + 0.02*math.sin(math.pi*t)
    t=smoothstep(X_PALM_END, X_WRIST_END, x)
    return 0.22 - 0.02*t

def target_half_z(x):
    if x <= X_FINGER_END:
        t=smoothstep(X_TIP_END, X_FINGER_END, x)
        return 0.115 + 0.045*t
    if x <= X_PALM_END:
        t=smoothstep(X_FINGER_END, X_PALM_END, x)
        return 0.16 + 0.02*math.sin(math.pi*t)
    t=smoothstep(X_PALM_END, X_WRIST_END, x)
    return 0.17 - 0.01*t

def reshape(obj):
    mw=obj.matrix_world
    imw=mw.inverted()

    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    moved=0
    valley_hits=0
    lobe_hits=0
    side_groove_hits=0
    compact_hits=0

    for v in bm.verts:
        world=mw @ v.co
        x,y,z = world.x, world.y, world.z

        in_hand = (X_TIP_END-0.03 <= x <= X_WRIST_END and 0.98 <= z <= 1.82 and -0.60 <= y <= 0.72)
        if not in_hand:
            continue

        # keep wrist mostly stable
        hand_weight = 1.0 - smoothstep(X_PALM_END, X_WRIST_END, x)
        if x <= X_PALM_END:
            hand_weight = 1.0

        dy=y-Y_CENTER
        dz=z-Z_CENTER

        # Slight further compaction to keep the hand proportionate.
        hy=target_half_y(x)
        hz=target_half_z(x)

        if abs(dy) > hy:
            excess=abs(dy)-hy
            y -= math.copysign(excess*0.82*hand_weight, dy)
            compact_hits += 1
        if abs(dz) > hz:
            excess=abs(dz)-hz
            z -= math.copysign(excess*0.75*hand_weight, dz)
            compact_hits += 1

        # Stronger three-finger lobe / valley sculpting at the tip silhouette.
        tip_weight = 1.0 - smoothstep(X_TIP_END, X_FINGER_END+0.02, x)
        if tip_weight > 0:
            lobes = [(c, gaussian(z,c,0.022)) for c in LOBE_CENTERS]
            valleys = [(c, gaussian(z,c,0.016)) for c in VALLEY_CENTERS]
            lobe_sum = sum(g for _,g in lobes)
            valley_sum = sum(g for _,g in valleys)

            # Valleys recede more, lobes project slightly.
            x += (-0.034*lobe_sum + 0.044*valley_sum) * tip_weight

            # Carve side grooves so the separations read from front/back too.
            side_strength = smoothstep(0.04, 0.18, abs(dy))
            y += math.copysign(0.026*valley_sum*side_strength*tip_weight, dy)

            # Slight vertical shaping to round the three lobes individually.
            for c,g in lobes:
                z += (z-c) * (-0.030*g*tip_weight)
                if g > 0.18:
                    lobe_hits += 1
            for c,g in valleys:
                # pull valley center toward midpoint between neighboring lobes
                z += (Z_CENTER - z) * (0.012*g*tip_weight)
                if g > 0.18:
                    valley_hits += 1
            if valley_sum > 0.05 and side_strength > 0.3:
                side_groove_hits += 1

        # Separate the hand from the underside thumb/palm lump a bit more.
        thumb_zone = (X_FINGER_END-0.02 <= x <= X_PALM_END+0.04 and z < 1.36)
        if thumb_zone:
            z += (1.365 - z) * 0.42
            # also trim lateral spread in the lower part
            if abs(dy) > 0.18:
                y -= math.copysign((abs(dy)-0.18)*0.35, dy)

        # Better front edge break between finger band and palm.
        if X_FINGER_END-0.02 <= x <= X_FINGER_END+0.05:
            t = 1.0 - abs((x - X_FINGER_END)/0.07)
            if t > 0:
                x += 0.010*t
                z += (z-Z_CENTER) * (-0.015*t)

        # Keep the wrist a little slimmer for sleeve fit.
        if X_PALM_END <= x <= X_WRIST_END:
            wrist_t = smoothstep(X_PALM_END, X_WRIST_END, x)
            y -= dy * 0.04 * wrist_t
            z -= dz * 0.03 * wrist_t

        world = Vector((x,y,z))
        v.co = imw @ world
        moved += 1

    # Very light hand-only smoothing after carving so shapes remain readable.
    hand_verts=[]
    for v in bm.verts:
        world=mw @ v.co
        if X_TIP_END-0.03 <= world.x <= X_PALM_END+0.02 and 1.0 <= world.z <= 1.82:
            hand_verts.append(v)

    if hand_verts:
        bmesh.ops.smooth_vert(
            bm, verts=hand_verts, factor=0.055,
            use_axis_x=False, use_axis_y=True, use_axis_z=True
        )

    bm.normal_update()
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()

    return {
        "vertices_moved": moved,
        "valley_hits": valley_hits,
        "lobe_hits": lobe_hits,
        "side_groove_hits": side_groove_hits,
        "compact_hits": compact_hits,
    }

def look_at(obj,target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def clear_and_get_collection(name):
    col=ensure_collection(name)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    return col

def render_views(target):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.image_settings.file_format='PNG'
    scene.render.resolution_percentage=100
    scene.world.color=(0.025,0.025,0.03)

    states={}
    for obj in bpy.context.scene.objects:
        states[obj.name]=obj.hide_render
        if obj.type == 'MESH':
            obj.hide_render=(obj != target)
    target.hide_render=False

    cam_col=replace_collection(CAM_COLLECTION)
    light_col=clear_and_get_collection(LIGHT_COLLECTION)

    hand_focus=Vector((-1.22, Y_CENTER, Z_CENTER))
    arm_focus=Vector((-0.95, 0.08, 1.48))

    def area(name, loc, energy, size, aim):
        data=bpy.data.lights.new(name+"_Data", type='AREA')
        data.energy=energy
        data.shape='DISK'
        data.size=size
        obj=bpy.data.objects.new(name, data)
        obj.location=loc
        look_at(obj, aim)
        light_col.objects.link(obj)
        return obj

    area("J3_Key", (-2.4,-3.0,2.4), 680, 2.1, hand_focus)
    area("J3_Fill", (-0.7,-1.4,1.9), 140, 3.2, hand_focus)
    area("J3_Rim", (-1.0,2.9,2.1), 260, 2.0, hand_focus)

    out_dir=project_root()/"renders"/"hand_refine_j3"
    out_dir.mkdir(parents=True, exist_ok=True)

    views=[
        ("J3_Hand_Frontish", (-1.58,-2.18,1.47), hand_focus, 78, "J3_Hand_Frontish.png"),
        ("J3_Hand_Backish", (-1.58,2.18,1.47), hand_focus, 78, "J3_Hand_Backish.png"),
        ("J3_Hand_Side", (-1.93,0.08,1.47), hand_focus, 74, "J3_Hand_Side.png"),
        ("J3_Arm_ThreeQuarter", (-0.96,-3.4,1.76), arm_focus, 68, "J3_Arm_ThreeQuarter.png"),
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
        print(f"[Step01M-J3] Rendered {out_dir/fn}")

    for name,state in states.items():
        obj=bpy.data.objects.get(name)
        if obj:
            obj.hide_render=state

def write_report(stats):
    out_dir=project_root()/"renders"/"hand_refine_j3"
    out_dir.mkdir(parents=True, exist_ok=True)
    path=out_dir/"J3_FingerSeparation_Report.txt"
    path.write_text(
        "Step01M-J3 Finger Separation Completion Pass\n"
        "===========================================\n\n"
        f"Vertices moved: {stats['vertices_moved']}\n"
        f"Lobe-zone hits: {stats['lobe_hits']}\n"
        f"Valley-zone hits: {stats['valley_hits']}\n"
        f"Side-groove hits: {stats['side_groove_hits']}\n"
        f"Compaction events: {stats['compact_hits']}\n\n"
        "Goals:\n"
        "- visibly separated finger lobes\n"
        "- stronger valleys between fingers\n"
        "- better readability from front/back as well as silhouette\n"
        "- keep wrist compact for future hoodie sleeve fit\n"
        "- preserve the improved J2B hand scale\n",
        encoding='utf-8'
    )

def main():
    source=pick_source()
    target=duplicate_source(source)
    stats=reshape(target)
    render_views(target)
    write_report(stats)

    out=project_root()/"blender"/"sackboy_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[Step01M-J3] Saved: {out}")

if __name__=="__main__":
    main()
