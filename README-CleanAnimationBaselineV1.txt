Clean Animation Baseline v1

Write scope:
- Bake F2's currently visible shape-key result into permanent mesh geometry.
- Remove F2's shape-key datablock.
- Clear old object animation data only from the approved rig targets.
- Normalize origins without moving visible evaluated geometry:
    F2
    Lowerpoly hoodie
    Cargo pants
    L.Eye
    R.Eye
    Plane.001
    Plane.022
- Unparent Plane.001 and Plane.022 from the Shoes Empty using keep-transform behavior.
- Remove only the exact Shoes Empty after verifying its children.
- Preserve all other objects, including lightning, bolts, fog, volume, clouds, lamps, cameras, car and environment.
- Create no armature.

Safety:
- Stops if required objects are missing.
- Stops if F2 has modifiers or evaluated topology changes during baking.
- Verifies evaluated world-space vertex positions before and after.
- Snapshots every non-target object and stops before save if any protected object changes.
- Does not create a full .blend backup.
