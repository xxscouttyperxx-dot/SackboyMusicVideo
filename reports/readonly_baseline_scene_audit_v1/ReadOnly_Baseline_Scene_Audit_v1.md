# Read-Only Baseline Scene Audit v1

## Safety
This audit does not edit, delete, move, rename, hide, organize, or save any Blender scene objects.

## Summary
- audit_type: READ ONLY - no scene edits, no object deletes, no save
- blend_file: C:\BlenderProjects\SackboyMusicVideo\Project\blender\sackboy_scene.blend
- total_objects: 252
- visible_objects: 204
- hidden_objects: 48
- mesh_objects: 223
- light_objects: 9
- camera_objects: 12
- collection_count: 46
- duplicate_base_name_group_count: 6
- shared_data_group_count: 1
- multi_collection_object_count: 40
- hidden_but_renderable_guess_count: 11
- likely_old_hidden_object_count: 0
- category_counts: {'Cameras': 13, 'Character / Duplicates': 23, 'Clothing': 14, 'Environment / Props': 45, 'Lighting / Reflections': 26, 'Unsorted / Needs Review': 131}

## Why the same object name can highlight multiple times
One Blender object can be linked into multiple collections. The Outliner may show the same object under every collection that contains it. Selecting that one object highlights every listed occurrence. If you press Delete, Blender deletes the object itself, so all collection listings disappear.

Separate objects can also share the same mesh data-block. If `data_users > 1`, editing mesh data can affect linked copies unless you make that mesh single-user.

## Category counts
- Cameras: 13
- Character / Duplicates: 23
- Clothing: 14
- Environment / Props: 45
- Lighting / Reflections: 26
- Unsorted / Needs Review: 131

## Duplicate base-name groups
- 177d920ddde57c74f8e1ef18863ab511: 2 -> 177d920ddde57c74f8e1ef18863ab511, 177d920ddde57c74f8e1ef18863ab511.001
- Bolt: 3 -> Bolt, Bolt.001, Bolt.002
- Circle: 8 -> Circle, Circle.001, Circle.002, Circle.003, Circle.006, Circle.007, Circle.009, Circle.011
- F2: 2 -> F2, F2.001
- Mball: 2 -> Mball.008, Mball.011
- Plane: 74 -> Plane, Plane.001, Plane.002, Plane.003, Plane.004, Plane.005, Plane.006, Plane.007, Plane.008, Plane.009, Plane.010, Plane.011, Plane.012, Plane.013, Plane.014, Plane.015, Plane.016, Plane.017, Plane.018, Plane.019, Plane.020, Plane.021, Plane.022, Plane.023, Plane.024 ...

## Shared mesh/data-block groups
- MESH::Meshy_Left_Standing_Candidate.006: 2 -> F2, F2.001

## Objects appearing in multiple collections
- Asphalt ground: 2 collections -> Asphalt ground, ENV_PARKING
- Cargo pants: 2 collections -> OPTIMIZATION_PREVIEW_DECIMATE_TARGETS, WARDROBE_IMPORTED
- Cast iron sewer hatch: 2 collections -> Cast iron sewer hatch, ENV_PARKING
- F2: 2 collections -> CHAR_F2, CHAR_Meshy_LeftCandidate_Refined
- F2.001: 2 collections -> CHAR_F2, CHAR_Meshy_LeftCandidate_Refined
- FX_TrafficLight_Green: 2 collections -> FX_REFLECTION_TRAFFIC, WINDOW_REFLECTION_SPOTLIGHTS_FAR_END
- FX_TrafficLight_Red: 2 collections -> FX_REFLECTION_TRAFFIC, WINDOW_REFLECTION_SPOTLIGHTS_FAR_END
- FX_TrafficLight_Yellow: 2 collections -> FX_REFLECTION_TRAFFIC, WINDOW_REFLECTION_SPOTLIGHTS_FAR_END
- HERO_CarAmberHoodRead: 2 collections -> ENV_LIGHTING_APPROVED, HERO_CAR_AMBER_READ
- HERO_CarAmberRoofRead: 2 collections -> ENV_LIGHTING_APPROVED, HERO_CAR_AMBER_READ
- HERO_CarWarmSideGlint: 2 collections -> ENV_LIGHTING_APPROVED, HERO_CAR_AMBER_READ
- HERO_CyanUnderglow_Area: 2 collections -> ENV_LIGHTING_APPROVED, HERO_CAR_UNDERGLOW
- HERO_HParking_CenterSpine: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_0: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_1: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_2: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_3: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_4: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_5: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_6: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row0_Divider_7: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_0: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_1: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_2: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_3: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_4: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_5: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_6: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_HParking_Row1_Divider_7: 4 collections -> ENV_PARKING, HERO_H_PARKING_LAYOUT, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_Underglow_FrontHiddenStrip: 4 collections -> ENV_PARKING, HERO_CAR_UNDERGLOW, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- HERO_Underglow_RearHiddenStrip: 4 collections -> ENV_PARKING, HERO_CAR_UNDERGLOW, PARKING_PAINT_FLAT_ORIGINALS_ACTIVE, PARKING_PAINT_ORIGINALS_HIDDEN
- Lid.001: 2 collections -> Large Trash Can, OPTIMIZATION_PREVIEW_DECIMATE_TARGETS
- No Parking Sign Board: 2 collections -> ENV_PARKING, No Parking Sign Board
- Plane.001: 2 collections -> OPTIMIZATION_PREVIEW_DECIMATE_TARGETS, Shoes
- Plane.022: 2 collections -> OPTIMIZATION_PREVIEW_DECIMATE_TARGETS, Shoes
- SACKBOY_Hoodie_EditProxy: 3 collections -> HERO_IMPORTED_CLOTHING_CANDIDATES, OPTIMIZATION_PREVIEW_DECIMATE_TARGETS, WARDROBE_IMPORTED
- SACKBOY_Hoodie_Main: 3 collections -> HERO_IMPORTED_CLOTHING_CANDIDATES, OPTIMIZATION_PREVIEW_DECIMATE_TARGETS, WARDROBE_IMPORTED
- Utility Box (Photoscanned): 2 collections -> OPTIMIZATION_PREVIEW_DECIMATE_TARGETS, Utility Box (Photoscanned)
- V2B_OverheadAmber_0: 2 collections -> ENV_LIGHTING_APPROVED, V2B_LIGHTS_OVERHEAD
- V2B_OverheadAmber_1: 2 collections -> ENV_LIGHTING_APPROVED, V2B_LIGHTS_OVERHEAD

