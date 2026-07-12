HOODIE CROWN SLEEVE TAPER V1

This package continues from the approved safer hoodie-only direction.

It:
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_CrownSleeveTaper_v1
- expands the hood crown in feathered sections so it better fits Sackboy's large head
- smooths the transition below the crown by using lower/middle/crown expansion bands
- tapers sleeve outer/cuff regions to reduce the large sticking-out sleeve mass
- preserves the narrowed hoodie body from the previous hoodie pass
- preserves current reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- does not deform pants, shoes, or F2 in this pass

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieCrownSleeveTaper_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieCrownSleeveTaper.ps1
.\Apply-HoodieCrownSleeveTaper.ps1
.\Validate-HoodieCrownSleeveTaper.ps1
.\Publish-CurrentReview.ps1
