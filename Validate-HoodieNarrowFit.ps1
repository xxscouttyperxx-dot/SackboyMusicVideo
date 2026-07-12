$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_narrow_fit_v1\01_HoodieNarrowFront.png",
"renders\hoodie_narrow_fit_v1\02_HoodieNarrowProfile.png",
"renders\hoodie_narrow_fit_v1\03_HoodieNarrowThreeQuarter.png",
"renders\hoodie_narrow_fit_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_narrow_fit_v1\HoodieNarrowFit_report.txt",
"renders\hoodie_narrow_fit_v1\HoodieNarrowFit_status.json",
"reports\hoodie_narrow_fit_v1\Hoodie_Narrow_Fit_v1.md",
"reports\hoodie_narrow_fit_v1\hoodie_narrow_fit_v1.json",
"renders\current_review\01_HoodieNarrowFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE NARROW FIT VALIDATION PASS ==="
