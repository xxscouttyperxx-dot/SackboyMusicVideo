# Hoodie Spike Sleeve Side Fix v1

## Changes
- Added active hoodie shape key: **HOODIEFIT_SpikeSleeveSideFix_v1**.
- Rounded the top ridge more and feathered it further into the bowl.
- Reversed the prior lower-side outward bias to reduce the convex side folds.
- Thickened sleeves more uniformly and opened the shoulder root so it does not pinch thinner than Sackboy's arm silhouette.
- Added a local neighbor-smoothing pass to reduce visible wire spikes/outlier vertices.
- Review cameras now use one material preview, left gray side, right gray side, wire spike check, and one scene preservation view.

## Counts
- Vertex is singular; vertices is plural.
- Hoodie vertices: 257116 -> 257116 (delta 0)
- Hoodie faces: 489064 -> 489064 (delta 0)
- Touched vertices in shape key: 84153
- Smoothed vertices: 83146
- Max local vertex movement: 0.092581
- World dimensions before: [2.277528, 1.136009, 2.25433]
- World dimensions after: [2.277528, 1.141722, 2.32066]
- World dimension delta: [0.0, 0.005712, 0.066331]

## Why the convex sides happened before
- The previous pass over-expanded the lower side shell outward while trying to open the hood cavity.
- This pass does the opposite there: it eases those side walls inward/upward and moves the opening emphasis to the upper bowl and rim.