Character Spatial / Hierarchy Audit v1

Strictly read-only.

This audit focuses on:
- F2, current visible clothing, eyes, shoes, hands and likely attached character objects
- world-space bounds, dimensions, origins and object transforms
- parent/child relationships and parent inverse matrices
- object data sharing and duplicate-linked meshes
- shape keys and their current values
- existing actions, drivers, constraints and modifiers
- empties/axes near the character
- objects whose origin is far from their visible geometry
- candidate joint landmark estimates for later armature placement
- protected lightning/cloud/fog objects that must not be changed
- shape-key cleanup scope for a later write package

No scene data is changed and the .blend is not saved.
