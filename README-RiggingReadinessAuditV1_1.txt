Rigging Readiness Audit v1.1

Fixes Blender 5.1 compositor API compatibility. The earlier deprecation warnings were harmless; the actual failure was Scene.node_tree not existing.

Rigging Readiness Audit v1

Strictly read-only.

Inventories the completed pre-rigging scene:
- character and clothing meshes
- hands, shoes, mouth materials
- vertex groups and shape keys
- existing armatures, modifiers and constraints
- parenting and collections
- lightning, fog and cloud assets
- actions and animation data
- cameras, lights, render/world/compositor settings
- external and missing files
- likely rigging candidates

Outputs are written under:
reports/rigging_readiness_audit_v1

A separate optional script pushes only blender/sackboy_scene.blend.
