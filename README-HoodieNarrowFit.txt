HOODIE NARROW FIT V1

This is the safer pass after restoring the character baseline.

It:
- leaves F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- adds a hoodie-only active shape key: HOODIEFIT_NarrowSackboy_v1
- narrows the hoodie shoulders and upper torso so it fits Sackboy's narrow body better
- tucks the sleeve-root/shoulder caps inward and slightly downward
- lightly reduces torso depth and softens the hood crown
- preserves current reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- does not deform pants, shoes, or F2 in this pass

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieNarrowFit_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieNarrowFit.ps1
.\Apply-HoodieNarrowFit.ps1
.\Validate-HoodieNarrowFit.ps1
.\Publish-CurrentReview.ps1
