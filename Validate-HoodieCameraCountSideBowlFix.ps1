$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\current_review\01_HoodFrontMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"renders\Project changes\HoodieCameraCountSideBowlFix_report.txt",
"renders\Project changes\HoodieCameraCountSideBowlFix_status.json",
"reports\hoodie_camera_count_side_bowl_fix_v1\Hoodie_Camera_Count_Side_Bowl_Fix_v1.md",
"reports\hoodie_camera_count_side_bowl_fix_v1\hoodie_camera_count_side_bowl_fix_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE CAMERA COUNT / SIDE BOWL FIX VALIDATION PASS ==="
