Collar Bridge Repair v1O

This is the recovery/fix pass after v1N over-moved the collar region and distorted the side/shoulder area.

What it does:
- Sets SEAMSEAT_CollarParallelSnap_v1N to 0 to remove the damaging spike/stretch.
- Does NOT deform hoodie vertices.
- Creates a separate cloth collar bridge seam object named SACKBOY_CollarGapBridge_v1O.
- The bridge is a fabric band/gasket around the hood-to-sweater intersection to cover the visible collar gap.
- It uses the hoodie material when possible.
- It renders the DIAG_L.Arm and DIAG_R.Arm views because those are the best side collar gap views.

Why this method:
- Snapping hundreds of existing hoodie verts damaged the shoulder/armpit region.
- A separate bridge object fixes the visible gap without touching armpits/shoulders.
- It is reversible: hide/delete SACKBOY_CollarGapBridge_v1O or turn v1N back on/off for comparison.

Manual checks:
- Confirm SEAMSEAT_CollarParallelSnap_v1N value is 0.
- Confirm SACKBOY_CollarGapBridge_v1O is visible.
- Inspect POST_02 and POST_03 side collar renders.
