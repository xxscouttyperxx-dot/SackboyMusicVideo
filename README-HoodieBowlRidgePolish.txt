HOODIE BOWL RIDGE POLISH V1

This package is a hoodie-only shape polish pass.

It:
- renames the main hoodie object to SACKBOY_Hoodie_Main
- renames duplicate hoodie-like meshes to SACKBOY_Hoodie_Duplicate_##
- creates a new hoodie-only shape key: HOODIEFIT_BowlRidgePolish_v1
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- repositions focused cameras using the hoodie bounds instead of the F2 bounds
- rounds/feathers the ridge on the top of the hood
- shapes the hood toward a cleaner concave bowl around Sackboy's head
- keeps the rim vertically open
- reports vertex count, face count, and before/after dimensions
- preserves reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieBowlRidgePolish_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieBowlRidgePolish.ps1
.\Apply-HoodieBowlRidgePolish.ps1
.\Validate-HoodieBowlRidgePolish.ps1
.\Publish-CurrentReview.ps1
