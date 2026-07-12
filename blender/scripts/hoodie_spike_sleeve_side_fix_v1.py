import json, traceback
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'renders' / 'hoodie_spike_sleeve_side_fix_v1'
REP = ROOT / 'reports' / 'hoodie_spike_sleeve_side_fix_v1'
CUR = ROOT / 'renders' / 'current_review'
AUD = ROOT / 'reports' / 'project_workflow_audit'

HERO_NAME = 'F2'
HOODIE_NAME = 'SACKBOY_Hoodie_Main'
FALLBACK_HOODIE_NAMES = ['SACKBOY_Hoodie_Main', 'Apricot Pullover Hoodie']
PREV_HOODIE_KEYS = [
    'HOODIEFIT_BowlRimRefine_v1',
    'HOODIEFIT_BowlRidgePolish_v1',
    'HOODIEFIT_TopArtifactFix_v1',
    'HOODIEFIT_RimCrownContain_v1',
    'HOODIEFIT_CrownSmoothExpand_v1',
    'HOODIEFIT_CrownSleeveTaper_v1',
    'HOODIEFIT_NarrowSackboy_v1',
]
NEW_HOODIE_KEY = 'HOODIEFIT_SpikeSleeveSideFix_v1'
UNDERGLOW_NAME = 'HERO_CyanUnderglow_Area'
UNDERGLOW_LOCK_LOC = (-1.522953, 5.177517, 0.075276)


def log(msg):
    print(msg)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'HoodieSpikeSleeveSideFix_report.txt').open('a', encoding='utf-8') as f:
        f.write(msg + '\n')


def reset():
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    CUR.mkdir(parents=True, exist_ok=True)
    AUD.mkdir(parents=True, exist_ok=True)
    (OUT / 'HoodieSpikeSleeveSideFix_report.txt').write_text('', encoding='utf-8')


def visible(o):
    return (not o.hide_viewport) and (not o.hide_render)


def bounds_world(o):
    if not o or not hasattr(o, 'bound_box'):
        return None
    coords = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {'min_x':min(xs), 'max_x':max(xs), 'min_y':min(ys), 'max_y':max(ys), 'min_z':min(zs), 'max_z':max(zs),
            'dim_x':max(xs)-min(xs), 'dim_y':max(ys)-min(ys), 'dim_z':max(zs)-min(zs)}


def bounds_from_key_data(key):
    coords = [p.co for p in key.data]
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {'min_x':min(xs), 'max_x':max(xs), 'min_y':min(ys), 'max_y':max(ys), 'min_z':min(zs), 'max_z':max(zs),
            'dim_x':max(xs)-min(xs), 'dim_y':max(ys)-min(ys), 'dim_z':max(zs)-min(zs)}


def key_world_bounds(obj, key=None):
    if key:
        coords = [obj.matrix_world @ p.co for p in key.data]
    elif obj.type == 'MESH':
        coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    else:
        return bounds_world(obj)
    xs=[c.x for c in coords]; ys=[c.y for c in coords]; zs=[c.z for c in coords]
    return {'min_x':min(xs), 'max_x':max(xs), 'min_y':min(ys), 'max_y':max(ys), 'min_z':min(zs), 'max_z':max(zs),
            'dim_x':max(xs)-min(xs), 'dim_y':max(ys)-min(ys), 'dim_z':max(zs)-min(zs)}


def center_from_bounds(b):
    return Vector(((b['min_x']+b['max_x'])*0.5, (b['min_y']+b['max_y'])*0.5, (b['min_z']+b['max_z'])*0.5))


def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def band(zn, a, b, c, d):
    return smoothstep(a, b, zn) * (1.0 - smoothstep(c, d, zn))


def radial(nx, ny, sx, sy):
    r = (nx/max(sx, 1e-6))**2 + (ny/max(sy, 1e-6))**2
    return max(0.0, 1.0 - min(1.0, r))


