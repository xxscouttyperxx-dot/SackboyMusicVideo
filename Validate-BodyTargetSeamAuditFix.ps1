$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"reports\body_target_seam_audit_fix_v1B\Body_Target_Seam_Audit_Fix_v1B.md",
"reports\body_target_seam_audit_fix_v1B\BodyTargetSeamAuditFix_status.json",
"reports\body_target_seam_audit_fix_v1B\targeted_mesh_exports\current_body_F2.obj",
"reports\body_target_seam_audit_fix_v1B\targeted_mesh_exports\current_hoodie_SACKBOY_Hoodie_EditProxy.obj"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== BODY TARGET + SEAM AUDIT FIX V1B VALIDATION PASS ==="
