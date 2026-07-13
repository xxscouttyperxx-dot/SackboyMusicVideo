$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\current_review\01_DIAG_FullFront_SOLID.png",
"renders\current_review\02_DIAG_Full3Q_SOLID.png",
"renders\current_review\03_DIAG_Full3Q_RENDERED.png",
"renders\current_review\04_DIAG_LeftArmpit_SOLID.png",
"renders\current_review\05_DIAG_RightArmpit_SOLID.png",
"renders\current_review\06_DIAG_HoodTop_SOLID.png",
"reports\diagnostic_cameras_mesh_export_v1\Diagnostic_Cameras_Mesh_Export_v1.md",
"reports\diagnostic_cameras_mesh_export_v1\DiagnosticCamerasMeshExport_status.json",
"reports\diagnostic_cameras_mesh_export_v1\diagnostic_cameras_mesh_export_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== DIAGNOSTIC CAMERAS + MESH EXPORT VALIDATION PASS ==="
