# Step01A v5 - Face Integration + Open Mouth
# Focus:
# - partially embed the eyes into the head
# - create an actual dark open mouth cavity
# - keep facial features attached to the face plane
# - preserve the improved V4 head/body silhouette

CHARACTER = {
    # Head
    "head_loc": (0.0, 0.0, 2.08),
    "head_scale": (0.98, 0.72, 0.80),

    # Eyes: moved inward so they intersect the head instead of floating
    "eye_x": 0.31,
    "eye_y": -0.615,
    "eye_z": 2.15,
    "eye_scale": (0.125, 0.105, 0.150),

    # Open mouth cavity
    "mouth_loc": (0.0, -0.635, 1.985),
    "mouth_scale": (0.34, 0.055, 0.105),
    "mouth_corner_lift": 0.032,
    "mouth_top_flatten": 0.45,

    # Torso
    "torso_loc": (0.0, 0.03, 1.16),
    "torso_scale": (0.47, 0.37, 0.68),

    # Arms
    "upper_arm_L_loc": (-0.50, 0.00, 1.37),
    "upper_arm_R_loc": ( 0.50, 0.00, 1.37),
    "upper_arm_scale": (0.16, 0.14, 0.36),

    "forearm_L_loc": (-0.64, 0.00, 1.03),
    "forearm_R_loc": ( 0.64, 0.00, 1.03),
    "forearm_scale": (0.145, 0.130, 0.32),

    "hand_L_loc": (-0.76, -0.01, 0.76),
    "hand_R_loc": ( 0.76, -0.01, 0.76),
    "hand_scale": (0.25, 0.165, 0.135),

    # Legs
    "thigh_L_loc": (-0.18, 0.00, 0.60),
    "thigh_R_loc": ( 0.18, 0.00, 0.60),
    "thigh_scale": (0.19, 0.175, 0.30),

    "shin_L_loc": (-0.18, 0.00, 0.30),
    "shin_R_loc": ( 0.18, 0.00, 0.30),
    "shin_scale": (0.18, 0.165, 0.275),

    "foot_L_loc": (-0.18, -0.13, 0.12),
    "foot_R_loc": ( 0.18, -0.13, 0.12),
    "foot_scale": (0.28, 0.37, 0.14),
}
