SCENE SCRUB / GLASS REFLECTION BOOST V1B

This corrected package is named v1B so it will not collide with earlier downloads.

It:
- removes rejected ENV_Frame* parking-edge objects
- preserves white parking paint strips
- scrubs stale hidden/generated helper duplicates and clutter
- locks HERO_CyanUnderglow_Area to [-1.522953, 5.177517, 0.075276]
- changes the reflection setup to red / yellow / green
- removes the extra fourth/white reflection light
- creates camera-invisible emissive reflection cards/strips for the storefront glass
- tunes glass/window materials for stronger reflections
- prepares the setup for later keyframing of red/yellow/green intensity
- does not deform Sackboy or clothing yet
- avoids staging blender/sackboy_scene.blend1 to reduce unnecessary LFS uploads

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_SceneScrub_GlassReflectionBoost_v1B.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-SceneScrubGlassReflectionBoost.ps1
.\Apply-SceneScrubGlassReflectionBoost.ps1
.\Validate-SceneScrubGlassReflectionBoost.ps1
.\Publish-CurrentReview.ps1
