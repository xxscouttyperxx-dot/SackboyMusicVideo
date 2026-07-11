import bpy
from character_config import CHARACTER as CFG
from common import ensure_collection, move_to_collection, material, apply_material

COL = "CHAR_SackDoll"

def clear():
    col = bpy.data.collections.get(COL)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

def add_subsurf(obj, levels=2):
    mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    mod.levels = levels
    mod.render_levels = levels
    return mod

def uv_sphere(name, loc, scale, mat, col, segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=loc
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_material(obj, mat)
    move_to_collection(obj, col)
    bpy.ops.object.shade_smooth()
    return obj

def smooth_head_deform(obj):
    sx, sy, sz = CFG["head_scale"]

    for v in obj.data.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        y_norm = y / max(0.001, sy)
        z_norm = z / max(0.001, sz)

        # Gradual front flattening.
        face_w = max(0.0, min(1.0, (-y_norm - 0.20) / 0.80))
        y *= (1.0 - 0.18 * face_w)

        # Gentle cheek fullness.
        cheek_w = max(0.0, 1.0 - abs(z_norm) / 0.80) * max(0.0, 1.0 - abs(y_norm) / 0.95)
        x *= (1.0 + 0.06 * cheek_w)

        # Gentle lower-face taper.
        jaw_w = max(0.0, min(1.0, (-z_norm - 0.18) / 0.82))
        x *= (1.0 - 0.08 * jaw_w)

        # Slight crown/chin flattening.
        cap_w = max(0.0, min(1.0, (abs(z_norm) - 0.70) / 0.30))
        z *= (1.0 - 0.05 * cap_w)

        v.co.x, v.co.y, v.co.z = x, y, z

def soften_torso(obj):
    sx, sy, sz = CFG["torso_scale"]

    for v in obj.data.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        z_norm = z / max(0.001, sz)
        y_norm = y / max(0.001, sy)

        belly_w = max(0.0, 1.0 - abs(z_norm) / 0.45) * max(0.0, min(1.0, (-y_norm - 0.10) / 0.80))
        y -= 0.04 * belly_w

        hip_w = max(0.0, min(1.0, (-z_norm - 0.12) / 0.88))
        x *= (1.0 + 0.08 * hip_w)

        if z_norm < -0.65:
            z *= 0.90

        v.co.x, v.co.y, v.co.z = x, y, z

def integrate_eye(name, x, col, eye_mat):
    eye = uv_sphere(
        name,
        (x, CFG["eye_y"], CFG["eye_z"]),
        CFG["eye_scale"],
        eye_mat,
        col,
        segments=48,
        rings=24,
    )

    # Slightly flatten the visible front so it reads like an inset bead/button.
    for v in eye.data.vertices:
        if v.co.y < 0.0:
            v.co.y *= 0.82

    return eye

def add_open_mouth(col, mouth_mat):
    mouth = uv_sphere(
        "SK_Mouth_Open",
        CFG["mouth_loc"],
        CFG["mouth_scale"],
        mouth_mat,
        col,
        segments=64,
        rings=32,
    )

    # Sculpt a simple smile-like cavity:
    # center hangs lower, corners rise slightly, upper edge flatter.
    sx, sy, sz = CFG["mouth_scale"]

    for v in mouth.data.vertices:
        x_norm = v.co.x / max(0.001, sx)
        z_norm = v.co.z / max(0.001, sz)

        # Lift corners for a smile arc.
        v.co.z += CFG["mouth_corner_lift"] * (x_norm * x_norm)

        # Flatten the upper half so the mouth reads as an opening, not lips.
        if z_norm > 0.0:
            v.co.z *= CFG["mouth_top_flatten"]

        # Push the rear side slightly into the head.
        if v.co.y > 0.0:
            v.co.y *= 0.55

    return mouth

def add_mitten(name, loc, scale, mat, col, side_sign):
    hand = uv_sphere(name, loc, scale, mat, col, segments=48, rings=24)

    for v in hand.data.vertices:
        v.co.y *= 0.84
        if v.co.x * side_sign > 0:
            v.co.x *= 1.06

    uv_sphere(
        name + "_Thumb",
        (
            loc[0] + side_sign * scale[0] * 0.50,
            loc[1] - scale[1] * 0.25,
            loc[2] - scale[2] * 0.05,
        ),
        (scale[0] * 0.33, scale[1] * 0.46, scale[2] * 0.52),
        mat,
        col,
        segments=32,
        rings=16,
    )

    return hand

def add_shoe(name, loc, scale, mat, col):
    shoe = uv_sphere(name, loc, scale, mat, col, segments=48, rings=24)

    for v in shoe.data.vertices:
        if v.co.z < -0.04:
            v.co.z *= 0.32
        if v.co.y < -0.02:
            v.co.x *= 1.08
        if v.co.y > 0.12:
            v.co.x *= 0.92
            v.co.z *= 0.92

    return shoe

def build():
    clear()
    col = ensure_collection(COL)

    base = material("MAT_BaseGray_v5", (0.84, 0.84, 0.86, 1), 0.66)
    mouth_mat = material("MAT_MouthDark_v5", (0.025, 0.025, 0.032, 1), 0.36)
    eye_mat = material("MAT_EyesGloss_v5", (0.01, 0.01, 0.015, 1), 0.08, 0.0)

    # Head
    head = uv_sphere("SK_Head", CFG["head_loc"], CFG["head_scale"], base, col)
    smooth_head_deform(head)
    add_subsurf(head, 2)

    # Torso
    torso = uv_sphere("SK_Torso", CFG["torso_loc"], CFG["torso_scale"], base, col)
    soften_torso(torso)
    add_subsurf(torso, 2)

    # Eyes integrated into the face plane.
    integrate_eye("SK_Eye_L", -CFG["eye_x"], col, eye_mat)
    integrate_eye("SK_Eye_R",  CFG["eye_x"], col, eye_mat)

    # Actual open mouth cavity.
    add_open_mouth(col, mouth_mat)

    # Arms
    ua_l = uv_sphere("SK_UpperArm_L", CFG["upper_arm_L_loc"], CFG["upper_arm_scale"], base, col, 48, 24)
    ua_r = uv_sphere("SK_UpperArm_R", CFG["upper_arm_R_loc"], CFG["upper_arm_scale"], base, col, 48, 24)
    fa_l = uv_sphere("SK_Forearm_L", CFG["forearm_L_loc"], CFG["forearm_scale"], base, col, 48, 24)
    fa_r = uv_sphere("SK_Forearm_R", CFG["forearm_R_loc"], CFG["forearm_scale"], base, col, 48, 24)

    for arm in (ua_l, ua_r, fa_l, fa_r):
        add_subsurf(arm, 1)

    add_mitten("SK_Hand_L", CFG["hand_L_loc"], CFG["hand_scale"], base, col, -1)
    add_mitten("SK_Hand_R", CFG["hand_R_loc"], CFG["hand_scale"], base, col, 1)

    # Legs
    th_l = uv_sphere("SK_Thigh_L", CFG["thigh_L_loc"], CFG["thigh_scale"], base, col, 48, 24)
    th_r = uv_sphere("SK_Thigh_R", CFG["thigh_R_loc"], CFG["thigh_scale"], base, col, 48, 24)
    sh_l = uv_sphere("SK_Shin_L", CFG["shin_L_loc"], CFG["shin_scale"], base, col, 48, 24)
    sh_r = uv_sphere("SK_Shin_R", CFG["shin_R_loc"], CFG["shin_scale"], base, col, 48, 24)

    for leg in (th_l, th_r, sh_l, sh_r):
        add_subsurf(leg, 1)

    add_shoe("SK_Foot_L", CFG["foot_L_loc"], CFG["foot_scale"], base, col)
    add_shoe("SK_Foot_R", CFG["foot_R_loc"], CFG["foot_scale"], base, col)

    print("[Step01A v5] Face integration and open mouth complete.")

if __name__ == "__main__":
    build()
