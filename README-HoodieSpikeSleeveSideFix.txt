HOODIE SPIKE / SLEEVE / SIDE FIX V1

This package responds to the latest feedback.

It:
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_SpikeSleeveSideFix_v1
- rounds the top ridge more and feathers it further into the bowl
- smooths local wire spikes / outlier vertices using neighbor smoothing
- reduces the convex lower-side folds by reversing the prior outward bias
- thickens sleeves more uniformly and opens the shoulder root so it does not pinch too thin
- uses smaller 960x540 Workbench evidence renders
- includes one material-preview-style render, left/right gray side views, one wire spike check, and one scene-preservation view
- keeps reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting preserved
- reports vertex count, face count, touched vertices, smoothed vertices, max movement, and before/after dimensions

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieSpikeSleeveSideFix_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieSpikeSleeveSideFix.ps1
.\Apply-HoodieSpikeSleeveSideFix.ps1
.\Validate-HoodieSpikeSleeveSideFix.ps1
.\Publish-CurrentReview.ps1
