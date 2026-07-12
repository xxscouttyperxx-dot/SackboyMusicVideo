HOODIE REPORTS AND DOME FIX V1D

This package:
- moves all text/json/md files from renders\Project changes into reports/<matching_pass_folder>
- removes renders\Project changes when empty
- keeps current_review image-only
- lowers the front hood camera and aims it upward at the hood
- applies a small directional correction to remaining side depressions/droop
- reports latest smoothed vertices and max local vertex movement under reports\hoodie_reports_and_dome_fix_v1D
- preserves F2, lighting, reflections, car, underglow, asphalt, sky/HDRI, and scene

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodieReportsAndDomeFix_v1D.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodieReportsAndDomeFix_v1D.ps1
.\Apply-HoodieReportsAndDomeFix_v1D.ps1
.\Validate-HoodieReportsAndDomeFix_v1D.ps1
.\Publish-CurrentReview.ps1
