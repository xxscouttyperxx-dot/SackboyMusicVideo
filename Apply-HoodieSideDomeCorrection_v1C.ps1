$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieSideDomeCorrection_v1C-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieSideDomeCorrection_v1C.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_side_dome_correction_v1C.py") (Join-Path $Scripts "hoodie_side_dome_correction_v1C.py") -Force

Write-Host "[HoodieSideDomeCorrection_v1C] Cleaning old package root files..."
$Keep=@("Apply-HoodieSideDomeCorrection_v1C.ps1","Validate-HoodieSideDomeCorrection_v1C.ps1","Publish-CurrentReview.ps1","README-HoodieSideDomeCorrection_v1C.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieSideDomeCorrection_v1C] Applying directional side dome correction and raised camera review..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_side_dome_correction_v1C.py")
if($LASTEXITCODE -ne 0){throw "Hoodie side dome correction v1C failed."}

$Expected=@(
"renders\current_review\01_HoodFrontMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"reports\hoodie_side_dome_correction_v1C\HoodieSideDomeCorrection_v1C_report.txt",
"reports\hoodie_side_dome_correction_v1C\HoodieSideDomeCorrection_v1C_status.json",
"reports\hoodie_side_dome_correction_v1C\Hoodie_Side_Dome_Correction_v1C.md",
"reports\hoodie_side_dome_correction_v1C\hoodie_side_dome_correction_v1C.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE SIDE DOME CORRECTION v1C PASS ==="
Write-Host "Front side depressions were moved down/outward and feathered."
Write-Host "Rear side droop was moved up/outward and feathered into the hood silhouette."
Write-Host "All review cameras were raised to show the top of the hood and wire termination better."
Write-Host "Text/json outputs were written to reports\hoodie_side_dome_correction_v1C."
Write-Host "Current_review was cleaned and contains only current images."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
