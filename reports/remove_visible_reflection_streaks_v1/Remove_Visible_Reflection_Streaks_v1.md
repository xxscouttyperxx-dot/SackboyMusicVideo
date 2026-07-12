# Remove Visible Reflection Streaks v1

## What changed
- Removed visible FX_GlassStreak / FX_WindowGlow overlays: **6**
- Preserved reflection-only FX_ReflectCard objects: **6**
- Red/yellow/green traffic lights were preserved.
- Car, asphalt, white parking strips, approved amber lights, sky/HDRI, character, and clothing were preserved.

## Why
- The visible streak overlays were a fallback draft to force reflections in Eevee.
- They showed up as floating/intersecting lines in renders, so they are removed.
- Next reflection attempt should use either better material/probe setup or cards positioned only where they cannot enter camera view.

## Locked underglow
- [-1.522953, 5.177517, 0.075276]