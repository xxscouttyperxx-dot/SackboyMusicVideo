HOODIE SIDE DOME CORRECTION V1C

This package follows your latest directional correction instructions.

It:
- keeps F2/Sackboy untouched
- keeps all F2 BODYFIT shape keys disabled
- creates hoodie-only shape key: HOODIEFIT_SideDomeCorrection_v1C
- from the front view:
  - moves the left convex depression down and left/outward
  - moves the right convex depression down and right/outward
- from side views:
  - moves rear/lower droop up and outward on both sides
  - feathers the correction into the hood silhouette
- raises all review cameras so the hood top remains visible
- pushes the wire check camera up/back so wire termination at the top is more visible
- writes text/json reports only to reports\hoodie_side_dome_correction_v1C
- writes current images only to renders\current_review
- preserves scene lighting, car, reflections, underglow, asphalt, sky/HDRI, and storefronts

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieSideDomeCorrection_v1C.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieSideDomeCorrection_v1C.ps1
.\Apply-HoodieSideDomeCorrection_v1C.ps1
.\Validate-HoodieSideDomeCorrection_v1C.ps1
.\Publish-CurrentReview.ps1
