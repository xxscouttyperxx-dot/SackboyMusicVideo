$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_crown_sleeve_taper_v1\01_HoodCrownFront.png",
"renders\hoodie_crown_sleeve_taper_v1\02_HoodCrownProfile.png",
"renders\hoodie_crown_sleeve_taper_v1\03_SleeveTaperThreeQuarter.png",
"renders\hoodie_crown_sleeve_taper_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_crown_sleeve_taper_v1\HoodieCrownSleeveTaper_report.txt",
"renders\hoodie_crown_sleeve_taper_v1\HoodieCrownSleeveTaper_status.json",
"reports\hoodie_crown_sleeve_taper_v1\Hoodie_Crown_Sleeve_Taper_v1.md",
"reports\hoodie_crown_sleeve_taper_v1\hoodie_crown_sleeve_taper_v1.json",
"renders\current_review\01_HoodCrownFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE CROWN SLEEVE TAPER VALIDATION PASS ==="
