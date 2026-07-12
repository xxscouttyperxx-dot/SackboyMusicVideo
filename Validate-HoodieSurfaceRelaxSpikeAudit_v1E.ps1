$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path

$Expected=@(
"renders\current_review\01_HoodFrontLowAngleMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"reports\hoodie_surface_relax_spike_audit_v1E\HoodieSurfaceRelaxSpikeAudit_v1E_report.txt",
"reports\hoodie_surface_relax_spike_audit_v1E\HoodieSurfaceRelaxSpikeAudit_v1E_status.json",
"reports\hoodie_surface_relax_spike_audit_v1E\Hoodie_Surface_Relax_Spike_Audit_v1E.md",
"reports\hoodie_surface_relax_spike_audit_v1E\hoodie_surface_relax_spike_audit_v1E.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$BadFiles = Get-ChildItem (Join-Path $Root "renders\current_review") -File |
    Where-Object { $_.Extension -in @(".txt",".json",".md") }
if($BadFiles.Count -gt 0){
    throw "current_review contains text/json/md files; expected images only: $($BadFiles.Name -join ', ')"
}

Write-Host "=== HOODIE SURFACE RELAX / SPIKE AUDIT v1E VALIDATION PASS ==="
