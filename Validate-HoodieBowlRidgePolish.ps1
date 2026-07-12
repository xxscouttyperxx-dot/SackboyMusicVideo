$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
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
Write-Host "=== HOODIE BOWL RIDGE POLISH VALIDATION PASS ==="
