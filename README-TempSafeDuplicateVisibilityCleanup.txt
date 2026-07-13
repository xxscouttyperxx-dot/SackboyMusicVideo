TEMP SAFE DUPLICATE VISIBILITY CLEANUP V1

This is deliberately conservative.

It does NOT:
- delete objects
- hide currently visible objects
- touch the visible current character
- touch the visible current clothing
- touch the Audi car Plane/Circle/Bolt imported parts
- unlink multi-collection objects

It only:
- creates/uses ARCHIVE_HIDDEN_HELPERS_DO_NOT_DELETE
- takes a few hidden viewport helper objects that were still renderable/selectable
- sets hide_viewport=true, hide_render=true, hide_select=true
- links them to the archive collection
- writes a report explaining the duplicate/multi-collection/shared-data situation

Objects affected only if currently hidden:
- HERO_BlackSkateShoe_L_WhiteSole
- HERO_BlackSkateShoe_R_WhiteSole
- MOUTH_CUT_GUIDE_Data

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_TempSafeDuplicateVisibilityCleanup_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-TempSafeDuplicateVisibilityCleanup.ps1
.\Apply-TempSafeDuplicateVisibilityCleanup.ps1
.\Validate-TempSafeDuplicateVisibilityCleanup.ps1
.\Publish-CurrentReview.ps1
