HOODIE CAMERA COUNT / SIDE BOWL FIX V1

This package responds to the camera cleanup and hoodie-side/back-shape feedback.

It:
- deletes all existing camera objects and recreates exactly 12 total cameras:
  - 3 F2 reference cameras
  - 1 storefront reflection camera
  - 1 whole-scene camera
  - 4 hood cameras: left side, right side, top, front
  - 3 hidden animation cameras
- writes text/json change files to renders\Project changes
- cleans renders\current_review so only current images remain
- adds hoodie-only shape key: HOODIEFIT_SideBackBowlFix_v1
- raises the shoulder collar seam
- pulls lower hood sides out/down
- rounds the rear hood droop from lower back to mid back
- feathers the rear protrusion into the hood silhouette
- keeps F2 untouched and all BODYFIT keys disabled
- preserves reflections, lights, car, underglow, asphalt, sky/HDRI, and approved scene elements

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieCameraCountSideBowlFix_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieCameraCountSideBowlFix.ps1
.\Apply-HoodieCameraCountSideBowlFix.ps1
.\Validate-HoodieCameraCountSideBowlFix.ps1
.\Publish-CurrentReview.ps1
