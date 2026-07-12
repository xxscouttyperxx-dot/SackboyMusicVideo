HOODIE SURFACE RELAX / SPIKE AUDIT V1E

This package focuses on two things:
1. Better identifying the wire "spikes"
2. More broadly smoothing/rounding the hood depressions and droop

It:
- keeps F2/Sackboy untouched
- keeps all F2 BODYFIT shape keys disabled
- creates hoodie-only shape key: HOODIEFIT_SurfaceRelaxSpikeAudit_v1E
- audits the hoodie mesh for true isolated spike/outlier vertices
- smooths any true spike candidates if found
- reports spike candidates before/after and long edge candidates before/after
- treats the visible hood dents as broad surface valleys, not tiny point edits
- expands side valleys outward into the dome/bowl silhouette
- feathers valley boundaries with stronger broad smoothing
- lifts/feathers rear droop into the back curve
- keeps the front rim/opening preserved
- keeps current_review image-only
- writes text/json outputs to reports\hoodie_surface_relax_spike_audit_v1E
- preserves scene lighting, car, reflections, underglow, asphalt, sky/HDRI, and storefronts

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieSurfaceRelaxSpikeAudit_v1E.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieSurfaceRelaxSpikeAudit_v1E.ps1
.\Apply-HoodieSurfaceRelaxSpikeAudit_v1E.ps1
.\Validate-HoodieSurfaceRelaxSpikeAudit_v1E.ps1
.\Publish-CurrentReview.ps1
