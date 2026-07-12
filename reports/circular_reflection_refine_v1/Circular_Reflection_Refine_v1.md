# Circular Reflection Refine v1

## What changed
- Old reflection cards/overlays removed: **6**
- Circular reflection-only cards created: **6**
- Red/yellow/green spotlights preserved/tuned: **3**
- Glass material slots tuned: **11**

## Important
- This pass keeps the successful Cycles-based reflection approach.
- `FX_ReflectCard_*` objects are smaller circular emissive sources.
- They remain hidden from the direct camera and visible to glossy / transmission rays for storefront reflections.
- No character deformation was applied in this pass.

## Locked
- Underglow locked to: **[-1.522953, 5.177517, 0.075276]**