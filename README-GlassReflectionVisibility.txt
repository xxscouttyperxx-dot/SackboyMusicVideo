GLASS REFLECTION VISIBILITY V1B

v1B fixes the Blender Object-removed iteration error from v1.

This package:
- preserves car, asphalt, white parking strips, sky/HDRI, approved amber lights, character, and clothing
- keeps red/yellow/green traffic-light concept
- rebuilds reflection cards close to the storefront glass
- uses camera-invisible FX_ReflectCard_* objects where ray visibility supports reflection-only behavior
- adds subtle FX_GlassStreak_* overlays directly on the glass to guarantee visible red/yellow/green reflection streaks in Eevee/rendered view
- tunes glass materials for stronger reflections
- prepares the setup for later keyframing of red/yellow/green intensity
- does not deform Sackboy or clothing yet
- avoids staging blender/sackboy_scene.blend1

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_GlassReflectionVisibility_v1B.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-GlassReflectionVisibility.ps1
.\Apply-GlassReflectionVisibility.ps1
.\Validate-GlassReflectionVisibility.ps1
.\Publish-CurrentReview.ps1
