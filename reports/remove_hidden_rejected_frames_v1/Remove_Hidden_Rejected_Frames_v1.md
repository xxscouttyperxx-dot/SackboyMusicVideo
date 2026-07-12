# Remove Hidden Rejected Frames v1

## What changed
- Removed hidden rejected ENV_Glass/ENV_Frame objects: **14**
- Removed empty PARKING_PAINT_ORIGINALS_HIDDEN collection: **False**
- White parking paint strips were preserved.
- Car, asphalt, sky/HDRI, approved amber lights, character, and clothing were preserved.
- Character deformation was not applied.

## Reflection card note
- `FX_ReflectCard_*` objects are intentional reflection-only emissive cards.
- They are camera-invisible where Blender supports ray visibility, and are meant to appear in glass reflections.
- The hidden `ENV_Glass*` / `ENV_Frame*` objects were not reflection cards and were removed.

## Locked underglow
- [-1.522953, 5.177517, 0.075276]
