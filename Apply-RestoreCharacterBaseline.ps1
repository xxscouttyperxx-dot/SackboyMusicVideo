$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\RestoreCharacterBaseline-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_RestoreCharacterBaseline.blend") -Force
Copy-Item (Join-Path $PatchScripts "restore_character_baseline_v1.py") (Join-Path $Scripts "restore_character_baseline_v1.py") -Force

Write-Host "[RestoreCharacterBaseline] Cleaning old package root files..."
$Keep=@("Apply-RestoreCharacterBaseline.ps1","Validate-RestoreCharacterBaseline.ps1","Publish-CurrentReview.ps1","README-RestoreCharacterBaseline.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[RestoreCharacterBaseline] Disabling bad BODYFIT shape keys and restoring character baseline..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "restore_character_baseline_v1.py")
if($LASTEXITCODE -ne 0){throw "Restore character baseline failed."}

$Expected=@(
"renders\restore_character_baseline_v1\01_RestoredCharacterFront.png",
"renders\restore_character_baseline_v1\02_RestoredCharacterProfile.png",
"renders\restore_character_baseline_v1\03_RestoredFaceHands.png",
"renders\restore_character_baseline_v1\04_StorefrontReflectionPreserved.png",
"renders\restore_character_baseline_v1\RestoreCharacterBaseline_report.txt",
"renders\restore_character_baseline_v1\RestoreCharacterBaseline_status.json",
"reports\restore_character_baseline_v1\Restore_Character_Baseline_v1.md",
"reports\restore_character_baseline_v1\restore_character_baseline_v1.json",
"renders\current_review\01_RestoredCharacterFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== RESTORE CHARACTER BASELINE PASS ==="
Write-Host "All BODYFIT shape key values on F2 were set to 0."
Write-Host "The bad silhouette deformation is disabled; F2 visually returns to the mesh Basis state."
Write-Host "Shape keys were not deleted, only disabled for safety/history."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
