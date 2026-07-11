PARKING TEXTURE DECAL / FIT PREP V1

This package responds to the asphalt/paint feedback:
- makes the imported "Asphalt ground" object visible again
- flattens the imported asphalt mesh so it keeps its dirty/detail material but loses the slope
- hides ENV_Asphalt to avoid z-fighting
- hides the old raised paint-strip meshes
- creates new zero-thickness flat paint decal planes just above the asphalt
- places the hatch/manhole on the active asphalt surface
- scans current lights without modifying them
- records the red/white/amber/green reflection-light plan for a later package
- records character/clothing fit dimensions without deforming body or clothes

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_ParkingTextureDecal_FitPrep_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-ParkingTextureDecalFitPrep.ps1
.\Apply-ParkingTextureDecalFitPrep.ps1
.\Validate-ParkingTextureDecalFitPrep.ps1
.\Publish-CurrentReview.ps1
