# Hoodie Camera Cleanup Shape Fix v1

## Changes
- Added active hoodie shape key: **HOODIEFIT_CameraCleanupShapeFix_v1**.
- Deleted old `CAM_REVIEW_*` camera duplicates and recreated a minimal review set.
- Pushed the wire camera back and rendered it as an isolated hoodie-only wire view so scene/camera/light wireframes do not look like hoodie spikes.
- Raised shoulder collar seams.
- Pulled lower hood sides back out and down instead of pushing them in/up.
- Feathered/reduced the rear hood protrusion in side profile.
- Kept sleeves more uniformly thick near the shoulder root.

## Counts
- Hoodie vertices: 257116 -> 257116 (delta 0)
- Hoodie faces: 489064 -> 489064 (delta 0)
- Touched vertices: 103613
- Smoothed vertices: 102252
- Max local vertex movement: 0.050728
- World dimensions before: [2.277528, 1.141722, 2.32066]
- World dimensions after: [2.277528, 1.144981, 2.366244]
- World dimension delta: [0.0, 0.003259, 0.045584]

## Camera cleanup
- Removed old review cameras: 37
- Retained/created reference cameras: ['CAM_REVIEW_F2_Front', 'CAM_REVIEW_F2_ThreeQuarter', 'CAM_REVIEW_F2_Profile', 'CAM_REVIEW_StorefrontReflection_A', 'CAM_REVIEW_StorefrontReflection_B', 'CAM_REVIEW_StorefrontReflection_C']