# Glass Reflection Visibility v1B

## What changed
- Rebuilt the reflection system around the storefront glass rather than around the far-end lights.
- Camera-invisible reflection cards: **6**
- Subtle on-glass streak overlays: **6**
- Red/yellow/green traffic spotlights: **3**
- Glass material slots tuned: **14**

## Why there are both cards and streaks
- `FX_ReflectCard_*` objects are intended for ray/path reflections and are hidden from direct camera view where Blender supports that visibility.
- `FX_GlassStreak_*` objects are subtle on-glass reflection overlays so the traffic reflection is actually visible in Eevee/rendered view.

## Locked
- Underglow locked to: **[-1.522953, 5.177517, 0.075276]**
- Car, asphalt, parking paint strips, approved amber lights, sky/HDRI, character, and clothing were preserved.
- Character deformation was not applied.