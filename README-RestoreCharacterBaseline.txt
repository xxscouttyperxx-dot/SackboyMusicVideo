RESTORE CHARACTER BASELINE V1

This package disables the rejected character body/silhouette deformation.

It:
- sets all F2 BODYFIT_* shape key values to 0
- visually restores F2 to the mesh Basis state
- keeps the bad shape keys disabled rather than deleting them
- preserves the successful reflection setup after the reflection passes
- preserves traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- creates current_review renders to confirm the character is back to baseline

Why:
The previous silhouette pass created unacceptable distortion: pitbull-like head/face, four-leg appearance, snout, head rolls/indentations. This pass resets that before we continue.

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_RestoreCharacterBaseline_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-RestoreCharacterBaseline.ps1
.\Apply-RestoreCharacterBaseline.ps1
.\Validate-RestoreCharacterBaseline.ps1
.\Publish-CurrentReview.ps1