def restore_underglow():
    o = bpy.data.objects.get(UNDERGLOW_NAME)
    if not o:
        log('[lock] underglow missing')
        return {'name': UNDERGLOW_NAME, 'status': 'missing'}
    before = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    o.location = Vector(UNDERGLOW_LOCK_LOC)
    after = [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)]
    log(f'[lock] underglow locked {before} -> {after}')
    return {'name': UNDERGLOW_NAME, 'before': before, 'after': after}


def keep_character_baseline():
    hero = bpy.data.objects.get(HERO_NAME)
    disabled = []
    if hero and hero.type == 'MESH' and hero.data.shape_keys:
        for kb in hero.data.shape_keys.key_blocks:
            if kb.name.startswith('BODYFIT_'):
                before = float(kb.value)
                kb.value = 0.0
                disabled.append({'name': kb.name, 'before': round(before,4), 'after': 0.0})
    log('[character] F2 baseline preserved; BODYFIT keys kept disabled')
    return disabled


def find_hoodie():
    for name in FALLBACK_HOODIE_NAMES:
        o = bpy.data.objects.get(name)
        if o and o.type == 'MESH':
            if o.name != HOODIE_NAME:
                old = o.name
                o.name = HOODIE_NAME
                o.data.name = HOODIE_NAME + '_Mesh'
                log(f'[rename] hoodie renamed {old} -> {o.name}')
            return o
    matches = [o for o in bpy.data.objects if o.type == 'MESH' and ('hoodie' in o.name.lower() or 'pullover' in o.name.lower() or 'apricot' in o.name.lower())]
    if not matches:
        raise RuntimeError('No hoodie mesh found')
    o = sorted(matches, key=lambda x: (not visible(x), -len(x.data.vertices), x.name))[0]
    old = o.name
    o.name = HOODIE_NAME
    o.data.name = HOODIE_NAME + '_Mesh'
    log(f'[rename] hoodie renamed {old} -> {o.name}')
    return o


def ensure_hoodie_key(obj):
    if not obj.data.shape_keys:
        obj.shape_key_add(name='Basis', from_mix=False)
    if obj.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
        bpy.ops.object.shape_key_remove()

    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith('HOODIEFIT_'):
            kb.value = 0.0

    source = None
    for key_name in PREV_HOODIE_KEYS:
        kb = obj.data.shape_keys.key_blocks.get(key_name)
        if kb:
            kb.value = 1.0
            source = key_name
            break

    new_key = obj.shape_key_add(name=NEW_HOODIE_KEY, from_mix=True)
    for kb in obj.data.shape_keys.key_blocks:
        if kb.name.startswith('HOODIEFIT_'):
            kb.value = 0.0
    new_key.value = 1.0
    obj.active_shape_key_index = list(obj.data.shape_keys.key_blocks.keys()).index(NEW_HOODIE_KEY)
    return new_key, source


def build_adjacency(mesh):
    adj = [set() for _ in range(len(mesh.vertices))]
    for poly in mesh.polygons:
        vs = list(poly.vertices)
        n = len(vs)
        for i, a in enumerate(vs):
            for b in (vs[(i-1)%n], vs[(i+1)%n]):
                if a != b:
                    adj[a].add(b)
                    adj[b].add(a)
    return adj


def smooth_region(key, adjacency, weights, factor=0.35):
    original = [p.co.copy() for p in key.data]
    smoothed_count = 0
    max_fix = 0.0
    for i, w in enumerate(weights):
        if w <= 0.0:
            continue
        nbrs = adjacency[i]
        if not nbrs:
            continue
        avg = Vector((0.0, 0.0, 0.0))
        for n in nbrs:
            avg += original[n]
        avg /= len(nbrs)
        before = key.data[i].co.copy()
        key.data[i].co = before.lerp(avg, min(1.0, factor * w))
        d = (key.data[i].co - before).length
        if d > 1e-8:
            smoothed_count += 1
            max_fix = max(max_fix, d)
    return smoothed_count, max_fix


