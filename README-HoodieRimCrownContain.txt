HOODIE RIM CROWN CONTAIN V1

This package is a hoodie-only polish pass based on your screenshots.

It:
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_RimCrownContain_v1
- stretches the hood rim more vertically/proportionally
- lifts and expands the hood crown using F2's head top as a clearance reference
- targets the red/top show-through artifact by raising the central crown cap
- feathers the crown transition to avoid banded indentations
- preserves sleeve elbow smoothing from the previous pass
- preserves reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- does not deform pants, shoes, or F2

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieRimCrownContain_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieRimCrownContain.ps1
.\Apply-HoodieRimCrownContain.ps1
.\Validate-HoodieRimCrownContain.ps1
.\Publish-CurrentReview.ps1
