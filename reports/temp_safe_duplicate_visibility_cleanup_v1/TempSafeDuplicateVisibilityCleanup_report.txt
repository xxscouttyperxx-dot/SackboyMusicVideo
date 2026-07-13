# Temp Safe Duplicate Visibility Cleanup v1

## What I found from the audit
- Main cause of repeated highlighted Outliner labels: **multi-collection linking**, not true duplicates.
- Multi-collection objects before: 40
- Duplicate base-name groups before: 6
- Shared mesh-data groups before: 1

## What this package changed
- HERO_BlackSkateShoe_L_WhiteSole: archived hidden helper / set hide_viewport=true hide_render=true hide_select=true
- HERO_BlackSkateShoe_R_WhiteSole: archived hidden helper / set hide_viewport=true hide_render=true hide_select=true
- MOUTH_CUT_GUIDE_Data: archived hidden helper / set hide_viewport=true hide_render=true hide_select=true

## What it deliberately did NOT touch
- Did not delete anything.
- Did not hide any currently visible object.
- Did not touch the visible current Sackboy character.
- Did not touch the visible current hoodie/clothing.
- Did not touch the Audi/car Plane/Circle/Bolt parts because those are visible imported asset pieces, not safe duplicates.
- Did not unlink multi-collection objects yet, because that is organization cleanup and should be reviewed before changing collection structure.

## Important exact findings
- `F2` and `F2.001` are the only shared mesh-data group. `F2` is visible. `F2.001` is hidden/render-disabled. They share the same mesh data-block.
- `SACKBOY_Hoodie_EditProxy` is visible and appears to be your current edited hoodie.
- `SACKBOY_Hoodie_Main` is hidden and appears to be the original/imported hoodie baseline backup.
- Many `Plane`, `Circle`, and `Bolt` names belong to visible Audi/sign asset pieces. The repeated names are generic import names, not automatically removable duplicates.

## Before / after
- Hidden-but-renderable before: 11
- Hidden-but-renderable after: 8
- Total objects before/after: 252 -> 252
- Visible objects before/after: 204 -> 204

## Next recommended cleanup
Next pass should be collection organization only: move/link objects into clean top-level collections without deleting mesh objects. I recommend organizing first, then deciding what to remove.