# Current Baseline Annotation v1

## Safety
- Audit/render/report only.
- No objects were edited, deleted, moved, renamed, hidden/unhidden, or saved.
- Normal current_review cleanup rule resumed: old review images were removed before this run.

## Current counts
- total_objects: 216
- visible_objects: 205
- hidden_objects: 11
- mesh_objects: 188
- camera_objects: 12
- light_objects: 9
- duplicate_base_name_group_count: 6
- duplicate_base_name_object_count: 91
- shared_data_group_count: 1
- multi_collection_object_count: 0

## Category counts
- Cameras: 13
- Character: 8
- Clothing - Hoodie / Top: 1
- Clothing - Lower / Shoes: 2
- Environment: 42
- Hero Car: 2
- Lighting / Reflections: 26
- Props / Signs / Decor: 3
- Unsorted / Review: 119

## Duplicate base-name groups
- `177d920ddde57c74f8e1ef18863ab511`: 2 -> 177d920ddde57c74f8e1ef18863ab511, 177d920ddde57c74f8e1ef18863ab511.001
- `Bolt`: 3 -> Bolt, Bolt.001, Bolt.002
- `Circle`: 8 -> Circle, Circle.001, Circle.002, Circle.003, Circle.006, Circle.007, Circle.009, Circle.011
- `F2`: 2 -> F2, F2.001
- `Mball`: 2 -> Mball.008, Mball.011
- `Plane`: 74 -> Plane, Plane.001, Plane.002, Plane.003, Plane.004, Plane.005, Plane.006, Plane.007, Plane.008, Plane.009, Plane.010, Plane.011, Plane.012, Plane.013, Plane.014, Plane.015, Plane.016, Plane.017, Plane.018, Plane.019, Plane.020, Plane.021, Plane.022, Plane.023, Plane.024, Plane.025, Plane.026, Plane.027, Plane.028, Plane.029, Plane.030, Plane.031, Plane.032, Plane.033, Plane.034, Plane.035, Plane.036, Plane.037, Plane.038, Plane.039 ...

## Shared mesh-data groups
- `MESH::Meshy_Left_Standing_Candidate.006`: 2 -> F2, F2.001

## Current hoodie candidates
- `SACKBOY_Hoodie_EditProxy` visible=True verts=245107 faces=489016 collections=HOODIE

## Current character candidates
- `F2` visible=True verts=33625 faces=63717 data_users=2 collections=Main Model
- `F2.001` visible=False verts=33625 faces=63717 data_users=2 collections=Main Model
- `Handlebars.001` visible=True verts=4352 faces=4791 data_users=1 collections=PROPS
- `HERO_LampArm_0` visible=True verts=36 faces=20 data_users=1 collections=LIGHTS_AND_REFLECTION_HELPERS
- `HERO_LampArm_1` visible=True verts=36 faces=20 data_users=1 collections=LIGHTS_AND_REFLECTION_HELPERS
- `HERO_StoreMall_DeepBody` visible=True verts=8 faces=6 data_users=1 collections=ENVIRONMENT_AND_PARKING
- `L.Eye` visible=True verts=482 faces=512 data_users=1 collections=Main Model
- `Mball.008` visible=True verts=1510 faces=1893 data_users=1 collections=SAME_NAME_Mball
- `Mball.011` visible=True verts=1930 faces=2419 data_users=1 collections=SAME_NAME_Mball
- `R.Eye` visible=True verts=482 faces=512 data_users=1 collections=Main Model
- `SACKBOY_Hoodie_EditProxy` visible=True verts=245107 faces=489016 data_users=1 collections=HOODIE

## New review renders
- `01_CurrentSceneWide_SOLID.png` camera=`CAM_SceneWide` mode=solid
- `02_CurrentSceneWide_RENDERED.png` camera=`CAM_SceneWide` mode=rendered
- `03_CurrentCharacterThreeQuarter_SOLID.png` camera=`CAM_F2_ThreeQuarter` mode=solid
- `04_CurrentCharacterThreeQuarter_RENDERED.png` camera=`CAM_F2_ThreeQuarter` mode=rendered
- `05_CurrentHoodFront_SOLID.png` camera=`CAM_Hood_Front` mode=solid
- `06_CurrentHoodLeftSide_SOLID.png` camera=`CAM_Hood_LeftSide` mode=solid
- `07_CurrentHoodRightSide_SOLID.png` camera=`CAM_Hood_RightSide` mode=solid

## Notes for next pass
- Treat the current visible character and current visible hoodie/clothing as the new baseline.
- Do not reintroduce duplicate cleanup unless requested.
- Before clothing fit, inspect hoodie candidates and seam/open-boundary diagnostics.