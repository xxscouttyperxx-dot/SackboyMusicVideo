REMOVE HIDDEN REJECTED FRAMES V1

This package removes the hidden rejected objects you identified in:
PARKING_PAINT_ORIGINALS_HIDDEN

It targets:
- ENV_Glass*
- ENV_Frame*
- ENV_FrameTop*

It preserves:
- white parking paint strips
- imported asphalt
- car and underglow
- approved lights
- sky/HDRI
- character and clothing
- FX_ReflectCard* objects

Important:
FX_ReflectCard* objects are intentional reflection-only emissive cards. They are not the hidden ENV_Glass/ENV_Frame leftovers.

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_RemoveHiddenRejectedFrames_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-RemoveHiddenRejectedFrames.ps1
.\Apply-RemoveHiddenRejectedFrames.ps1
.\Validate-RemoveHiddenRejectedFrames.ps1
.\Publish-CurrentReview.ps1
