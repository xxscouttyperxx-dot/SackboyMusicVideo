# Seam Diagnostic Audit v1

## Safety
- Diagnostic only.
- Deleted only previous `SEAMDIAG_*` cameras and `TMP_SEAMDIAG_*` temporary objects.
- Created fresh seam diagnostic cameras.
- Temporarily rendered boundary-edge overlays, then removed overlay objects before saving.
- Did not edit hoodie mesh geometry, smoothing, shrinkwrap, materials, shape keys, lights, car, or environment.

## Hoodie target
- `SACKBOY_Hoodie_EditProxy`

## Mesh diagnostics
- vertices: 245107
- edges: 733840
- faces: 489016
- total boundary/open edges: 931
- connected vertex islands: 380
- largest island sizes: [180811, 40509, 13703, 3069, 3053, 1092, 1092, 360, 360, 103]

## Seam zone boundary/open-edge counts
- `left_armpit`: boundary_edges=605, total_length=3.342531, mean_length=0.005525
- `right_armpit`: boundary_edges=326, total_length=2.290879, mean_length=0.007027
- `hood_collar_band`: boundary_edges=0, total_length=0, mean_length=0.0
- `hood_top_center`: boundary_edges=0, total_length=0, mean_length=0.0
- `all_boundary_edges`: boundary_edges=931, total_length=5.63341, mean_length=0.006051

## Created seam cameras
- `SEAMDIAG_LEFT_ARMPIT_CLOSE`
- `SEAMDIAG_RIGHT_ARMPIT_CLOSE`
- `SEAMDIAG_HOOD_COLLAR_FRONT`
- `SEAMDIAG_HOOD_TOP_CENTER`
- `SEAMDIAG_FULL_FRONT_CONTEXT`

## Renders
- `01_SEAM_FullFront_BoundaryOverlay.png` camera=`SEAMDIAG_FULL_FRONT_CONTEXT`
- `02_SEAM_LeftArmpit_BoundaryOverlay.png` camera=`SEAMDIAG_LEFT_ARMPIT_CLOSE`
- `03_SEAM_RightArmpit_BoundaryOverlay.png` camera=`SEAMDIAG_RIGHT_ARMPIT_CLOSE`
- `04_SEAM_HoodCollar_BoundaryOverlay.png` camera=`SEAMDIAG_HOOD_COLLAR_FRONT`
- `05_SEAM_HoodTop_BoundaryOverlay.png` camera=`SEAMDIAG_HOOD_TOP_CENTER`

## Repair guidance for next pass
- Do not broad-smooth the armpit or hood top seam areas.
- Use local seam-border repositioning, bridge/fill, or merge-by-distance only after reviewing these zone overlays.
- Sleeve/armpit zones should be fixed locally before any cloth simulation.