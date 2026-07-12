$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\character_torso_hood_fit_v1\01_BodyFitStrongerFront.png",
"renders\character_torso_hood_fit_v1\02_BodyFitProfileThickness.png",
"renders\character_torso_hood_fit_v1\03_HoodiePantsClearance.png",
"renders\character_torso_hood_fit_v1\04_StorefrontReflectionCamera.png",
"renders\character_torso_hood_fit_v1\CharacterTorsoHoodFit_report.txt",
"renders\character_torso_hood_fit_v1\CharacterTorsoHoodFit_status.json",
"reports\character_torso_hood_fit_v1\Character_Torso_Hood_Fit_v1.md",
"reports\character_torso_hood_fit_v1\character_torso_hood_fit_v1.json",
"renders\current_review\01_BodyFitStrongerFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CHARACTER TORSO HOOD FIT VALIDATION PASS ==="
