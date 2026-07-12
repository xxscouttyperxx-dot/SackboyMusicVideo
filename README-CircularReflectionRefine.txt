CIRCULAR REFLECTION REFINE V1

This pass preserves the successful Cycles glass look and tightens the reflection sources.

It:
- keeps the current good-looking reflection behavior
- rebuilds FX_ReflectCard objects as smaller circular reflection-only emissive cards
- preserves the red / yellow / green traffic-light concept
- keeps spotlights in the scene
- keeps glass materials tuned for strong Cycles reflections
- preserves car, underglow, asphalt, parking strips, amber lights, sky/HDRI, character, and clothing
- does not deform Sackboy or clothing yet

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CircularReflectionRefine_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CircularReflectionRefine.ps1
.\Apply-CircularReflectionRefine.ps1
.\Validate-CircularReflectionRefine.ps1
.\Publish-CurrentReview.ps1
