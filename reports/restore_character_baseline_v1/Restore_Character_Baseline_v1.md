# Restore Character Baseline v1

## Changes
- Disabled all `BODYFIT_*` shape key values on `F2`.
- This visually restores the character to the mesh Basis state while preserving the current reflection/scene work.
- Did not delete shape keys; they remain as disabled history for safety.
- Kept the Cycles reflection setup, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting.

## Why
- The previous silhouette pass distorted the character into an unacceptable pitbull/four-leg/snouted shape.
- This reset returns to the first usable character state after the reflection passes instead of trying to sculpt over the distortion.

## Next goal
- Resume with a safer method: fit clothing around the restored body first, then make only small, targeted body tweaks.