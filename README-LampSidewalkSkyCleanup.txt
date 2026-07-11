LAMP / SIDEWALK / SKY CLEANUP

Run
---
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-LampSidewalkSkyCleanup.ps1
.\Apply-LampSidewalkSkyCleanup.ps1

Validate
--------
.\Validate-LampSidewalkSkyCleanup.ps1

Publish
-------
.\Publish-CurrentReview.ps1

Changes
-------
- removes duplicate old moon/cloud/star geometry
- preserves HDRI world
- moves/rebuilds visible lamp posts and fixtures at overhead amber lights
- widens sidewalk
- hides old narrow sidewalk/curb
- rebuilds flat double-thick parking lines
- fixes publish script so deleted package files are staged and git push errors throw
