HOODIE DOME SIDE DEPRESSION FIX V1B

This replaces v1 and uses the preferred reporting structure.

Changes from v1:
- text/json reports go under reports\hoodie_dome_side_depression_fix_v1B
- nothing is written to renders\Project changes
- current_review contains images only
- publish no longer force-adds renders\Project changes

It:
- keeps F2/Sackboy untouched
- keeps all F2 BODYFIT shape keys disabled
- creates a hoodie-only shape key: HOODIEFIT_DomeSideDepressionFix_v1B
- corrects deep side depressions/valleys
- feathers side panels into a smoother half-dome/bowl shape
- preserves the front rim/opening as the intentional break in the dome
- rounds lower-back-to-mid-back hood droop
- feathers rear protrusion into the side-profile silhouette
- raises shoulder collar seam without pinching the sleeve root
- deletes and recreates exactly 12 cameras: 9 visible + 3 hidden animation cameras
- writes only images to renders\current_review
- preserves scene lighting, car, reflections, underglow, asphalt, sky/HDRI, and storefronts

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieDomeSideDepressionFix_v1B.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieDomeSideDepressionFix_v1B.ps1
.\Apply-HoodieDomeSideDepressionFix_v1B.ps1
.\Validate-HoodieDomeSideDepressionFix_v1B.ps1
.\Publish-CurrentReview.ps1
