HOODIE SURFACE DATA REPAIR V1F

This package responds to the request to:
- check the persistent wire spikes more specifically
- log extreme depression/ridge positions
- visualize depressions/ridges/irregularities
- make a stronger data-driven repair to the hood surface

It:
- keeps F2/Sackboy untouched
- keeps all F2 BODYFIT shape keys disabled
- creates hoodie-only shape key: HOODIEFIT_SurfaceDataRepair_v1F
- measures local radial disparity between hood-side vertices and their neighbor average
- logs max depression/ridge values before and after
- stores top depression/ridge vertex coordinates in the JSON report
- renders 05_DepressionRidgeMarkers.png:
  - red = ridge/outward extreme
  - blue = depression/inward extreme
- renders 06_ActualLongEdgeAudit.png:
  - actual long topology edges directly, without using the Wireframe modifier
- pushes inward depression extremes outward
- pulls ridge extremes toward local neighbor average
- applies masked multi-pass relaxation to smooth hard valley boundaries
- preserves the front rim/opening
- stores text/json reports under reports\hoodie_surface_data_repair_v1F
- keeps renders\current_review image-only

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieSurfaceDataRepair_v1F.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieSurfaceDataRepair_v1F.ps1
.\Apply-HoodieSurfaceDataRepair_v1F.ps1
.\Validate-HoodieSurfaceDataRepair_v1F.ps1
.\Publish-CurrentReview.ps1
