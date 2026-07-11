CHARACTER WARDROBE PREP V1

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CharacterWardrobePrep.ps1
.\Apply-CharacterWardrobePrep.ps1
.\Validate-CharacterWardrobePrep.ps1
.\Publish-CurrentReview.ps1

Purpose:
- Preserve current scene, car, world/HDRI, and all lighting.
- Do not touch hand geometry.
- Apply procedural yarn material to F2.
- Create non-destructive hoodie, jeans, and black skate-shoe fit guides for review.
