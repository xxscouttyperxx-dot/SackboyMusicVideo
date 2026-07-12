$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CharacterTorsoHoodFit-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CharacterTorsoHoodFit.blend") -Force
Copy-Item (Join-Path $PatchScripts "character_torso_hood_fit_v1.py") (Join-Path $Scripts "character_torso_hood_fit_v1.py") -Force

Write-Host "[CharacterTorsoHoodFit] Cleaning old package root files..."
$Keep=@("Apply-CharacterTorsoHoodFit.ps1","Validate-CharacterTorsoHoodFit.ps1","Publish-CurrentReview.ps1","README-CharacterTorsoHoodFit.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[CharacterTorsoHoodFit] Applying stronger torso/head fit shape key and review cameras..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "character_torso_hood_fit_v1.py")
if($LASTEXITCODE -ne 0){throw "Character torso hood fit failed."}

$Expected=@(
"renders\character_torso_hood_fit_v1\01_BodyFitStrongerFront.png",
"renders\character_torso_hood_fit_v1\02_BodyFitProfileThickness.png",
"renders\character_torso_hood_fit_v1\03_HoodiePantsClearance.png",
"renders\character_torso_hood_fit_v1\04_StorefrontReflectionCamera.png",
"renders\character_torso_hood_fit_v1\CharacterTorsoHoodFit_report.txt",
"renders\character_torso_hood_fit_v1\CharacterTorsoHoodFit_status.json",
"reports\character_torso_hood_fit_v1\Character_Torso_Hood_Fit_v1.md",
"reports\character_torso_hood_fit_v1\character_torso_hood_fit_v1.json",
"renders\current_review\01_BodyFitStrongerFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CHARACTER TORSO HOOD FIT PASS ==="
Write-Host "F2 received a stronger active non-destructive torso/hood fit shape key."
Write-Host "Torso/head depth was reduced more significantly for hoodie clearance; hands were protected."
Write-Host "Persistent review cameras were added, including CAM_REVIEW_StorefrontReflection."
Write-Host "Clothing deformation was not applied yet."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
