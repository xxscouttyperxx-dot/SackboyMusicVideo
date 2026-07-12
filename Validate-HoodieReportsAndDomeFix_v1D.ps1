$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path

$Expected=@(
"renders\current_review\01_HoodFrontLowAngleMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"reports\hoodie_reports_and_dome_fix_v1D\HoodieReportsAndDomeFix_v1D_report.txt",
"reports\hoodie_reports_and_dome_fix_v1D\HoodieReportsAndDomeFix_v1D_status.json",
"reports\hoodie_reports_and_dome_fix_v1D\Hoodie_Reports_And_Dome_Fix_v1D.md",
"reports\hoodie_reports_and_dome_fix_v1D\hoodie_reports_and_dome_fix_v1D.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$BadFiles = Get-ChildItem (Join-Path $Root "renders\current_review") -File |
    Where-Object { $_.Extension -in @(".txt",".json",".md") }
if($BadFiles.Count -gt 0){
    throw "current_review contains text/json/md files; expected images only: $($BadFiles.Name -join ', ')"
}

Write-Host "=== HOODIE REPORTS AND DOME FIX v1D VALIDATION PASS ==="
