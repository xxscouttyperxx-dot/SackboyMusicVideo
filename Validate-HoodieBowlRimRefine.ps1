$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_bowl_rim_refine_v1\01_HoodieMaterialPreviewShape.png",
"renders\hoodie_bowl_rim_refine_v1\02_HoodieSolidGrayShape.png",
"renders\hoodie_bowl_rim_refine_v1\03_HoodieWireEdgeShape.png",
"renders\hoodie_bowl_rim_refine_v1\04_HoodieScenePreserved.png",
"renders\hoodie_bowl_rim_refine_v1\HoodieBowlRimRefine_report.txt",
"renders\hoodie_bowl_rim_refine_v1\HoodieBowlRimRefine_status.json",
"reports\hoodie_bowl_rim_refine_v1\Hoodie_Bowl_Rim_Refine_v1.md",
"reports\hoodie_bowl_rim_refine_v1\hoodie_bowl_rim_refine_v1.json",
"renders\current_review\01_HoodieMaterialPreviewShape.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE BOWL RIM REFINE VALIDATION PASS ==="
