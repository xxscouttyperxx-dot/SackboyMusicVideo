CYCLES REFLECTION CARDS V1

This package is the cleaner reflection approach.

It:
- removes any visible FX_GlassStreak / FX_WindowGlow leftovers
- creates no visible floating streak lines
- rebuilds FX_ReflectCard_* as camera-invisible / glossy-visible Cycles reflection sources
- keeps red/yellow/green traffic-light concept
- tunes glass materials
- sets the render engine to Cycles for reflection proof renders
- preserves car, asphalt, white parking strips, approved amber lights, sky/HDRI, character, and clothing
- does not deform Sackboy or clothing yet

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CyclesReflectionCards_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CyclesReflectionCards.ps1
.\Apply-CyclesReflectionCards.ps1
.\Validate-CyclesReflectionCards.ps1
.\Publish-CurrentReview.ps1
