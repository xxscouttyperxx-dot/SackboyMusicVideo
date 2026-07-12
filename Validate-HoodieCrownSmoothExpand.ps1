$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_crown_smooth_expand_v1\01_HoodTopFront.png",
"renders\hoodie_crown_smooth_expand_v1\02_HoodTopProfile.png",
"renders\hoodie_crown_smooth_expand_v1\03_SleeveElbowCheck.png",
"renders\hoodie_crown_smooth_expand_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_crown_smooth_expand_v1\HoodieCrownSmoothExpand_report.txt",
"renders\hoodie_crown_smooth_expand_v1\HoodieCrownSmoothExpand_status.json",
"reports\hoodie_crown_smooth_expand_v1\Hoodie_Crown_Smooth_Expand_v1.md",
"reports\hoodie_crown_smooth_expand_v1\hoodie_crown_smooth_expand_v1.json",
"renders\current_review\01_HoodTopFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE CROWN SMOOTH EXPAND VALIDATION PASS ==="
