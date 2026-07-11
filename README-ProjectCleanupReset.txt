SACKBOY PROJECT CLEANUP + RESET

PURPOSE
-------
Undo the clutter introduced by the integrated preview and accumulated diagnostics.

SCENE CLEANUP
-------------
- removes PRODUCTION_PREVIEW and PP_* collections
- removes diagnostic/guide collections
- removes J3 and J4 hand branches
- keeps:
  1) BASE_Meshy_LeftCandidate_Source
  2) F2 manual-cleaned baseline
  3) HANDREFINE_J2B_Working best hand branch
- removes old diagnostic lights/cameras
- creates exactly two amber area lights
- creates exactly three cameras plus one orbit helper
- hides legacy parking-lot/camera collections rather than deleting user-authored data
- applies a warmer brown yarn-like procedural material

PROJECT-FOLDER CLEANUP
----------------------
- deletes obsolete Apply-Step*.ps1 files
- deletes obsolete Validate-Step*.ps1 files
- deletes obsolete README-Step*.txt files
- deletes old ProductionPreview launcher/validator/readme files
- removes patch staging directory
- keeps only the newest three backup directories

RUN
---
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-ProjectCleanupReset.ps1
.\Apply-ProjectCleanupReset.ps1

VALIDATE
--------
.\Validate-ProjectCleanupReset.ps1
