COLLECTION VISIBILITY FIX RETRY PUSH V1

Why:
- SceneCollectionsOrganization_v1 succeeded locally and committed locally.
- Push failed due Git LFS/network connection errors.
- The log also showed visible objects changed 204 -> 205.
- This likely happened because a previously collection-hidden object was moved into a visible clean collection.

This package:
- sets 08_HIDDEN_NONVISIBLE_REVIEW hide_viewport=true
- sets 08_HIDDEN_NONVISIBLE_REVIEW hide_render=true
- select-locks objects inside that collection
- does not delete any objects
- does not edit geometry/materials/modifiers/shape keys
- creates a small fix commit on top of the local collection-organization commit
- retries Git LFS push and Git push up to 5 times each

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_CollectionVisibilityFixRetryPush_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-CollectionVisibilityFixRetryPush.ps1
.\Apply-CollectionVisibilityFixRetryPush.ps1
.\Validate-CollectionVisibilityFixRetryPush.ps1
.\Publish-CurrentReview.ps1
