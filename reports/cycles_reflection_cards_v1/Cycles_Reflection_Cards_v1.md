# Cycles Reflection Cards v1

## What changed
- Removed any visible FX_GlassStreak / FX_WindowGlow leftovers.
- Cycles reflection-only cards created: **6**
- Red/yellow/green traffic spotlights preserved/tuned: **3**
- Glass material slots tuned: **11**
- Scene render engine was set to Cycles for reflection proof renders.

## Important
- No visible line/streak overlays were created.
- `FX_ReflectCard_*` objects are hidden from direct camera rays where Cycles visibility is supported.
- They remain visible to glossy/reflection rays so storefront glass can catch the traffic colors.
- This is the cleaner method compared with the rejected floating streak draft.

## Locked
- Underglow locked to: **[-1.522953, 5.177517, 0.075276]**
- Car, asphalt, parking paint strips, approved amber lights, sky/HDRI, character, and clothing were preserved.
- Character deformation was not applied.