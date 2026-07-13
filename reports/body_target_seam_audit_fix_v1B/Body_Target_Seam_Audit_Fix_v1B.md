# Body Target + Seam Audit Fix v1B

## Why
- The previous diagnostic pass selected the hoodie as both hoodie and body because the hoodie name contains `SACKBOY`.
- This pass explicitly selects visible `F2` as the current body target when available.
- It also uses nearest-boundary-edge seam zones so collar/top hood zones are not reported as zero merely because a bounding-box heuristic missed them.

## Safety
- No seam repair.
- No smoothing/shrinkwrap/welding/bridging.
- Deletes only previous `SEAMDIAG_*` and `TMP_SEAMDIAG_*` diagnostic objects.
- Temporary overlays are removed before save.

## Targets
- Hoodie: `SACKBOY_Hoodie_EditProxy`
- Body: `F2` selected by `exact_visible_F2`

## Hoodie mesh
- vertices: 245107
- faces: 489016
- boundary edges total: 931
- vertex islands: 380
- top island sizes: [180811, 40509, 13703, 3069, 3053, 1092, 1092, 360, 360, 103]

## Seam zones
- `left_armpit`: edges=180 total_length=0.598499
- `right_armpit`: edges=180 total_length=1.277087
- `hood_collar_front`: edges=180 total_length=0.514702
- `hood_collar_back`: edges=180 total_length=0.960556
- `hood_top_center`: edges=180 total_length=0.594362

## Mesh exports
- `current_hoodie_SACKBOY_Hoodie_EditProxy.obj` verts=37028 faces=73351
- `current_body_F2.obj` verts=33625 faces=63717

## Renders
- `01_V1B_FullContext_SeamOverlay.png` camera=`SEAMDIAG_V1B_FULL_CONTEXT`
- `02_V1B_LeftArmpit_SeamOverlay.png` camera=`SEAMDIAG_V1B_LEFT_ARMPIT`
- `03_V1B_RightArmpit_SeamOverlay.png` camera=`SEAMDIAG_V1B_RIGHT_ARMPIT`
- `04_V1B_HoodCollar_SeamOverlay.png` camera=`SEAMDIAG_V1B_HOOD_COLLAR`
- `05_V1B_HoodTop_SeamOverlay.png` camera=`SEAMDIAG_V1B_HOOD_TOP`