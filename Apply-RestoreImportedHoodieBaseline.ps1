$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\RestoreImportedHoodieBaseline-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_RestoreImportedHoodieBaseline.blend") -Force
Copy-Item (Join-Path $PatchScripts "restore_imported_hoodie_baseline_v1.py") (Join-Path $Scripts "restore_imported_hoodie_baseline_v1.py") -Force

Write-Host "[RestoreImportedHoodieBaseline] Cleaning old package root files..."
$Keep=@("Apply-RestoreImportedHoodieBaseline.ps1","Validate-RestoreImportedHoodieBaseline.ps1","Publish-CurrentReview.ps1","README-RestoreImportedHoodieBaseline.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[RestoreImportedHoodieBaseline] Restoring hoodie to imported Basis geometry..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "restore_imported_hoodie_baseline_v1.py")
if($LASTEXITCODE -ne 0){throw "Restore imported hoodie baseline failed."}

$Expected=@(
"renders\current_review\01_RestoredHoodieFront.png",
"renders\current_review\02_RestoredHoodieLeftSideGray.png",
"renders\current_review\03_RestoredHoodieRightSideGray.png",
"renders\current_review\04_RestoredHoodieTopGray.png",
"renders\current_review\05_ScenePreserved.png",
"reports\restore_imported_hoodie_baseline_v1\RestoreImportedHoodieBaseline_report.txt",
"reports\restore_imported_hoodie_baseline_v1\RestoreImportedHoodieBaseline_status.json",
"reports\restore_imported_hoodie_baseline_v1\Restore_Imported_Hoodie_Baseline_v1.md",
"reports\restore_imported_hoodie_baseline_v1\restore_imported_hoodie_baseline_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== RESTORE IMPORTED HOODIE BASELINE PASS ==="
Write-Host "Hoodie restored to imported/Basis geometry by disabling all non-Basis hoodie shape keys."
Write-Host "No new hoodie deformation was applied."
Write-Host "Current_review was cleaned and contains only current images."
Write-Host "Text/json outputs were written to reports\restore_imported_hoodie_baseline_v1."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
