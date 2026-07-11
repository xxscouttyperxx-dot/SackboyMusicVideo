# Scene Cleanup / Flat Asphalt v1B

## Asphalt / Paint
- Flat asphalt target: **ENV_Asphalt**
- Flat plane z: **0.18075430393218994**
- Paint objects adjusted: **48**
- Hidden bumpy imported asphalt: **Asphalt ground**

## Decimate Preview Verification
- **Apricot Pullover Hoodie** | modifier=True | ratio=0.25 | faces=489064
- **Utility Box (Photoscanned)** | modifier=True | ratio=0.699999988079071 | faces=23700
- **Lid.001** | modifier=True | ratio=0.699999988079071 | faces=23160

## Current Light Scan
- **HERO_CarAmberHoodRead** | type=SPOT | loc=[5.265154, 1.978295, 5.190777] | energy=100.0 | color=[1.0, 0.257203, 0.006592] | spot_size=0.949999988079071 | spot_blend=0.6499999761581421
- **HERO_CarAmberRoofRead** | type=SPOT | loc=[-5.186506, 1.995343, 5.201615] | energy=100.00001525878906 | color=[1.0, 0.216022, 0.00379] | spot_size=1.0499999523162842 | spot_blend=0.7200000286102295
- **HERO_CarWarmSideGlint** | type=SPOT | loc=[0.007344, 22.906092, 7.155601] | energy=90.0 | color=[1.0, 0.38, 0.08] | spot_size=0.8500000238418579 | spot_blend=0.800000011920929
- **HERO_CyanUnderglow_Area** | type=AREA | loc=[-1.522953, 5.177517, 0.075276] | energy=160.0 | color=[0.0, 0.55, 1.0] | spot_size=None | spot_blend=None
- **V2B_OverheadAmber_0** | type=AREA | loc=[-5.222266, 2.649782, 5.278863] | energy=520.0 | color=[1.0, 0.37, 0.055] | spot_size=None | spot_blend=None
- **V2B_OverheadAmber_1** | type=AREA | loc=[5.284363, 2.653402, 5.278863] | energy=300.0 | color=[1.0, 0.37, 0.055] | spot_size=None | spot_blend=None

## Reflection Lighting Plan
- Colored off-scene spotlights for glass reflections are a good idea, but this pass does not add them.
- That should be a separate package so your newly tuned amber lighting remains preserved.

## Locked Items
- Existing lights were scanned only and not changed.
- Car, storefront, sky/world/HDRI, and character hands were not changed.