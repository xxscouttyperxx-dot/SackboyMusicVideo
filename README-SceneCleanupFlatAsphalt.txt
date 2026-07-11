SCENE CLEANUP / FLAT ASPHALT V1B

This fixes the material-slot error from v1.

It:
- scans current manually tuned light values and writes them to the report
- does not modify existing lights
- hides the bumpy imported Asphalt ground object
- flattens ENV_Asphalt into a clean parking surface
- places parking paint strips directly above the flat asphalt
- removes prior package-generated temporary review cameras
- verifies the existing decimate preview modifiers
- does not add street-reflection lights yet

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_SceneCleanup_FlatAsphalt_v1B.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-SceneCleanupFlatAsphalt.ps1
.\Apply-SceneCleanupFlatAsphalt.ps1
.\Validate-SceneCleanupFlatAsphalt.ps1
.\Publish-CurrentReview.ps1