def apply_spike_sleeve_side_fix(hoodie):
    key, source = ensure_hoodie_key(hoodie)
    lb = bounds_from_key_data(key)
    before_world = key_world_bounds(hoodie, key)
    cx = (lb['min_x'] + lb['max_x']) * 0.5
    cy = (lb['min_y'] + lb['max_y']) * 0.5
    zmin = lb['min_z']; dz = max(lb['dim_z'], 1e-6)
    hx = max(lb['dim_x'] * 0.5, 1e-6)
    hy = max(lb['dim_y'] * 0.5, 1e-6)

    vertex_count_before = len(hoodie.data.vertices)
    face_count_before = len(hoodie.data.polygons)

    touched = 0
    max_delta = 0.0
    counts = {
        'ridge_rounded': 0,
        'spike_zone_smoothed': 0,
        'side_convex_reduced': 0,
        'sleeve_uniform_thickened': 0,
        'shoulder_root_opened': 0,
    }
    smooth_weights = [0.0] * len(key.data)

    for i, point in enumerate(key.data):
        co = point.co.copy()
        zn = (co.z - zmin) / dz
        nx_signed = (co.x - cx) / hx
        nx = abs(nx_signed)
        ny_signed = (co.y - cy) / hy
        ny = abs(ny_signed)

        top_ridge = band(zn, 0.76, 0.84, 1.0, 1.0)
        upper_bowl = band(zn, 0.62, 0.72, 0.94, 1.0)
        rim_top = band(zn, 0.54, 0.62, 0.84, 0.94)
        lower_side = band(zn, 0.34, 0.42, 0.64, 0.78)
        shoulder_band = band(zn, 0.48, 0.58, 0.72, 0.82)
        sleeve_band = band(zn, 0.34, 0.44, 0.70, 0.80)

        center = radial(nx, ny, 0.76, 0.90)
        wide = radial(nx, ny, 1.08, 1.04)
        side = smoothstep(0.36, 0.86, nx)
        frontback = smoothstep(0.32, 0.88, ny)
        outer = max(side, frontback)
        extreme_side = smoothstep(0.58, 0.92, nx)

        new = co.copy()

        # Round and raise the top ridge more, but with feathering so it blends into the bowl.
        ridge_weight = top_ridge * (0.55 + 0.45 * center)
        if ridge_weight > 0:
            new.z += dz * 0.030 * ridge_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.008 * ridge_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.012 * ridge_weight)
            smooth_weights[i] = max(smooth_weights[i], 0.55 * ridge_weight)

        bowl_weight = upper_bowl * wide
        if bowl_weight > 0:
            new.z += dz * 0.016 * bowl_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.012 * bowl_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.018 * bowl_weight)
            smooth_weights[i] = max(smooth_weights[i], 0.50 * bowl_weight)

        # Reduce the convex lower-side folds by reversing the previous outward push.
        side_fix = lower_side * side * (0.45 + 0.55 * (1.0 - center))
        if side_fix > 0:
            new.x = cx + (new.x - cx) * (1.0 - 0.028 * side_fix)
            new.y = cy + (new.y - cy) * (1.0 - 0.016 * side_fix)
            new.z += dz * 0.010 * side_fix
            smooth_weights[i] = max(smooth_weights[i], 0.70 * side_fix)

        # Keep the rim open vertically, but not too wide horizontally.
        rim_weight = rim_top * (0.55 + 0.45 * wide)
        if rim_weight > 0:
            new.z += dz * 0.022 * rim_weight
            new.x = cx + (new.x - cx) * (1.0 + 0.006 * rim_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.010 * rim_weight)
            smooth_weights[i] = max(smooth_weights[i], 0.45 * rim_weight)

        # Make sleeves more uniformly thick instead of pinched near the shoulder root.
        sleeve_weight = sleeve_band * extreme_side * (1.0 - 0.35 * frontback)
        if sleeve_weight > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.022 * sleeve_weight)
            new.y = cy + (new.y - cy) * (1.0 + 0.010 * sleeve_weight)
            smooth_weights[i] = max(smooth_weights[i], 0.55 * sleeve_weight)

        shoulder_weight = shoulder_band * extreme_side * (0.55 + 0.45 * (1.0 - ny))
        if shoulder_weight > 0:
            new.x = cx + (new.x - cx) * (1.0 + 0.016 * shoulder_weight)
            new.z += dz * 0.006 * shoulder_weight
            smooth_weights[i] = max(smooth_weights[i], 0.50 * shoulder_weight)

        delta = (new - co).length
        if delta > 1e-7:
            if ridge_weight > 0.08: counts['ridge_rounded'] += 1
            if side_fix > 0.08: counts['side_convex_reduced'] += 1
            if sleeve_weight > 0.08: counts['sleeve_uniform_thickened'] += 1
            if shoulder_weight > 0.08: counts['shoulder_root_opened'] += 1
            point.co = new
            touched += 1
            max_delta = max(max_delta, delta)

    adjacency = build_adjacency(hoodie.data)
    smoothed_count, max_smooth = smooth_region(key, adjacency, smooth_weights, factor=0.42)
    counts['spike_zone_smoothed'] = smoothed_count
    max_delta = max(max_delta, max_smooth)

    after_world = key_world_bounds(hoodie, key)
    vertex_count_after = len(hoodie.data.vertices)
    face_count_after = len(hoodie.data.polygons)
    hoodie['hoodie_fit_pass'] = 'HoodieSpikeSleeveSideFix_v1'
    hoodie['hoodie_fit_shape_key'] = NEW_HOODIE_KEY

    log(f"[hoodie] active shape key {NEW_HOODIE_KEY}; source={source}; touched_vertices={touched}; smoothed_vertices={smoothed_count}; max_delta_local={max_delta:.6f}; vertices={vertex_count_before}->{vertex_count_after}; faces={face_count_before}->{face_count_after}")
    return {
        'shape_key': NEW_HOODIE_KEY,
        'source_key': source,
        'value': 1.0,
        'touched_vertices': touched,
        'smoothed_vertices': smoothed_count,
        'max_delta_local': max_delta,
        'vertex_count_before': vertex_count_before,
        'vertex_count_after': vertex_count_after,
        'vertex_count_delta': vertex_count_after - vertex_count_before,
        'face_count_before': face_count_before,
        'face_count_after': face_count_after,
        'face_count_delta': face_count_after - face_count_before,
        'world_dimensions_before': [round(before_world['dim_x'],6), round(before_world['dim_y'],6), round(before_world['dim_z'],6)],
        'world_dimensions_after': [round(after_world['dim_x'],6), round(after_world['dim_y'],6), round(after_world['dim_z'],6)],
        'world_dimension_delta': [round(after_world['dim_x']-before_world['dim_x'],6), round(after_world['dim_y']-before_world['dim_y'],6), round(after_world['dim_z']-before_world['dim_z'],6)],
        'region_counts': counts,
    }


