$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$Script=Join-Path $Root "patch\blender\scripts\diagnostic_cameras_mesh_export_v1.py"
$Scripts=Join-Path $Root "blender\scripts"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\DiagnosticCamerasMeshExport-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Blend,$Script,$BlenderExe,$Scripts)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_DiagnosticCamerasMeshExport.blend") -Force
Copy-Item $Script (Join-Path $Scripts "diagnostic_cameras_mesh_export_v1.py") -Force

Write-Host "[DiagnosticCamerasMeshExport] Creating current diagnostic cameras, renders, and targeted mesh exports..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "diagnostic_cameras_mesh_export_v1.py")
if($LASTEXITCODE -ne 0){throw "Diagnostic cameras mesh export failed."}

$Expected=@(
"renders\current_review\01_DIAG_FullFront_SOLID.png",
"renders\current_review\02_DIAG_Full3Q_SOLID.png",
"renders\current_review\03_DIAG_Full3Q_RENDERED.png",
"renders\current_review\04_DIAG_LeftArmpit_SOLID.png",
"renders\current_review\05_DIAG_RightArmpit_SOLID.png",
"renders\current_review\06_DIAG_HoodTop_SOLID.png",
"reports\diagnostic_cameras_mesh_export_v1\Diagnostic_Cameras_Mesh_Export_v1.md",
"reports\diagnostic_cameras_mesh_export_v1\DiagnosticCamerasMeshExport_status.json",
"reports\diagnostic_cameras_mesh_export_v1\diagnostic_cameras_mesh_export_v1.json",
"reports\diagnostic_cameras_mesh_export_v1\mesh_diagnostics.csv"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== DIAGNOSTIC CAMERAS + MESH EXPORT PASS ==="
Write-Host "Fresh diagnostic cameras created after deleting previous DIAG_CURRENT_* cameras."
Write-Host "Targeted OBJ exports and mesh diagnostics written to reports\diagnostic_cameras_mesh_export_v1."
Write-Host "Blend saved locally so diagnostic cameras remain available."
Write-Host "Backup: $BackupRoot"
