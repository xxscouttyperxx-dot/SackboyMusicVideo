CURRENT BASELINE ANNOTATION V1

Use this after the user's manual duplicate cleanup and BLEND1 relocation.

This pass:
- cleans renders/current_review again
- renders fresh current scene views
- writes object/collection/duplicate/shared-data reports
- identifies visible current hoodie/clothing/character candidates
- publishes the current smaller blend file if Git LFS succeeds

It does NOT:
- edit objects
- delete objects
- move objects
- rename objects
- hide/unhide objects
- save the blend during Blender execution

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CurrentBaselineAnnotation_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CurrentBaselineAnnotation.ps1
.\Apply-CurrentBaselineAnnotation.ps1
.\Validate-CurrentBaselineAnnotation.ps1
.\Publish-CurrentReview.ps1