def object_report(name):
    o = bpy.data.objects.get(name)
    if not o:
        return {'name': name, 'status': 'missing'}
    b = bounds_world(o)
    shape_keys = []
    if o.type == 'MESH' and o.data.shape_keys:
        shape_keys = [{'name': kb.name, 'value': round(float(kb.value), 4)} for kb in o.data.shape_keys.key_blocks]
    return {'name': name, 'status': 'present', 'type': o.type, 'visible': visible(o),
            'loc': [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
            'dims': None if not b else [round(b['dim_x'],6), round(b['dim_y'],6), round(b['dim_z'],6)],
            'vertices': len(o.data.vertices) if o.type == 'MESH' else 0,
            'faces': len(o.data.polygons) if o.type == 'MESH' else 0,
            'shape_keys': shape_keys}


def scan_lights():
    rows = []
    for o in sorted([x for x in bpy.data.objects if x.type == 'LIGHT'], key=lambda x:x.name):
        d = o.data
        rows.append({'name': o.name, 'type': d.type, 'loc': [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)],
                     'energy': getattr(d, 'energy', None),
                     'color': [round(v,6) for v in getattr(d, 'color', [])] if hasattr(d, 'color') else None})
    return rows


def set_workbench(scene, color_type):
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = color_type
    scene.display.shading.show_xray = False
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = True


