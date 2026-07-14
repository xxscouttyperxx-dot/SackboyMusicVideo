Collar Snap Shape Seat v1M

Goal:
- More aggressively close the large hood-to-sweater/collar gap.
- Work ONLY on the collar/hood-sweater intersection area.
- Do not touch armpits in this pass.

Method:
- Creates/updates a reversible shape key: SEAMSEAT_CollarSnap_v1M
- Computes the current visual hoodie state including existing active shape keys.
- Moves collar boundary vertices toward the nearest matching boundary component using stronger snap seating.
- Does not change topology. Boundary edge/loop counts should remain unchanged.
- Produces plain solid renders with no colored tube overlays.

Manual comparison:
- Select SACKBOY_Hoodie_EditProxy.
- Object Data Properties > Shape Keys.
- Toggle SEAMSEAT_CollarSnap_v1M between 1 and 0.
- You can also toggle SEAMSEAT_ArmpitCollar_v1L to compare previous vs combined seating.
