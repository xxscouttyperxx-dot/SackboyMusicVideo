$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieSurfaceDataRepair_v1F-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieSurfaceDataRepair_v1F.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_surface_data_repair_v1F.py") (Join-Path $Scripts "hoodie_surface_data_repair_v1F.py") -Force

Write-Host "[HoodieSurfaceDataRepair_v1F] Cleaning old package root files..."
$Keep=@("Apply-HoodieSurfaceDataRepair_v1F.ps1","Validate-HoodieSurfaceDataRepair_v1F.ps1","Publish-CurrentReview.ps1","README-HoodieSurfaceDataRepair_v1F.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieSurfaceDataRepair_v1F] Measuring ridge/depression disparity and repairing hood surface..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_surface_data_repair_v1F.py")
if($LASTEXITCODE -ne 0){throw "Hoodie surface data repair v1F failed."}

$Expected=@(
"renders\current_review\01_HoodFrontLowAngleMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_DepressionRidgeMarkers.png",
"renders\current_review\06_ActualLongEdgeAudit.png",
"renders\current_review\07_ScenePreserved.png",
"reports\hoodie_surface_data_repair_v1F\HoodieSurfaceDataRepair_v1F_report.txt",
"reports\hoodie_surface_data_repair_v1F\HoodieSurfaceDataRepair_v1F_status.json",
"reports\hoodie_surface_data_repair_v1F\Hoodie_Surface_Data_Repair_v1F.md",
"reports\hoodie_surface_data_repair_v1F\hoodie_surface_data_repair_v1F.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE SURFACE DATA REPAIR v1F PASS ==="
Write-Host "Measured ridge/depression disparity and logged extreme positions."
Write-Host "Created depression/ridge marker render and actual long-edge audit render."
Write-Host "Repaired side depressions using local disparity data and masked relaxation."
Write-Host "Current_review was cleaned and contains only current images."
Write-Host "Text/json outputs were written to reports\hoodie_surface_data_repair_v1F."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
