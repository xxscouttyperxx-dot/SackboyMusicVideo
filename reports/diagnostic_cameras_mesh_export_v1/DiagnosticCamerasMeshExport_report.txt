# Diagnostic Cameras + Mesh Export v1

## Safety
- Deleted only previous `DIAG_CURRENT_*` diagnostic cameras.
- Created fresh `DIAG_CURRENT_*` cameras aimed at the current visible character/clothing baseline.
- Exported targeted OBJ diagnostics for current hoodie/body/clothing candidates.
- Did not edit mesh geometry, materials, shape keys, modifiers, lights, world, car, or environment.
- Saved the blend locally so diagnostic cameras remain available.

## Counts
- total_objects: 221
- visible_objects: 210
- hidden_objects: 11
- duplicate_base_name_groups: 6
- duplicate_base_name_object_count: 91
- shared_data_groups: 1

## Current targets
- Current hoodie: `SACKBOY_Hoodie_EditProxy`
- Current body: `SACKBOY_Hoodie_EditProxy`

## Removed old diagnostic cameras
- None

## Created diagnostic cameras
- `DIAG_CURRENT_FULL_FRONT`
- `DIAG_CURRENT_FULL_3Q`
- `DIAG_CURRENT_LEFT_ARMPIT`
- `DIAG_CURRENT_RIGHT_ARMPIT`
- `DIAG_CURRENT_HOOD_TOP`

## Mesh diagnostics
- `SACKBOY_Hoodie_EditProxy`: boundary_edges=931, boundary_vertices=923, nonmanifold_edges=1102, islands=380, top_islands=[180811, 40509, 13703, 3069, 3053]
- `Cargo pants`: boundary_edges=356, boundary_vertices=362, nonmanifold_edges=540, islands=1, top_islands=[16507]

## Exports
- `current_hoodie_SACKBOY_Hoodie_EditProxy.obj` verts=37028 faces=73351
- `current_body_SACKBOY_Hoodie_EditProxy.obj` verts=37028 faces=73351
- `clothing_2_Cargo_pants.obj` verts=16507 faces=16424

## Renders
- `01_DIAG_FullFront_SOLID.png` camera=`DIAG_CURRENT_FULL_FRONT` mode=solid
- `02_DIAG_Full3Q_SOLID.png` camera=`DIAG_CURRENT_FULL_3Q` mode=solid
- `03_DIAG_Full3Q_RENDERED.png` camera=`DIAG_CURRENT_FULL_3Q` mode=rendered
- `04_DIAG_LeftArmpit_SOLID.png` camera=`DIAG_CURRENT_LEFT_ARMPIT` mode=solid
- `05_DIAG_RightArmpit_SOLID.png` camera=`DIAG_CURRENT_RIGHT_ARMPIT` mode=solid
- `06_DIAG_HoodTop_SOLID.png` camera=`DIAG_CURRENT_HOOD_TOP` mode=solid

## Next recommendation
- Use the mesh diagnostics and current renders to choose a seam-repair pass, not broad smoothing.
- Sleeve/armpit seam repair should use local seam-border repositioning/merge or bridge repair before any cloth simulation.