def setup_render_settings():
    scene = bpy.context.scene
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    log('[render] smaller 960x540 Workbench evidence renders with corrected side cameras')


def look_at(o, target):
    direction = target - o.location
    if direction.length:
        o.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def make_or_update_cam(name, loc, target, lens):
    cam = bpy.data.objects.get(name)
    if not cam or cam.type != 'CAMERA':
        data = bpy.data.cameras.new(name + '_Data')
        cam = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    return cam


def create_temp_wire_overlay(hoodie):
    dup = hoodie.copy()
    dup.data = hoodie.data.copy()
    dup.name = 'TMP_Hoodie_WireOverlay_DO_NOT_SAVE'
    dup.data.name = 'TMP_Hoodie_WireOverlay_Mesh'
    bpy.context.scene.collection.objects.link(dup)
    if dup.data.shape_keys:
        for kb in dup.data.shape_keys.key_blocks:
            kb.value = 0.0
            if kb.name == NEW_HOODIE_KEY:
                kb.value = 1.0
    mat = bpy.data.materials.new('TMP_Wire_Black_DO_NOT_SAVE')
    mat.diffuse_color = (0.0, 0.0, 0.0, 1.0)
    dup.data.materials.clear()
    dup.data.materials.append(mat)
    mod = dup.modifiers.new('TMP_RenderWire', 'WIREFRAME')
    mod.thickness = 0.0025
    mod.use_even_offset = True
    mod.use_replace = False
    dup.show_in_front = True
    return dup, mat


def render_review(hoodie):
    scene = bpy.context.scene
    old_engine = scene.render.engine
    old_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    old_camera = scene.camera
    old_filepath = scene.render.filepath

    kb = hoodie.data.shape_keys.key_blocks.get(NEW_HOODIE_KEY) if hoodie.data.shape_keys else None
    hb = key_world_bounds(hoodie, kb)
    center = center_from_bounds(hb)
    hood_focus = Vector((center.x, center.y, hb['min_z'] + hb['dim_z'] * 0.76))

    camspecs = [
        ('CAM_REVIEW_Hoodie_Material', (hood_focus.x + 0.70, hood_focus.y - 3.65, hood_focus.z + 1.00), hood_focus, 55, '01_HoodieMaterialPreviewShape.png', 'MATERIAL', False),
        ('CAM_REVIEW_Hoodie_LeftGray', (hood_focus.x - 2.45, hood_focus.y - 2.65, hood_focus.z + 0.95), hood_focus, 58, '02_HoodieLeftGraySide.png', 'SINGLE', False),
        ('CAM_REVIEW_Hoodie_RightGray', (hood_focus.x + 2.45, hood_focus.y - 2.65, hood_focus.z + 0.95), hood_focus, 58, '03_HoodieRightGraySide.png', 'SINGLE', False),
        ('CAM_REVIEW_Hoodie_Wire', (hood_focus.x + 0.30, hood_focus.y - 3.05, hood_focus.z + 1.30), hood_focus, 58, '04_HoodieWireSpikeCheck.png', 'SINGLE', True),
        ('CAM_REVIEW_Hoodie_Scene', (center.x + 5.0, center.y - 7.6, center.z + 1.25), center + Vector((0,1.0,0.2)), 44, '05_HoodieScenePreserved.png', 'MATERIAL', False),
    ]

    cams = []
    wire_obj = None
    wire_mat = None
    try:
        setup_render_settings()
        for name, loc, tgt, lens, fn, color_type, use_wire in camspecs:
            if use_wire:
                wire_obj, wire_mat = create_temp_wire_overlay(hoodie)
            set_workbench(scene, color_type)
            cam = make_or_update_cam(name, loc, tgt, lens)
            cams.append({'name': name, 'render': fn, 'loc': [round(cam.location.x,6), round(cam.location.y,6), round(cam.location.z,6)], 'lens': lens, 'mode': 'WORKBENCH_' + color_type + ('_WIREFRAME' if use_wire else '')})
            scene.camera = cam
            scene.render.filepath = str(OUT / fn)
            bpy.ops.render.render(write_still=True)
            log('[render] ' + fn)
            if wire_obj:
                bpy.data.objects.remove(wire_obj, do_unlink=True)
                wire_obj = None
            if wire_mat:
                bpy.data.materials.remove(wire_mat, do_unlink=True)
                wire_mat = None
    finally:
        if wire_obj:
            bpy.data.objects.remove(wire_obj, do_unlink=True)
        if wire_mat:
            bpy.data.materials.remove(wire_mat, do_unlink=True)
        scene.render.engine = old_engine
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old_res
        scene.camera = old_camera
        scene.render.filepath = old_filepath
    return cams


