HOODIE BOWL RIM REFINE V1

This package responds to the material-preview/solid-shape feedback.

It:
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_BowlRimRefine_v1
- raises the remaining top ridge a little more
- feathers the ridge into the hood bowl
- vertically widens the hood rim
- reduces the folded/convex lower-side shape by opening the lower sides outward
- uses smaller 960x540 Workbench evidence renders instead of full Cycles renders
- includes material-style, solid gray, and wire/edge evidence views
- uses pulled-back cameras targeted at hoodie bounds
- reports vertex count, face count, touched vertices, max vertex movement, and before/after dimensions
- restores the original render engine after evidence renders
- preserves reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieBowlRimRefine_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieBowlRimRefine.ps1
.\Apply-HoodieBowlRimRefine.ps1
.\Validate-HoodieBowlRimRefine.ps1
.\Publish-CurrentReview.ps1
