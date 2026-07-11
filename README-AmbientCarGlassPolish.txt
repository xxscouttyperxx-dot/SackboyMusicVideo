AMBIENT CAR / GLASS POLISH V1

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-AmbientCarGlassPolish.ps1
.\Apply-AmbientCarGlassPolish.ps1
.\Validate-AmbientCarGlassPolish.ps1
.\Publish-CurrentReview.ps1

Purpose:
- Preserve current manually adjusted scene layout.
- Remove scripted sky backdrop if present, preserving user-managed World/HDRI.
- Add subtle amber helper lights so the approved overhead lamp color reads on the car.
- Polish storefront glass so it reads as dark glossy night glass with traffic/street reflections.
