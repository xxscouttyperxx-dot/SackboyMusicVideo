SCENE COLLECTIONS ORGANIZATION V1

This organizes the Outliner collections first, before more clothing edits.

It does NOT:
- delete objects
- hide currently visible objects
- change geometry
- change materials
- change modifiers
- change shape keys
- change camera transforms
- change lights

It DOES:
- create clean top-level collections
- put same-name object groups together
- keep same-name groups under their most likely category
- link each object to a clean target collection
- unlink objects from old collections after they are safely linked to the new target
- reduce multi-collection Outliner duplicate listings

Top-level collections:
01_CHARACTER_AND_SAME_NAME_GROUPS
02_CLOTHING_AND_SAME_NAME_GROUPS
03_HERO_CAR_AND_IMPORTED_PARTS
04_ENVIRONMENT_STOREFRONTS_PARKING
05_PROPS_SIGNS_DECOR
06_LIGHTING_REFLECTIONS
07_CAMERAS
08_HIDDEN_NONVISIBLE_REVIEW

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_SceneCollectionsOrganization_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-SceneCollectionsOrganization.ps1
.\Apply-SceneCollectionsOrganization.ps1
.\Validate-SceneCollectionsOrganization.ps1
.\Publish-CurrentReview.ps1
