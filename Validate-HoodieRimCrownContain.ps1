$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_rim_crown_contain_v1\01_HoodRimFront.png",
"renders\hoodie_rim_crown_contain_v1\02_HoodRimProfile.png",
"renders\hoodie_rim_crown_contain_v1\03_HoodTopArtifactCheck.png",
"renders\hoodie_rim_crown_contain_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_rim_crown_contain_v1\HoodieRimCrownContain_report.txt",
"renders\hoodie_rim_crown_contain_v1\HoodieRimCrownContain_status.json",
"reports\hoodie_rim_crown_contain_v1\Hoodie_Rim_Crown_Contain_v1.md",
"reports\hoodie_rim_crown_contain_v1\hoodie_rim_crown_contain_v1.json",
"renders\current_review\01_HoodRimFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE RIM CROWN CONTAIN VALIDATION PASS ==="
