HOODIE CAMERA CLEANUP SHAPE FIX V1

This package responds to the latest camera and hoodie-shape feedback.

It:
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_CameraCleanupShapeFix_v1
- deletes old CAM_REVIEW_* duplicate cameras and recreates a minimal camera set
- pushes the wire camera back and isolates the hoodie for the wire render so scene/camera/light wireframes do not look like hoodie spikes
- raises the shoulder collar seams
- pulls the lower hood sides back out and down
- feathers/reduces the rear hood protrusion in side profile
- keeps sleeve thickness more uniform near the shoulder root
- uses 960x540 Workbench evidence renders
- reports vertex/face counts, touched vertices, smoothed vertices, max movement, camera cleanup, and dimensions
- preserves reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieCameraCleanupShapeFix_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieCameraCleanupShapeFix.ps1
.\Apply-HoodieCameraCleanupShapeFix.ps1
.\Validate-HoodieCameraCleanupShapeFix.ps1
.\Publish-CurrentReview.ps1
