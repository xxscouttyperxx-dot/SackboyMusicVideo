PARKING HEIGHT / UNDERGLOW REPAIR V1

This repairs the issues from Parking Texture Decal / Fit Prep v1:
- lowers the imported Asphalt ground back down to the previous clean surface height
- keeps the imported asphalt visible and flattened
- removes the bad PARKING_DECAL_*ENV_PlazaShell decal
- rebuilds the flat parking paint decals using stricter filtering
- restores HERO_CyanUnderglow_Area to its locked under-car location:
  [-1.522953, 5.177517, 0.075276]
- does not add far-end red/white/amber/green reflection lights yet

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_ParkingHeightUnderglowRepair_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-ParkingHeightUnderglowRepair.ps1
.\Apply-ParkingHeightUnderglowRepair.ps1
.\Validate-ParkingHeightUnderglowRepair.ps1
.\Publish-CurrentReview.ps1
