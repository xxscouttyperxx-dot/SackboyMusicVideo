Sackboy Arm Alignment Refinement v1

Purpose:
- Refine the eight arm-chain bones:
  clavicle.L/R
  upper_arm.L/R
  forearm.L/R
  hand.L/R
- Use actual F2 evaluated world-space mesh vertices to estimate shoulder, elbow, wrist, and hand center positions.
- Keep the torso, head, pelvis, legs, feet, and toes unchanged.
- Preserve the 22-bone armature structure.
- Keep all character meshes unparented and unweighted.
- Preserve lightning, fog, clouds, lamps, cameras, car, and environment.

No IK controls or constraints are added in this stage.
No Armature modifiers or vertex groups are added.
