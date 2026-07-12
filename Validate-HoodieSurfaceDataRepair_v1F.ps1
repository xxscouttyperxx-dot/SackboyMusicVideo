$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
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
$BadFiles = Get-ChildItem (Join-Path $Root "renders\current_review") -File |
    Where-Object { $_.Extension -in @(".txt",".json",".md") }
if($BadFiles.Count -gt 0){
    throw "current_review contains text/json/md files; expected images only: $($BadFiles.Name -join ', ')"
}
Write-Host "=== HOODIE SURFACE DATA REPAIR v1F VALIDATION PASS ==="
