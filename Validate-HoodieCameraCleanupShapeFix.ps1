$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_camera_cleanup_shape_fix_v1\01_HoodieMaterialShape.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\02_HoodieLeftSideGray.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\03_HoodieRightSideGray.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\04_HoodieIsolatedWireCheck.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\05_HoodieScenePreserved.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\HoodieCameraCleanupShapeFix_report.txt",
"renders\hoodie_camera_cleanup_shape_fix_v1\HoodieCameraCleanupShapeFix_status.json",
"reports\hoodie_camera_cleanup_shape_fix_v1\Hoodie_Camera_Cleanup_Shape_Fix_v1.md",
"reports\hoodie_camera_cleanup_shape_fix_v1\hoodie_camera_cleanup_shape_fix_v1.json",
"renders\current_review\01_HoodieMaterialShape.png"
)
foreach($Rel in $Expected){if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}}
Write-Host "=== HOODIE CAMERA CLEANUP / SHAPE FIX VALIDATION PASS ==="
