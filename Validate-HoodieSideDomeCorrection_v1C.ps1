$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path

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

$BadFiles = Get-ChildItem (Join-Path $Root "renders\current_review") -File |
    Where-Object { $_.Extension -in @(".txt",".json",".md") }
if($BadFiles.Count -gt 0){
    throw "current_review contains text/json/md files; expected images only: $($BadFiles.Name -join ', ')"
}

Write-Host "=== HOODIE SIDE DOME CORRECTION v1C VALIDATION PASS ==="
