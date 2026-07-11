# Parking Texture Decal / Fit Prep v1

## Parking Surface
- Active visible asphalt: **Asphalt ground**
- Asphalt flattened at z: **1.6371204853057861**
- ENV_Asphalt hidden to avoid z-fighting: **True**

## Paint Decals
- Old physical paint-strip meshes hidden: **48**
- Flat decal planes created: **48**
- Decal z: **1.6391204853057861**

## Hatch / Manhole
- Hatch/manhole objects adjusted: **1**

## Character / Clothing Fit Scan
- **F2** | present | dims=[2.783371, 1.475343, 2.749408] | faces=60930 | modifiers=[]
- **Apricot Pullover Hoodie** | present | dims=[2.277528, 1.091159, 1.549869] | faces=489064 | modifiers=[{'name': 'OPT_PREVIEW_DECIMATE', 'type': 'DECIMATE', 'ratio': 0.25}]
- **Cargo pants** | present | dims=[1.559261, 0.898337, 1.052398] | faces=16424 | modifiers=[{'name': 'Collision', 'type': 'COLLISION', 'ratio': None}]
- **Plane.001** | present | dims=[0.626516, 0.950595, 0.372303] | faces=10800 | modifiers=[]
- **Plane.022** | present | dims=[0.626517, 0.950595, 0.372303] | faces=10800 | modifiers=[{'name': 'WeightedNormal', 'type': 'WEIGHTED_NORMAL', 'ratio': None}, {'name': 'WeightedNormal.001', 'type': 'WEIGHTED_NORMAL', 'ratio': None}]

## Current Light Scan
- **HERO_CarAmberHoodRead** | type=SPOT | loc=[5.265154, 1.978295, 5.190777] | energy=100.0 | color=[1.0, 0.257203, 0.006592] | spot_size=0.949999988079071 | spot_blend=0.6499999761581421
- **HERO_CarAmberRoofRead** | type=SPOT | loc=[-5.186506, 1.995343, 5.201615] | energy=100.00001525878906 | color=[1.0, 0.216022, 0.00379] | spot_size=1.0499999523162842 | spot_blend=0.7200000286102295
- **HERO_CarWarmSideGlint** | type=SPOT | loc=[0.007344, 22.906092, 7.155601] | energy=90.0 | color=[1.0, 0.38, 0.08] | spot_size=0.8500000238418579 | spot_blend=0.800000011920929
- **HERO_CyanUnderglow_Area** | type=AREA | loc=[-1.522953, 5.177517, 0.075276] | energy=160.0 | color=[0.0, 0.55, 1.0] | spot_size=None | spot_blend=None
- **V2B_OverheadAmber_0** | type=AREA | loc=[-5.222266, 2.649782, 5.278863] | energy=520.0 | color=[1.0, 0.37, 0.055] | spot_size=None | spot_blend=None
- **V2B_OverheadAmber_1** | type=AREA | loc=[5.284363, 2.653402, 5.278863] | energy=300.0 | color=[1.0, 0.37, 0.055] | spot_size=None | spot_blend=None

## Direction Locked In
- For window reflections, use **red / white / amber / green** off-scene spotlights only. No blue.
- Do not force clothing onto Sackboy yet. Refine body/head/torso proportions first, then deform hoodie/pants/shoes to fit, then rig.
- Existing amber lights, car, storefront, and sky/HDRI were not changed.