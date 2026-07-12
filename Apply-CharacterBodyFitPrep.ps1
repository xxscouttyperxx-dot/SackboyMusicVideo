$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CharacterBodyFitPrep-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CharacterBodyFitPrep.blend") -Force
Copy-Item (Join-Path $PatchScripts "character_body_fit_prep_v1.py") (Join-Path $Scripts "character_body_fit_prep_v1.py") -Force

Write-Host "[CharacterBodyFitPrep] Cleaning old package root files..."
$Keep=@("Apply-CharacterBodyFitPrep.ps1","Validate-CharacterBodyFitPrep.ps1","Publish-CurrentReview.ps1","README-CharacterBodyFitPrep.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[CharacterBodyFitPrep] Applying non-destructive body fit shape key..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "character_body_fit_prep_v1.py")
if($LASTEXITCODE -ne 0){throw "Character body fit prep failed."}

$Expected=@(
"renders\character_body_fit_prep_v1\01_BodyFitFront.png",
"renders\character_body_fit_prep_v1\02_BodyFitThreeQuarter.png",
"renders\character_body_fit_prep_v1\03_ClothingFitContext.png",
"renders\character_body_fit_prep_v1\04_ReflectionScenePreserved.png",
"renders\character_body_fit_prep_v1\CharacterBodyFitPrep_report.txt",
"renders\character_body_fit_prep_v1\CharacterBodyFitPrep_status.json",
"reports\character_body_fit_prep_v1\Character_Body_Fit_Prep_v1.md",
"reports\character_body_fit_prep_v1\character_body_fit_prep_v1.json",
"renders\current_review\01_BodyFitFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CHARACTER BODY FIT PREP PASS ==="
Write-Host "F2 received an active non-destructive body-fit shape key for hoodie/pants prep."
Write-Host "Torso/head/lower-body proportions were lightly tightened; hands were protected."
Write-Host "Clothing deformation was not applied yet."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
