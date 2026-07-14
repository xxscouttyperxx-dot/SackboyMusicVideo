Armpit Collar Shape Seat v1L

This pass is reversible because it creates/updates a hoodie shape key:
SEAMSEAT_ArmpitCollar_v1L

Targets:
- hood-to-sweater/collar intersection
- left armpit irregularity
- right armpit irregularity
- slight hood-top cleanup only if close boundary candidates exist

What it does:
- No topology changes.
- Boundary counts should stay the same.
- Moves likely matching seam boundary vertices closer together in the shape key.
- Applies a tiny local relax only around the accepted seam seating pairs.
- Plain solid renders only; no colored tube overlays.
- Closeups hide Sackboy/body/accessories.

To manually compare:
- Select SACKBOY_Hoodie_EditProxy.
- Shape Keys panel.
- Toggle SEAMSEAT_ArmpitCollar_v1L value between 1 and 0.
