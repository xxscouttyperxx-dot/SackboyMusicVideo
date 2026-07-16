Sackboy Dressed Rig Review + Controls v1.8

Why v1.7 stopped before Blender:
- The production mesh_binding_snapshot function was already correct.
- The PowerShell launcher searched the entire Python file as raw text for
  matrix_world.
- A different safety function, object_snapshot, legitimately uses matrix_world.
- The whole-file search found that unrelated code and falsely claimed it was
  inside mesh_binding_snapshot.

Root correction:
- Removes the brittle whole-file matrix_world PowerShell check.
- Blender's own Python now parses the production script with ast.
- It locates mesh_binding_snapshot specifically.
- It rejects executable matrix_world access only inside that function.
- It also requires matrix_basis, matrix_parent_inverse, and the
  POSE_INDEPENDENT_BINDING_SNAPSHOT marker.

Preflight checks before the project opens:
1. Semantic AST inspection of mesh_binding_snapshot.
2. Synthetic pelvis disconnect/reparent/restore and movement test.
3. Synthetic bone-parented eye action-switch regression.

The project run still performs:
- Stage 9 dressed deformation review.
- Rest preservation.
- Pelvis propagation probe.
- Stage 11 automatic control checks.
- Pose-independent structural mesh-binding comparison.
- Protected-scene comparison.
- No save until all checks pass.

Stage 11 frames:
- 300 rest
- 310 root movement
- 320 torso/head controls
- 330 arm IK
- 340 elbow pole steering
- 350 planted-foot squat
- 360 left kick
- 370 right kick
- 380 planted-foot weight shift
- 390 rest
