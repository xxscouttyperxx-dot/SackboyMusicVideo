$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$Script=Join-Path $Root "patch\blender\scripts\seam_diagnostic_audit_v1.py"
$Scripts=Join-Path $Root "blender\scripts"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\SeamDiagnosticAudit-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Blend,$Script,$BlenderExe,$Scripts)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_SeamDiagnosticAudit.blend") -Force
Copy-Item $Script (Join-Path $Scripts "seam_diagnostic_audit_v1.py") -Force

Write-Host "[SeamDiagnosticAudit] Running seam diagnostic audit..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "seam_diagnostic_audit_v1.py")
if($LASTEXITCODE -ne 0){throw "Seam diagnostic audit failed."}

$Expected=@(
"renders\current_review\01_SEAM_FullFront_BoundaryOverlay.png",
"renders\current_review\02_SEAM_LeftArmpit_BoundaryOverlay.png",
"renders\current_review\03_SEAM_RightArmpit_BoundaryOverlay.png",
"renders\current_review\04_SEAM_HoodCollar_BoundaryOverlay.png",
"renders\current_review\05_SEAM_HoodTop_BoundaryOverlay.png",
"reports\seam_diagnostic_audit_v1\Seam_Diagnostic_Audit_v1.md",
"reports\seam_diagnostic_audit_v1\SeamDiagnosticAudit_status.json",
"reports\seam_diagnostic_audit_v1\seam_diagnostic_audit_v1.json",
"reports\seam_diagnostic_audit_v1\seam_zone_csv\left_armpit_boundary_edges.csv",
"reports\seam_diagnostic_audit_v1\seam_zone_csv\right_armpit_boundary_edges.csv",
"reports\seam_diagnostic_audit_v1\seam_zone_csv\hood_collar_band_boundary_edges.csv",
"reports\seam_diagnostic_audit_v1\seam_zone_csv\hood_top_center_boundary_edges.csv"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== SEAM DIAGNOSTIC AUDIT PASS ==="
Write-Host "Fresh seam diagnostic cameras created after deleting previous SEAMDIAG_* cameras."
Write-Host "Temporary boundary overlays were rendered and removed before save."
Write-Host "Reports written under reports\seam_diagnostic_audit_v1."
Write-Host "Blend saved locally so seam cameras remain available."
Write-Host "Backup: $BackupRoot"
