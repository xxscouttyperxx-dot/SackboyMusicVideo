$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\current_review\01_SEAM_FullFront_BoundaryOverlay.png",
"renders\current_review\02_SEAM_LeftArmpit_BoundaryOverlay.png",
"renders\current_review\03_SEAM_RightArmpit_BoundaryOverlay.png",
"renders\current_review\04_SEAM_HoodCollar_BoundaryOverlay.png",
"renders\current_review\05_SEAM_HoodTop_BoundaryOverlay.png",
"reports\seam_diagnostic_audit_v1\Seam_Diagnostic_Audit_v1.md",
"reports\seam_diagnostic_audit_v1\SeamDiagnosticAudit_status.json",
"reports\seam_diagnostic_audit_v1\seam_diagnostic_audit_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== SEAM DIAGNOSTIC AUDIT VALIDATION PASS ==="