## Hidden-but-renderable guess
- CAM_Hood_Front [CAMERA]
- CAM_Hood_LeftSide [CAMERA]
- CAM_Hood_RightSide [CAMERA]
- CAM_Hood_Top [CAMERA]
- CAM_Target [EMPTY]
- FX_TrafficLight_Green [LIGHT]
- FX_TrafficLight_Red [LIGHT]
- FX_TrafficLight_Yellow [LIGHT]
- HERO_BlackSkateShoe_L_WhiteSole [MESH]
- HERO_BlackSkateShoe_R_WhiteSole [MESH]
- MOUTH_CUT_GUIDE_Data [CURVE]

## Likely old hidden objects by name
- None found by name heuristic.

## Heaviest meshes
- SACKBOY_Hoodie_Main: 257116 verts / 489064 faces / visible=False / data_users=1
- SACKBOY_Hoodie_Main_duplicate: 257116 verts / 489064 faces / visible=False / data_users=1
- SACKBOY_Hoodie_Main_lowmesh: 257116 verts / 489064 faces / visible=False / data_users=1
- SACKBOY_Hoodie_EditProxy: 245107 verts / 489016 faces / visible=True / data_users=1
- Plane.074: 62832 verts / 67320 faces / visible=True / data_users=1
- MESHY_LEFT_SOURCE_00: 33504 verts / 66959 faces / visible=False / data_users=1
- MESHY_LEFT_REFINED_00: 33486 verts / 66924 faces / visible=False / data_users=1
- sackboy_scene_manual_v1.blend: 33484 verts / 66916 faces / visible=False / data_users=1
- F2: 33625 verts / 63717 faces / visible=True / data_users=2
- F2.001: 33625 verts / 63717 faces / visible=False / data_users=2
- HANDREFINE_J2B_Working: 30549 verts / 60930 faces / visible=False / data_users=1
- Circle.009: 23528 verts / 24192 faces / visible=True / data_users=1
- Utility Box (Photoscanned): 12028 verts / 23700 faces / visible=True / data_users=1
- Lid.001: 21254 verts / 23160 faces / visible=True / data_users=1
- Circle.003: 24792 verts / 20464 faces / visible=True / data_users=1
- Cargo pants: 16507 verts / 16424 faces / visible=True / data_users=1
- Asphalt ground: 16441 verts / 16154 faces / visible=True / data_users=1
- Plane.077: 14992 verts / 14168 faces / visible=True / data_users=1
- Traffic Cone (Photoscanned): 6658 verts / 12802 faces / visible=True / data_users=1
- Can.001: 11142 verts / 12327 faces / visible=True / data_users=1
- Ribbing.001: 11332 verts / 11940 faces / visible=True / data_users=1
- Plane.001: 10292 verts / 10800 faces / visible=True / data_users=1
- Plane.022: 10292 verts / 10800 faces / visible=True / data_users=1
- Bolt.002: 5440 verts / 5688 faces / visible=True / data_users=1
- Circle.011: 5632 verts / 5120 faces / visible=True / data_users=1

## Suggested collection order only — not applied
1. Character / Duplicates
2. Clothing
3. Hero car
4. Environment / Props
5. Lighting / Reflections
6. Cameras
7. Archive / Hidden, only after approval