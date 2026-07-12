$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieSurfaceRelaxSpikeAudit_v1E-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieSurfaceRelaxSpikeAudit_v1E.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_surface_relax_spike_audit_v1E.py") (Join-Path $Scripts "hoodie_surface_relax_spike_audit_v1E.py") -Force

Write-Host "[HoodieSurfaceRelaxSpikeAudit_v1E] Cleaning old package root files..."
$Keep=@("Apply-HoodieSurfaceRelaxSpikeAudit_v1E.ps1","Validate-HoodieSurfaceRelaxSpikeAudit_v1E.ps1","Publish-CurrentReview.ps1","README-HoodieSurfaceRelaxSpikeAudit_v1E.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieSurfaceRelaxSpikeAudit_v1E] Auditing spike geometry and relaxing hood surface depressions..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_surface_relax_spike_audit_v1E.py")
if($LASTEXITCODE -ne 0){throw "Hoodie surface relax spike audit v1E failed."}

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

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE SURFACE RELAX / SPIKE AUDIT v1E PASS ==="
Write-Host "Geometry was audited for true spike/outlier vertices."
Write-Host "Side depressions were treated as broad surface valleys and relaxed/feathered."
Write-Host "Rear droop was lifted/feathered into the hood silhouette."
Write-Host "Current_review was cleaned and contains only current images."
Write-Host "Text/json outputs were written to reports\hoodie_surface_relax_spike_audit_v1E."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
