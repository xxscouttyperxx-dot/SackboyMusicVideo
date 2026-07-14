# Collar Bridge Repair v1O

- Disabled `SEAMSEAT_CollarParallelSnap_v1N` to remove side/shoulder distortion.
- Created bridge object: `SACKBOY_CollarGapBridge_v1O`
- The bridge is a separate collar seam/gasket object, so it does not deform armpit or shoulder vertices.
- Bridge vertices/faces: **384 / 576**
- Hoodie boundary edges unchanged: **371**
- Hoodie boundary loops unchanged: **10**
- v1N value: **1.0 -> 0.0**

Manual revert: hide/delete `SACKBOY_CollarGapBridge_v1O` or set `SEAMSEAT_CollarParallelSnap_v1N` back to 1 for comparison.
