Sackboy F2-Only Bind / Weights v1

Purpose:
- Bind only F2 to SACKBOY_RIG_PLACEMENT_V1.
- Add one Armature modifier to F2.
- Generate normalized weights for the rig's deform bones.
- Leave F2 visually unchanged in the rest pose.
- Leave all clothing and accessories unbound.

Weighting:
1. Blender automatic bone-heat weighting is attempted first.
2. The result is validated for complete vertex coverage and valid weights.
3. A deterministic nearest-bone fallback is used only when automatic weighting
   fails or leaves unweighted vertices.

Safety:
- Requires the approved 22-bone armature.
- Requires F2 to have no shape keys, vertex groups, or Armature modifier.
- Requires the armature to have no active action and no non-rest pose transforms.
- Snapshots all non-F2 objects and the armature's rest bones.
- Stops before saving when F2 moves in the rest pose.
- Does not bind hoodie, pants, eyes, or shoes.
- Does not create a test action or change the scene timeline.

Next stage:
- Controlled F2 deformation preview poses.
- Weight assessment at shoulders, elbows, hips, knees, wrists, and ankles.
