CHARACTER SILHOUETTE REFINE V1

This pass pushes the body shape further before actual clothing deformation.

It:
- adds a new active non-destructive shape key to F2: BODYFIT_SilhouetteRefine_v1
- copies the latest prior body-fit key into the new key first, then refines it
- thins the legs so they read closer to the arms
- flattens the torso/gut more aggressively
- reduces the face/nose projection so it does not look like a snout
- makes the hands smaller/more Sackboy-like
- refreshes persistent review cameras, including CAM_REVIEW_StorefrontReflection
- preserves reflection setup, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting
- does not deform clothing yet

Why the storefront reflections are hard to see in the viewport:
- Cycles preview is noisy, especially while moving.
- The subtle reflections are real if the render captures them.
- Use CAM_REVIEW_StorefrontReflection and render a still with F12 to judge them more clearly.

Manual render reminder:
- Select a review camera in the Outliner
- Press Ctrl + Numpad 0 to look through that camera
- Press F12 to render a still
- Press Ctrl + F12 to render animation
- Output Properties controls the final save location for manual renders

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CharacterSilhouetteRefine_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CharacterSilhouetteRefine.ps1
.\Apply-CharacterSilhouetteRefine.ps1
.\Validate-CharacterSilhouetteRefine.ps1
.\Publish-CurrentReview.ps1
