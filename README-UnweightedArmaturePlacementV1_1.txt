Unweighted Armature Placement v1.1

Compatibility fix: Blender 5.1 does not accept OCTAHEDRAL as an Object.display_type. The armature object now uses SOLID display while the Armature datablock uses OCTAHEDRAL bone display.

Unweighted Armature Placement v1

Creates:
- Collection: RIGGING_PREVIEW
- Armature object: SACKBOY_RIG_PLACEMENT_V1
- 22 placement/deform bones:
  root, pelvis, spine, chest, neck, head
  clavicle.L/R, upper_arm.L/R, forearm.L/R, hand.L/R
  thigh.L/R, shin.L/R, foot.L/R, toe.L/R

This stage does NOT:
- parent character objects
- create vertex groups
- create Armature modifiers
- calculate automatic weights
- create IK constraints
- pose or animate the rig
- alter lightning, fog, clouds, lamps, car, cameras, materials or environment

Bone placement is derived from the current F2 world-space bounds and stylized Sackboy proportions.
The armature is shown in front for visual inspection and can be adjusted before binding.
