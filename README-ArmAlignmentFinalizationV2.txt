Sackboy Arm Alignment Finalization v2

The previous geometry-window pass selected torso/upper-sleeve samples and used the old hand endpoint as a fallback. That created the visible raised-clavicle M shape and long downward hand bones.

This package replaces that result with clean, straight T-pose arm chains:
- clavicle roots remain centered at the chest
- shoulder, elbow, wrist, and hand endpoint move monotonically outward
- both arm chains share one geometry-derived depth and height
- upper arm, forearm, and hand segments remain connected
- left and right proportions are computed from each side of F2's real bounds

Adjusted only:
- clavicle.L/R
- upper_arm.L/R
- forearm.L/R
- hand.L/R

No mesh, parenting, weighting, modifiers, constraints, actions, effects, cameras, lights, or environment objects are changed.
