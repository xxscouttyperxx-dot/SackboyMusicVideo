# Scene Collections Organization v1

## Safety
- No objects were deleted.
- No visible objects were hidden.
- No geometry, materials, modifiers, shape keys, light values, camera transforms, or render settings were intentionally changed.
- Objects were only linked into clean collections and unlinked from old collections to reduce repeated Outliner listings.

## Counts
- Total objects before/after: 252 -> 252
- Visible objects before/after: 204 -> 205
- Duplicate base-name groups: 6
- Objects inside duplicate base-name groups: 91
- Shared mesh-data groups: 1
- Multi-collection objects before/after: 43 -> 0

## Top collection order
- `01_CHARACTER_AND_SAME_NAME_GROUPS`
- `02_CLOTHING_AND_SAME_NAME_GROUPS`
- `03_HERO_CAR_AND_IMPORTED_PARTS`
- `04_ENVIRONMENT_STOREFRONTS_PARKING`
- `05_PROPS_SIGNS_DECOR`
- `06_LIGHTING_REFLECTIONS`
- `07_CAMERAS`
- `08_HIDDEN_NONVISIBLE_REVIEW`

## Same-name object groups
- `SAME_NAME_177d920ddde57c74f8e1ef18863ab511`: 2 objects -> 177d920ddde57c74f8e1ef18863ab511, 177d920ddde57c74f8e1ef18863ab511.001
- `SAME_NAME_Bolt`: 3 objects -> Bolt, Bolt.001, Bolt.002
- `SAME_NAME_Circle`: 8 objects -> Circle, Circle.001, Circle.002, Circle.003, Circle.006, Circle.007, Circle.009, Circle.011
- `SAME_NAME_F2`: 2 objects -> F2, F2.001
- `SAME_NAME_Mball`: 2 objects -> Mball.008, Mball.011
- `SAME_NAME_Plane`: 74 objects -> Plane, Plane.001, Plane.002, Plane.003, Plane.004, Plane.005, Plane.006, Plane.007, Plane.008, Plane.009, Plane.010, Plane.011, Plane.012, Plane.013, Plane.014, Plane.015, Plane.016, Plane.017, Plane.018, Plane.019, Plane.020, Plane.021, Plane.022, Plane.023, Plane.024, Plane.025, Plane.026, Plane.027, Plane.028, Plane.029 ...

## Shared mesh-data groups
- `MESH::Meshy_Left_Standing_Candidate.006`: 2 objects -> F2, F2.001

## Notes
- Same-name groups were kept together under their most likely category instead of being split into separate backup/duplicate collections.
- Hidden non-visible objects that are not part of a same-name group were placed under `08_HIDDEN_NONVISIBLE_REVIEW`.
- Visible generic imported car/sign parts such as `Plane`, `Circle`, and `Bolt` were grouped together instead of deleted.
- The current hoodie proxy and original hoodie remain intact; this pass does not decide which clothing object to keep.