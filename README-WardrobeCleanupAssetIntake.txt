WARDROBE CLEANUP / ASSET INTAKE V1

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-WardrobeCleanupAssetIntake.ps1
.\Apply-WardrobeCleanupAssetIntake.ps1
.\Validate-WardrobeCleanupAssetIntake.ps1
.\Publish-CurrentReview.ps1

What this does:
- preserves all lights, car, world/HDRI, storefront, sidewalk, and parking layout
- hides material swatch cubes
- hides blocky shoe accent cubes
- keeps current hoodie/jeans/shoe guide clothing as reference
- creates clothing asset folders:
  blender/assets/models/clothing/hoodie
  blender/assets/models/clothing/jeans
  blender/assets/models/clothing/sneakers
  blender/assets/models/clothing/misc
- imports .glb/.gltf/.fbx/.blend clothing candidates from those folders if present
- writes viewport/reflection notes to reports/wardrobe_asset_notes
