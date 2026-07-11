$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\WardrobeCleanupAssetIntake-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_WardrobeCleanupAssetIntake.blend") -Force
Copy-Item (Join-Path $PatchScripts "wardrobe_cleanup_asset_intake_v1.py") (Join-Path $Scripts "wardrobe_cleanup_asset_intake_v1.py") -Force

Write-Host "[WardrobeCleanupAssetIntake] Cleaning old package root files..."
$Keep=@(
    "Apply-WardrobeCleanupAssetIntake.ps1",
    "Validate-WardrobeCleanupAssetIntake.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-WardrobeCleanupAssetIntake.txt",
    "README_FIRST.txt",
    "Run-BuildAll.ps1",
    "Run-DiagnosticRenders.ps1"
)
$Patterns=@(
    "Apply-Step*.ps1",
    "Validate-Step*.ps1",
    "README-Step*.txt",
    "Apply-Production*.ps1",
    "Validate-Production*.ps1",
    "README-Production*.txt",
    "Apply-Project*.ps1",
    "Validate-Project*.ps1",
    "README-Project*.txt",
    "Apply-HeroCar*.ps1",
    "Validate-HeroCar*.ps1",
    "README-HeroCar*.txt",
    "Apply-LampSidewalkSkyCleanup.ps1",
    "Validate-LampSidewalkSkyCleanup.ps1",
    "README-LampSidewalkSkyCleanup.txt",
    "Apply-StorefrontParking*.ps1",
    "Validate-StorefrontParking*.ps1",
    "README-StorefrontParking*.txt",
    "Apply-AmbientCarGlassPolish.ps1",
    "Validate-AmbientCarGlassPolish.ps1",
    "README-AmbientCarGlassPolish.txt",
    "Apply-CharacterWardrobePrep.ps1",
    "Validate-CharacterWardrobePrep.ps1",
    "README-CharacterWardrobePrep.txt",
    "Apply-PublishFix.ps1",
    "README-PublishFix.txt"
)
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$Keep -notcontains $_.Name} |
        Remove-Item -Force
}

Write-Host "[WardrobeCleanupAssetIntake] Preserving locked scene; cleaning guide cubes and preparing clothing asset intake..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "wardrobe_cleanup_asset_intake_v1.py")
if($LASTEXITCODE -ne 0){throw "Wardrobe cleanup / asset intake failed."}

$Expected=@(
"renders\wardrobe_cleanup_asset_intake_v1\01_WardrobeCleanupFront.png",
"renders\wardrobe_cleanup_asset_intake_v1\02_ShoeGraphicCleanup.png",
"renders\wardrobe_cleanup_asset_intake_v1\03_ImportedClothingCandidates.png",
"renders\wardrobe_cleanup_asset_intake_v1\WardrobeCleanupAssetIntake_status.json",
"renders\wardrobe_cleanup_asset_intake_v1\WardrobeCleanupAssetIntake_report.txt",
"renders\current_review\01_WardrobeCleanupFront.png",
"reports\wardrobe_asset_notes\Wardrobe_Asset_Intake_Notes.txt"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== WARDROBE CLEANUP / ASSET INTAKE PASS ==="
Write-Host "Lights, car, world/HDRI, storefront, sidewalk, and parking were not modified."
Write-Host "Material swatch cubes hidden."
Write-Host "Blocky shoe accent cubes hidden and replaced with subtle curve guides."
Write-Host "Clothing asset folders created under blender\assets\models\clothing."
Write-Host "If clothing models are already in those folders, they were imported as candidates."
Write-Host "Viewport/reflection notes written to reports\wardrobe_asset_notes."
Write-Host "Current review renders updated."
Write-Host "Backup: $BackupRoot"
