SURFACE REPAIR / CHARACTER FIT SCAN V1B

This package is correctly packaged at the project root level.

It:
- makes ENV_Asphalt visible
- keeps the bumpy imported Asphalt ground hidden
- flattens ENV_Asphalt
- flattens parking paint strips to zero-height planes just above asphalt so they should not touch tires
- raises the manhole/sewer hatch back onto the asphalt surface
- scans current amber light values without modifying them
- scans Sackboy/clothing dimensions for the upcoming anatomical/clothing fit pass
- does not add red/white/amber/green reflection spotlights yet
- does not deform Sackboy or clothing yet

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\Sackboy_Blender_SurfaceRepair_CharacterFitScan_v1" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_SurfaceRepair_CharacterFitScan_v1B.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-SurfaceRepairCharacterFitScan.ps1
.\Apply-SurfaceRepairCharacterFitScan.ps1
.\Validate-SurfaceRepairCharacterFitScan.ps1
.\Publish-CurrentReview.ps1
