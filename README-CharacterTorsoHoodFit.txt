CHARACTER TORSO HOOD FIT V1

This pass strengthens the body fit before actual clothing deformation.

It:
- adds a new active non-destructive shape key to F2: BODYFIT_TorsoHoodFit_v1
- includes the previous body prep key, then disables the old one so body keys do not stack unpredictably
- reduces torso thickness/depth more significantly for hoodie clearance
- reduces head/neck depth more because the back of the head will sit inside the hood
- slightly narrows lower body for pants fit
- protects hand zones
- adds persistent review cameras:
  - CAM_REVIEW_BodyFit_Front
  - CAM_REVIEW_BodyFit_Profile
  - CAM_REVIEW_ClothingClearance
  - CAM_REVIEW_StorefrontReflection
- preserves reflection setup, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- does not deform clothing yet

Manual render basics after this package:
- Select a CAM_REVIEW camera in the Outliner
- Press Ctrl + Numpad 0 to view through that selected camera
- Press F12 to render one still image
- Press Ctrl + F12 to render animation frames
- Rendered files go wherever Output Properties points; the package still writes review renders to renders/current_review

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CharacterTorsoHoodFit_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CharacterTorsoHoodFit.ps1
.\Apply-CharacterTorsoHoodFit.ps1
.\Validate-CharacterTorsoHoodFit.ps1
.\Publish-CurrentReview.ps1
