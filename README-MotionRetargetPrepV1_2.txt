Sackboy Motion Extraction and Retarget Preparation v1.2

Why v1.1 stopped:
- protected_before was captured at the user's original frame.
- The script then switched to frame 300 for rest-appearance checks.
- protected_after was captured while the scene was still at frame 300.
- Empty, FINAL_ORBIT_RIG, and Lightning are animated, so their evaluated
  matrix_world values correctly differed between the two frames.
- The script falsely interpreted that time change as an object modification.

v1.2 root correction:
- Records the protected comparison frame explicitly.
- Restores that exact frame before taking protected_after snapshots.
- Updates the dependency graph before both comparisons.
- Writes ProtectedObjectDiagnosticV1_2.json with exact changed fields.
- Keeps matrix_world in protected-object checks because it is useful when both
  snapshots are evaluated at the same frame.
- Adds a real Blender regression proving different frames differ and restored
  same-frame snapshots match.

The project blend was not saved by the failed v1.1 run.
