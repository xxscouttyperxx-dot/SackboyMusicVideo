$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CharacterWardrobePrep-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CharacterWardrobePrep.blend") -Force
Copy-Item (Join-Path $PatchScripts "character_wardrobe_prep_v1.py") (Join-Path $Scripts "character_wardrobe_prep_v1.py") -Force

Write-Host "[CharacterWardrobePrep] Cleaning old package root files..."
$Keep=@(
    "Apply-CharacterWardrobePrep.ps1",
    "Validate-CharacterWardrobePrep.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-CharacterWardrobePrep.txt",
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
    "Apply-PublishFix.ps1",
    "README-PublishFix.txt"
)
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$Keep -notcontains $_.Name} |
        Remove-Item -Force
}

Write-Host "[CharacterWardrobePrep] Preserving locked scene; adding character material and wardrobe fit guides..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "character_wardrobe_prep_v1.py")
if($LASTEXITCODE -ne 0){throw "Character wardrobe prep failed."}

$Expected=@(
"renders\character_wardrobe_prep_v1\01_CharacterWardrobeFront.png",
"renders\character_wardrobe_prep_v1\02_ShoeCloseup.png",
"renders\character_wardrobe_prep_v1\03_WardrobeSceneContext.png",
"renders\character_wardrobe_prep_v1\CharacterWardrobePrep_status.json",
"renders\character_wardrobe_prep_v1\CharacterWardrobePrep_report.txt",
"renders\current_review\01_CharacterWardrobeFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CHARACTER WARDROBE PREP PASS ==="
Write-Host "Locked scene layout, car, sky/world, and lighting preserved."
Write-Host "No lights moved, removed, added, or edited."
Write-Host "F2 yarn material updated."
Write-Host "Non-destructive hoodie, jeans, and black skate-shoe fit guides created."
Write-Host "Hand geometry untouched."
Write-Host "Current review renders updated."
Write-Host "Backup: $BackupRoot"
