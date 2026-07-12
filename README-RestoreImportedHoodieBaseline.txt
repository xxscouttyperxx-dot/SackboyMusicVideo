RESTORE IMPORTED HOODIE BASELINE V1

This restores the hoodie to the imported/Basis geometry.

It:
- sets every non-Basis hoodie shape key value to 0
- sets the active hoodie shape key back to Basis
- does not apply any new deformation
- keeps the HOODIEFIT shape keys in the file for evidence/rollback, but inactive
- keeps F2/Sackboy untouched
- keeps F2 BODYFIT shape keys disabled
- keeps scene, car, underglow, lighting, sky, reflections, asphalt, and storefronts preserved
- writes images only to renders\current_review
- writes reports to reports\restore_imported_hoodie_baseline_v1

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_RestoreImportedHoodieBaseline_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-RestoreImportedHoodieBaseline.ps1
.\Apply-RestoreImportedHoodieBaseline.ps1
.\Validate-RestoreImportedHoodieBaseline.ps1
.\Publish-CurrentReview.ps1
