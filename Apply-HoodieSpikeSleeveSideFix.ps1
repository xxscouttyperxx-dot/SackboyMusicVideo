$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieSpikeSleeveSideFix-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieSpikeSleeveSideFix.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_spike_sleeve_side_fix_v1.py") (Join-Path $Scripts "hoodie_spike_sleeve_side_fix_v1.py") -Force

Write-Host "[HoodieSpikeSleeveSideFix] Cleaning old package root files..."
$Keep=@("Apply-HoodieSpikeSleeveSideFix.ps1","Validate-HoodieSpikeSleeveSideFix.ps1","Publish-CurrentReview.ps1","README-HoodieSpikeSleeveSideFix.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieSpikeSleeveSideFix] Fixing spikes, sleeves, and side folds..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_spike_sleeve_side_fix_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie spike/sleeve/side fix failed."}

$Expected=@(
"renders\hoodie_spike_sleeve_side_fix_v1\01_HoodieMaterialPreviewShape.png",
"renders\hoodie_spike_sleeve_side_fix_v1\02_HoodieLeftGraySide.png",
"renders\hoodie_spike_sleeve_side_fix_v1\03_HoodieRightGraySide.png",
"renders\hoodie_spike_sleeve_side_fix_v1\04_HoodieWireSpikeCheck.png",
"renders\hoodie_spike_sleeve_side_fix_v1\05_HoodieScenePreserved.png",
"renders\hoodie_spike_sleeve_side_fix_v1\HoodieSpikeSleeveSideFix_report.txt",
"renders\hoodie_spike_sleeve_side_fix_v1\HoodieSpikeSleeveSideFix_status.json",
"reports\hoodie_spike_sleeve_side_fix_v1\Hoodie_Spike_Sleeve_Side_Fix_v1.md",
"reports\hoodie_spike_sleeve_side_fix_v1\hoodie_spike_sleeve_side_fix_v1.json",
"renders\current_review\01_HoodieMaterialPreviewShape.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE SPIKE / SLEEVE / SIDE FIX PASS ==="
Write-Host "Wire spikes were smoothed, sleeves were thickened more uniformly, and convex side folds were reduced."
Write-Host "Review cameras now use one material preview, left/right gray side views, one wire check, and one scene preservation view."
Write-Host "Vertex/face counts and dimensional deltas were written to the report."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
