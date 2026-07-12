HOODIE CROWN SMOOTH EXPAND V1

This package continues from the safer hoodie-only direction.

It:
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_CrownSmoothExpand_v1
- continues expanding the hood crown to better contain Sackboy's massive head silhouette
- tries to fix the hood-top dip / inside-out overlap look by smoothing and lifting the crown top
- smooths crown transition areas to avoid banded indentations
- lifts/softens the sleeve elbow valley to reduce the "two camel humps" look
- preserves reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- does not deform pants, shoes, or F2 in this pass

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieCrownSmoothExpand_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieCrownSmoothExpand.ps1
.\Apply-HoodieCrownSmoothExpand.ps1
.\Validate-HoodieCrownSmoothExpand.ps1
.\Publish-CurrentReview.ps1