def copy_current_review():
    for p in CUR.glob('*'):
        if p.is_file():
            p.unlink()
    for p in OUT.glob('*'):
        if p.is_file():
            (CUR / p.name).write_bytes(p.read_bytes())


def write_reports(hoodie_fit, disabled_bodyfit, under, cams):
    payload = {
        'pass': 'hoodie_spike_sleeve_side_fix_v1',
        'hoodie_fit': hoodie_fit,
        'disabled_bodyfit_keys': disabled_bodyfit,
        'underglow_lock': under,
        'review_cameras': cams,
        'key_objects': [object_report(n) for n in [HERO_NAME, HOODIE_NAME, 'Cargo pants', 'Plane.001', 'Plane.022', 'Asphalt ground', 'Audi e-tron GT quattro Black']],
        'lights_scan': scan_lights(),
        'notes': [
            'Vertex is singular; vertices is plural.',
            'This pass only moves existing vertices through a shape key. It does not add/remove topology, so vertex and face counts should remain unchanged.',
            'Previous lower-side convexity came from over-pushing the lower side shell outward while trying to open the cavity. This pass reverses that bias and shifts the opening emphasis to the rim/upper bowl instead.',
            'Wire spikes are addressed by a local neighbor-smoothing pass after the shape deformation.'
        ],
    }
    (REP / 'hoodie_spike_sleeve_side_fix_v1.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    (OUT / 'HoodieSpikeSleeveSideFix_status.json').write_text(json.dumps({'ok': True, 'hoodie_shape_key': NEW_HOODIE_KEY, 'touched_vertices': hoodie_fit['touched_vertices'], 'smoothed_vertices': hoodie_fit['smoothed_vertices'], 'vertex_delta': hoodie_fit['vertex_count_delta'], 'face_delta': hoodie_fit['face_count_delta'], 'review_cameras': [c['name'] for c in cams]}, indent=2), encoding='utf-8')
    md = [
        '# Hoodie Spike Sleeve Side Fix v1',
        '',
        '## Changes',
        f"- Added active hoodie shape key: **{NEW_HOODIE_KEY}**.",
        '- Rounded the top ridge more and feathered it further into the bowl.',
        '- Reversed the prior lower-side outward bias to reduce the convex side folds.',
        '- Thickened sleeves more uniformly and opened the shoulder root so it does not pinch thinner than Sackboy\'s arm silhouette.',
        '- Added a local neighbor-smoothing pass to reduce visible wire spikes/outlier vertices.',
        '- Review cameras now use one material preview, left gray side, right gray side, wire spike check, and one scene preservation view.',
        '',
        '## Counts',
        '- Vertex is singular; vertices is plural.',
        f"- Hoodie vertices: {hoodie_fit['vertex_count_before']} -> {hoodie_fit['vertex_count_after']} (delta {hoodie_fit['vertex_count_delta']})",
        f"- Hoodie faces: {hoodie_fit['face_count_before']} -> {hoodie_fit['face_count_after']} (delta {hoodie_fit['face_count_delta']})",
        f"- Touched vertices in shape key: {hoodie_fit['touched_vertices']}",
        f"- Smoothed vertices: {hoodie_fit['smoothed_vertices']}",
        f"- Max local vertex movement: {hoodie_fit['max_delta_local']:.6f}",
        f"- World dimensions before: {hoodie_fit['world_dimensions_before']}",
        f"- World dimensions after: {hoodie_fit['world_dimensions_after']}",
        f"- World dimension delta: {hoodie_fit['world_dimension_delta']}",
        '',
        '## Why the convex sides happened before',
        '- The previous pass over-expanded the lower side shell outward while trying to open the hood cavity.',
        '- This pass does the opposite there: it eases those side walls inward/upward and moves the opening emphasis to the upper bowl and rim.',
    ]
    (REP / 'Hoodie_Spike_Sleeve_Side_Fix_v1.md').write_text('\n'.join(md), encoding='utf-8')


def manifest():
    data = {'blend_file': bpy.data.filepath, 'objects': [], 'collections': []}
    for col in sorted(bpy.data.collections, key=lambda c: c.name):
        data['collections'].append({'name': col.name, 'hide_viewport': bool(col.hide_viewport), 'hide_render': bool(col.hide_render), 'object_count': len(col.objects), 'child_count': len(col.children)})
    for o in sorted(bpy.data.objects, key=lambda x: x.name):
        b = bounds_world(o)
        item = {'name': o.name, 'type': o.type, 'collections': [c.name for c in o.users_collection], 'visible': visible(o), 'location': [round(o.location.x,6), round(o.location.y,6), round(o.location.z,6)], 'dimensions': None if not b else [round(b['dim_x'],6), round(b['dim_y'],6), round(b['dim_z'],6)]}
        if o.type == 'MESH':
            item['vertices'] = len(o.data.vertices)
            item['faces'] = len(o.data.polygons)
            if o.data.shape_keys:
                item['shape_keys'] = [{'name': kb.name, 'value': round(float(kb.value),4)} for kb in o.data.shape_keys.key_blocks]
        if o.type == 'LIGHT':
            item['energy'] = getattr(o.data, 'energy', None)
            item['color'] = [round(v,6) for v in getattr(o.data, 'color', [])] if hasattr(o.data, 'color') else None
        if o.type == 'CAMERA' and o.name.startswith('CAM_REVIEW_'):
            item['review_camera'] = True
        data['objects'].append(item)
    (ROOT / 'scene_manifest.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    (AUD / 'scene_manifest.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    (AUD / 'scene_layout_summary.md').write_text(
        '# Scene Layout Summary\n\nUpdated by Hoodie Spike Sleeve Side Fix v1.\n\n'
        '- Focused hoodie corrective shape key added.\n'
        '- Review renders use pulled-back Workbench/material/gray/wire views at 960x540.\n'
        '- Render engine is restored after evidence renders.\n', encoding='utf-8')
    (AUD / 'project_file_layout.json').write_text(json.dumps({'generated_by': 'hoodie_spike_sleeve_side_fix_v1', 'reports': str(REP), 'renders': str(OUT), 'current_review': str(CUR)}, indent=2), encoding='utf-8')


def main():
    reset()
    log('[pass] hoodie spike sleeve side fix v1')
    hoodie = find_hoodie()
    under = restore_underglow()
    disabled_bodyfit = keep_character_baseline()
    hoodie_fit = apply_spike_sleeve_side_fix(hoodie)
    cams = render_review(hoodie)
    write_reports(hoodie_fit, disabled_bodyfit, under, cams)
    copy_current_review()
    manifest()
    out = ROOT / 'blender' / 'sackboy_scene.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    log('[save] ' + str(out))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / 'HoodieSpikeSleeveSideFix_FATAL_ERROR.txt').open('w', encoding='utf-8') as f:
            traceback.print_exc(file=f)
        raise
