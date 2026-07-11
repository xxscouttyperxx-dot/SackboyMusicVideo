# Grid Parking / Reflection Lights v1

## Parking Repair
- Imported asphalt lowered/flattened to grid z: **0.0**
- Paint strips restored from original meshes: **47**
- Generated decal objects removed: **37**
- Hatch/manhole objects adjusted: **1**
- Underglow locked to: **[-1.522953, 5.177517, 0.075276]**

## Reflection Lights
- Added far-end spotlights in **red / white / amber / green** only.
- No blue reflection light was added.
- Existing amber overhead/car lights were not modified.

- **TRAFFIC_REFLECT_Red_BrakeLight** | loc=[-8.0, -18.0, 2.4] | energy=70.0 | color=[1.0, 0.05, 0.02]
- **TRAFFIC_REFLECT_White_Headlight** | loc=[-2.5, -19.5, 2.2] | energy=95.0 | color=[1.0, 0.92, 0.78]
- **TRAFFIC_REFLECT_Amber_StreetTurn** | loc=[3.2, -18.5, 2.5] | energy=75.0 | color=[1.0, 0.42, 0.06]
- **TRAFFIC_REFLECT_Green_SignalBounce** | loc=[8.2, -20.0, 2.6] | energy=45.0 | color=[0.08, 1.0, 0.2]

## Character Fit Scan
- **F2** | present | dims=[2.783371, 1.475343, 2.749408] | faces=60930
- **Apricot Pullover Hoodie** | present | dims=[2.277528, 1.091159, 1.549869] | faces=489064
- **Cargo pants** | present | dims=[1.559261, 0.898337, 1.052398] | faces=16424
- **Plane.001** | present | dims=[0.626516, 0.950595, 0.372303] | faces=10800
- **Plane.022** | present | dims=[0.626517, 0.950595, 0.372303] | faces=10800

## Next Character Deformation Plan
- Refine Sackboy body/head/torso proportions first.
- Then deform hoodie, pants, and shoes around the finalized body.
- Rig only after the visual body/clothing fit is approved.