CHARACTER BODY FIT PREP V1

This is the first deformation pass after the reflection work.

It:
- adds an active non-destructive shape key to F2: BODYFIT_HoodiePantsPrep_v1
- lightly tightens the central torso/depth for hoodie clearance
- lightly softens head/depth for hood clearance
- lightly narrows the lower body/legs for pants fit
- protects the outer mid-height hand zones
- does not deform clothing yet
- preserves car, underglow, asphalt, parking strips, approved amber lighting, sky/HDRI, and reflection setup
- creates validation renders and reports
- avoids visible helper objects, guide lines, and swatches

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CharacterBodyFitPrep_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CharacterBodyFitPrep.ps1
.\Apply-CharacterBodyFitPrep.ps1
.\Validate-CharacterBodyFitPrep.ps1
.\Publish-CurrentReview.ps1
