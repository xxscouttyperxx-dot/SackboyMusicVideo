$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\current_review\01_CurrentSceneWide_SOLID.png",
"renders\current_review\02_CurrentSceneWide_RENDERED.png",
"renders\current_review\03_CurrentCharacterThreeQuarter_SOLID.png",
"renders\current_review\04_CurrentCharacterThreeQuarter_RENDERED.png",
"renders\current_review\05_CurrentHoodFront_SOLID.png",
"renders\current_review\06_CurrentHoodLeftSide_SOLID.png",
"renders\current_review\07_CurrentHoodRightSide_SOLID.png",
"reports\current_baseline_annotation_v1\Current_Baseline_Annotation_v1.md",
"reports\current_baseline_annotation_v1\CurrentBaselineAnnotation_status.json",
"reports\current_baseline_annotation_v1\current_baseline_annotation_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CURRENT BASELINE ANNOTATION VALIDATION PASS ==="
