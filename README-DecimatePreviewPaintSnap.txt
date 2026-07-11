DECIMATE PREVIEW / PAINT SNAP V1B

This package:
- adds non-destructive Decimate preview modifiers to:
  - Apricot Pullover Hoodie at 0.25
  - Utility Box (Photoscanned) at 0.70
  - Lid.001 at 0.70
- creates hidden linked-original backup objects for those preview targets
- improves parking paint snap by placing the paint strips just above the asphalt target and keeping shrinkwrap preview modifiers
- does not apply destructive decimation
- does not modify lights, car, storefront, sky/world/HDRI, no-parking sign, traffic cone, cargo pants, or shoes

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_DecimatePreview_PaintSnap_v1C.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-DecimatePreviewPaintSnap.ps1
.\Apply-DecimatePreviewPaintSnap.ps1
.\Validate-DecimatePreviewPaintSnap.ps1
.\Publish-CurrentReview.ps1
