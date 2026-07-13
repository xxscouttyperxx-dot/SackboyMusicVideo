COMPARE CURRENT RENDERS ONLY V1

This package only creates comparison renders.

It does NOT:
- delete old current_review files
- clean current_review
- edit objects
- delete objects
- save the blend file

It creates:
renders\current_review\COMPARE_NOW_01_SceneWide_SOLID.png
renders\current_review\COMPARE_NOW_02_SceneWide_RENDERED.png
renders\current_review\COMPARE_NOW_03_HoodCharacterFront_SOLID.png
renders\current_review\COMPARE_NOW_04_HoodCharacterFront_RENDERED.png
renders\current_review\COMPARE_NOW_05_CharacterThreeQuarter_SOLID.png
renders\current_review\COMPARE_NOW_06_CharacterThreeQuarter_RENDERED.png

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CompareCurrentRendersOnly_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CompareCurrentRendersOnly.ps1
.\Apply-CompareCurrentRendersOnly.ps1
.\Validate-CompareCurrentRendersOnly.ps1
.\Publish-CurrentReview.ps1
