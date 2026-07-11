$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\MeshAuditOptimizationPreview-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_MeshAuditOptimizationPreview.blend") -Force
Copy-Item (Join-Path $PatchScripts "mesh_audit_optimization_preview_v1.py") (Join-Path $Scripts "mesh_audit_optimization_preview_v1.py") -Force

Write-Host "[MeshAuditOptimizationPreview] Cleaning old package root files..."
$Keep=@(
    "Apply-MeshAuditOptimizationPreview.ps1",
    "Validate-MeshAuditOptimizationPreview.ps1",
    "Publish-CurrentReview.ps1",
    "README-MeshAuditOptimizationPreview.txt",
    "README_FIRST.txt",
    "Run-BuildAll.ps1",
    "Run-DiagnosticRenders.ps1"
)
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[MeshAuditOptimizationPreview] Preserving current baseline; auditing imported meshes and preview-snapping parking paint strips..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "mesh_audit_optimization_preview_v1.py")
if($LASTEXITCODE -ne 0){throw "Mesh audit / optimization preview failed."}

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

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== MESH AUDIT / OPTIMIZATION PREVIEW PASS ==="
Write-Host "Current scene layout, clothing placement, car placement, sky, storefront, and locked lights preserved."
Write-Host "No automatic decimation was applied. This is an audit/preview pass only."
Write-Host "Imported clothing/prop meshes were scanned for vertex/face density and optimization candidates."
Write-Host "Parking paint strips received preview snap modifiers to sit on the asphalt more cleanly."
Write-Host "Current review renders and audit reports updated."
Write-Host "Backup: $BackupRoot"
