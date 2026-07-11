$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
    "renders\mesh_audit_optimization_preview_v1\01_MeshAuditOverview.png",
    "renders\mesh_audit_optimization_preview_v1\02_ImportedAssetsAudit.png",
    "renders\mesh_audit_optimization_preview_v1\03_ParkingPaintSnap.png",
    "renders\mesh_audit_optimization_preview_v1\MeshAuditOptimizationPreview_report.txt",
    "renders\mesh_audit_optimization_preview_v1\MeshAuditOptimizationPreview_status.json",
    "reports\mesh_audit_optimization_preview\mesh_audit_optimization_preview.json",
    "reports\mesh_audit_optimization_preview\Mesh_Audit_Optimization_Preview.md",
    "renders\current_review\01_MeshAuditOverview.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== MESH AUDIT / OPTIMIZATION PREVIEW VALIDATION PASS ==="
