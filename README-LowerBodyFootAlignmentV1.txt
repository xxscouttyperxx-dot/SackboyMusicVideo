Sackboy Lower-Body / Foot Alignment v1

Adjusts only:
- thigh.L / thigh.R
- shin.L / shin.R
- foot.L / foot.R
- toe.L / toe.R

Placement sources:
- Cargo pants evaluated geometry for hip, knee, and lower-leg centerlines
- Plane.001 and Plane.022 evaluated shoe geometry for ankle, foot, and toe placement

Jumpstyle-oriented placement safeguards:
- hip, knee, and ankle descend monotonically
- knee receives a very small forward bias to establish a stable future IK bend direction
- shin ends inside the shoe instead of above it
- foot and toe bones run through the shoe's interior center plane
- foot and toe move monotonically toward the front of each shoe
- toe endpoint stays inside the visible shoe tip
- both chains remain connected

This stage does not:
- alter the accepted arms, clavicles, spine, head, pelvis, or root
- parent or weight meshes
- add Armature modifiers
- add IK controls or constraints
- alter lightning, fog, clouds, lamps, cameras, car, or environment
