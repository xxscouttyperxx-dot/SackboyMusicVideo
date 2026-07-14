Collar Parallel Snap v1N

Goal:
- Close the largest remaining hood-to-sweater collar gaps more aggressively.
- Use the DIAG_L.Arm and DIAG_R.Arm cameras as collar-side review views, because those are actually the best collar-gap cameras.
- Work only on the collar/hood-sweater intersection area.

Method:
- Creates/updates reversible shape key: SEAMSEAT_CollarParallelSnap_v1N
- Uses current visual mesh state including prior active shape keys.
- Selects collar boundary vertices near the side/front/back collar zones.
- Snaps whole broken collar sections toward nearest parallel boundary seam from a different boundary component.
- Repeats internally in several rounds until the average measured gap reduction is significant.
- Does not change topology; boundary edge/loop counts should stay unchanged.

Manual comparison:
- Select SACKBOY_Hoodie_EditProxy.
- Object Data Properties > Shape Keys.
- Toggle SEAMSEAT_CollarParallelSnap_v1N between 1 and 0.
