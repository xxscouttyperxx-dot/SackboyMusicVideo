$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\character_body_fit_prep_v1\01_BodyFitFront.png",
"renders\character_body_fit_prep_v1\02_BodyFitThreeQuarter.png",
"renders\character_body_fit_prep_v1\03_ClothingFitContext.png",
"renders\character_body_fit_prep_v1\04_ReflectionScenePreserved.png",
"renders\character_body_fit_prep_v1\CharacterBodyFitPrep_report.txt",
"renders\character_body_fit_prep_v1\CharacterBodyFitPrep_status.json",
"reports\character_body_fit_prep_v1\Character_Body_Fit_Prep_v1.md",
"reports\character_body_fit_prep_v1\character_body_fit_prep_v1.json",
"renders\current_review\01_BodyFitFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CHARACTER BODY FIT PREP VALIDATION PASS ==="
