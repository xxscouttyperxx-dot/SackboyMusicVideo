REMOVE VISIBLE REFLECTION STREAKS V1

This package removes the visible floating/intersecting reflection line overlays from the previous glass reflection pass.

It removes:
- FX_GlassStreak_*
- FX_WindowGlow_*

It preserves:
- FX_ReflectCard_* reflection-only cards
- FX_TrafficLight_Red / Yellow / Green
- car, underglow, asphalt, parking strips
- approved amber lights
- sky/HDRI
- character and clothing

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_RemoveVisibleReflectionStreaks_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-RemoveVisibleReflectionStreaks.ps1
.\Apply-RemoveVisibleReflectionStreaks.ps1
.\Validate-RemoveVisibleReflectionStreaks.ps1
.\Publish-CurrentReview.ps1
