Sackboy Clothing / Accessory Bind v1

This stage:
- transfers F2's approved deform weights to Lowerpoly hoodie
- transfers F2's approved deform weights to Cargo pants
- adds one Armature modifier to each clothing mesh
- rigidly parents L.Eye and R.Eye to the head bone
- rigidly parents Plane.001 to foot.L
- rigidly parents Plane.022 to foot.R
- preserves F2_DEFORMATION_TEST_V1_2
- preserves production frames 1-120 and the scene frame range

Weight transfer:
- uses the nearest F2 surface triangle
- barycentrically interpolates F2's existing vertex weights
- keeps the strongest four influences per clothing vertex
- normalizes every clothing vertex to a total deform weight of 1.0

Safety:
- requires the approved 22-bone rig and existing F2 binding
- requires clothing to be unbound and without vertex groups
- requires eyes and shoes to be unparented
- validates zero rest-pose visual movement
- validates hoodie response at frame 205
- validates pants response at frame 235
- validates left/right shoes at frames 245/255
- validates eyes at frame 265
- verifies F2, armature rest bones, deformation-test action, and protected scene objects remain unchanged

The shoes are rigidly attached to foot bones for this first animation rig. Toe-roll
controls may be added later if the dance requires visible forefoot articulation.
