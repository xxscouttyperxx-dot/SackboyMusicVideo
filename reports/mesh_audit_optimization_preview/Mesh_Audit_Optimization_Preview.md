# Mesh Audit / Optimization Preview v1

This pass preserves the current scene baseline, audits imported clothing/props, and adds a non-destructive parking-paint snap preview.

## High-Poly Candidates
- **Apricot Pullover Hoodie** | category=clothing | faces=489064 | verts=257116 | suggested decimate ratio=0.2
- **Utility Box (Photoscanned)** | category=prop | faces=23700 | verts=12028 | suggested decimate ratio=0.7
- **Lid.001** | category=prop | faces=23160 | verts=21254 | suggested decimate ratio=0.7

## All Audited Assets
- **Apricot Pullover Hoodie** | clothing | faces=489064 | verts=257116 | dims=[2.27753, 1.09128, 1.54981] | collections=['Apricot Pullover Hoodie']
- **Utility Box (Photoscanned)** | prop | faces=23700 | verts=12028 | dims=[1.20927, 0.53493, 1.61522] | collections=['Utility Box (Photoscanned)']
- **Lid.001** | prop | faces=23160 | verts=21254 | dims=[1.05391, 1.26036, 0.13817] | collections=['Large Trash Can']
- **Cargo pants** | clothing | faces=16424 | verts=16507 | dims=[1.55926, 0.89834, 1.0524] | collections=['Cargo pants']
- **Asphalt ground** | environment | faces=16154 | verts=16441 | dims=[70.78242, 70.33268, 4.03217] | collections=['Asphalt ground']
- **Traffic Cone (Photoscanned)** | prop | faces=12802 | verts=6658 | dims=[0.45696, 0.46684, 0.80072] | collections=['Traffic Cone (Photoscanned)']
- **Can.001** | prop | faces=12327 | verts=11142 | dims=[1.13363, 1.18465, 1.64258] | collections=['Large Trash Can']
- **Ribbing.001** | prop | faces=11940 | verts=11332 | dims=[1.1229, 1.14015, 1.60965] | collections=['Large Trash Can']
- **Plane.001** | clothing | faces=10800 | verts=10292 | dims=[0.62652, 0.95059, 0.3723] | collections=['Shoes']
- **Plane.022** | clothing | faces=10800 | verts=10292 | dims=[0.62652, 0.95059, 0.3723] | collections=['Shoes']
- **Handlebars.001** | prop | faces=4791 | verts=4352 | dims=[0.68882, 0.19654, 0.21106] | collections=['Large Trash Can']
- **Wheel.001** | prop | faces=3346 | verts=3143 | dims=[1.09293, 0.3856, 0.38559] | collections=['Large Trash Can']
- **Lid Pins.001** | prop | faces=2970 | verts=2780 | dims=[0.74702, 0.04281, 0.04281] | collections=['Large Trash Can']
- **Mball.011** | environment | faces=2419 | verts=1930 | dims=[0.05926, 0.05791, 0.02755] | collections=['No Parking Sign Board']
- **Mball.008** | environment | faces=1893 | verts=1510 | dims=[0.26548, 0.02079, 0.34143] | collections=['No Parking Sign Board']
- **177d920ddde57c74f8e1ef18863ab511** | environment | faces=872 | verts=874 | dims=[0.42658, 0.02706, 0.55954] | collections=['No Parking Sign Board']
- **Bolt.001** | environment | faces=608 | verts=586 | dims=[0.013, 0.01044, 0.20103] | collections=['No Parking Sign Board']
- **Plane.029** | prop | faces=512 | verts=545 | dims=[0.97148, 0.97148, 0.00838] | collections=['Cast iron sewer hatch']
- **Axle.001** | prop | faces=320 | verts=302 | dims=[0.91977, 0.03333, 0.03333] | collections=['Large Trash Can']
- **Bolt** | environment | faces=304 | verts=293 | dims=[0.16502, 0.17825, 0.00931] | collections=['No Parking Sign Board']
- **Stop road sign** | prop | faces=267 | verts=253 | dims=[1.50013, 0.19677, 4.53016] | collections=['Stop road sign']
- **Plane.023** | environment | faces=126 | verts=132 | dims=[0.26758, 0.26759, 0.02] | collections=['No Parking Sign Board']
- **Cylinder** | environment | faces=51 | verts=60 | dims=[0.0468, 0.04682, 1.9893] | collections=['No Parking Sign Board']
- **177d920ddde57c74f8e1ef18863ab511.001** | environment | faces=6 | verts=8 | dims=[0.25264, 0.01386, 0.33347] | collections=['No Parking Sign Board']
- **ENV_Asphalt** | environment | faces=6 | verts=8 | dims=[36.0, 36.0, 0.2] | collections=['ENV_ParkingLot']
- **HERO_BlackSkateShoe_L_FlameAccent_0** | clothing | faces=6 | verts=8 | dims=[0.07793, 0.08852, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_L_FlameAccent_1** | clothing | faces=6 | verts=8 | dims=[0.07793, 0.08852, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_L_FlameAccent_2** | clothing | faces=6 | verts=8 | dims=[0.07793, 0.08852, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_L_WhiteSole** | clothing | faces=6 | verts=8 | dims=[1.00201, 0.8557, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_R_FlameAccent_0** | clothing | faces=6 | verts=8 | dims=[0.07793, 0.08852, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_R_FlameAccent_1** | clothing | faces=6 | verts=8 | dims=[0.07793, 0.08852, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_R_FlameAccent_2** | clothing | faces=6 | verts=8 | dims=[0.07793, 0.08852, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_BlackSkateShoe_R_WhiteSole** | clothing | faces=6 | verts=8 | dims=[1.00201, 0.8557, 0.09898] | collections=['HERO_CHARACTER_WARDROBE_V1']
- **HERO_MaterialSwatch_Hoodie** | clothing | faces=6 | verts=8 | dims=[0.11, 0.11, 0.11] | collections=['HERO_CHARACTER_MATERIAL_GUIDES']
- **HERO_MaterialSwatch_ShoeBlack** | clothing | faces=6 | verts=8 | dims=[0.11, 0.11, 0.11] | collections=['HERO_CHARACTER_MATERIAL_GUIDES']
- **HERO_MaterialSwatch_ShoeWhite** | clothing | faces=6 | verts=8 | dims=[0.11, 0.11, 0.11] | collections=['HERO_CHARACTER_MATERIAL_GUIDES']

## Parking Paint Snap Preview
- Asphalt target: **Asphalt ground**
- Parking paint objects updated: **55**

## Optimization Guidance
- Clothes and deforming meshes should be reduced carefully; use milder ratios first.
- Static props like signs, cones, hatch covers, and utility boxes are safer decimation candidates.
- Review the before/after shape once we do the later automatic decimation pass.