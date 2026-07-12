SCENE SCRUB / GLASS REFLECTION BOOST V1

This package:
- removes targeted ENV_Frame* black/glossy parking-edge objects
- preserves the white parking paint strips
- removes hidden/generated duplicate backup objects and clutter collections
- locks HERO_CyanUnderglow_Area to [-1.522953, 5.177517, 0.075276]
- boosts far-end red/white/amber/green reflection spotlights
- tunes storefront/window glass materials for sharper reflections
- does not add blue lighting
- does not deform Sackboy or clothing yet
- avoids staging blender/sackboy_scene.blend1 in the publish step to reduce LFS uploads

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_SceneScrub_GlassReflectionBoost_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-SceneScrubGlassReflectionBoost.ps1
.\Apply-SceneScrubGlassReflectionBoost.ps1
.\Validate-SceneScrubGlassReflectionBoost.ps1
.\Publish-CurrentReview.ps1
