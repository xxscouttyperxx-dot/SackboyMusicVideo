GRID PARKING / REFLECTION LIGHTS V1

This package:
- lowers the imported Asphalt ground to the world grid and keeps it visible
- restores the original parking paint strip meshes at grid level
- removes generated PARKING_DECAL objects
- locks HERO_CyanUnderglow_Area back to [-1.522953, 5.177517, 0.075276]
- adds far-end red/white/amber/green reflection spotlights for storefront glass tests
- does not add blue lighting
- does not deform Sackboy yet; it records fit data and next deformation plan

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_GridParking_ReflectionLights_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-GridParkingReflectionLights.ps1
.\Apply-GridParkingReflectionLights.ps1
.\Validate-GridParkingReflectionLights.ps1
.\Publish-CurrentReview.ps1
