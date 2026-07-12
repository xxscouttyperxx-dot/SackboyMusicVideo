$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieBowlRidgePolish-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieBowlRidgePolish.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_bowl_ridge_polish_v1.py") (Join-Path $Scripts "hoodie_bowl_ridge_polish_v1.py") -Force

Write-Host "[HoodieBowlRidgePolish] Cleaning old package root files..."
$Keep=@("Apply-HoodieBowlRidgePolish.ps1","Validate-HoodieBowlRidgePolish.ps1","Publish-CurrentReview.ps1","README-HoodieBowlRidgePolish.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieBowlRidgePolish] Renaming hoodie and polishing bowl/ridge shape..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_bowl_ridge_polish_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie bowl ridge polish failed."}

$Expected=@(
"renders\hoodie_bowl_ridge_polish_v1\01_HoodieTopClose.png",
"renders\hoodie_bowl_ridge_polish_v1\02_HoodieTopOverhead.png",
"renders\hoodie_bowl_ridge_polish_v1\03_HoodieBowlRimProfile.png",
"renders\hoodie_bowl_ridge_polish_v1\04_HoodieScenePreserved.png",
"renders\hoodie_bowl_ridge_polish_v1\HoodieBowlRidgePolish_report.txt",
"renders\hoodie_bowl_ridge_polish_v1\HoodieBowlRidgePolish_status.json",
"reports\hoodie_bowl_ridge_polish_v1\Hoodie_Bowl_Ridge_Polish_v1.md",
"reports\hoodie_bowl_ridge_polish_v1\hoodie_bowl_ridge_polish_v1.json",
"renders\current_review\01_HoodieTopClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE BOWL RIDGE POLISH PASS ==="
Write-Host "Main hoodie was renamed to SACKBOY_Hoodie_Main."
Write-Host "Focused cameras now target the hoodie object/bounds, not the F2 character bounds."
Write-Host "Hood ridge was rounded/feathered and the hood was shaped toward a cleaner concave bowl."
Write-Host "Vertex/face counts and before/after dimensions were written to the report."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
