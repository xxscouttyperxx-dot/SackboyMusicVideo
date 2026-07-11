BASELINE CAPTURE / SCAN V1

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-BaselineCaptureScan.ps1
.\Apply-BaselineCaptureScan.ps1
.\Validate-BaselineCaptureScan.ps1
.\Publish-CurrentReview.ps1

Purpose:
- Record and push the current manual baseline.
- No scene edits.
- No light edits.
- No clothing edits.
- No world/HDRI edits.
- No added line objects.
- Capture visible collections, lights, clothing/imported candidates, suspect leftover object names, and current review renders.
