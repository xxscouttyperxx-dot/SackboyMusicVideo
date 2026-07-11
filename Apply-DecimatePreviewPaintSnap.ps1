$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\DecimatePreviewPaintSnap-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_DecimatePreviewPaintSnap.blend") -Force
Copy-Item (Join-Path $PatchScripts "decimate_preview_paint_snap_v1B.py") (Join-Path $Scripts "decimate_preview_paint_snap_v1B.py") -Force

Write-Host "[DecimatePreviewPaintSnap] Cleaning old package root files..."
$Keep=@(
    "Apply-DecimatePreviewPaintSnap.ps1",
    "Validate-DecimatePreviewPaintSnap.ps1",
    "Publish-CurrentReview.ps1",
    "README-DecimatePreviewPaintSnap.txt",
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

Write-Host "[DecimatePreviewPaintSnap] Adding non-destructive decimation previews and improving parking paint snap..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "decimate_preview_paint_snap_v1B.py")
if($LASTEXITCODE -ne 0){throw "Decimate preview / paint snap failed."}

$Expected=@(
"renders\decimate_preview_paint_snap_v1B\01_DecimatePreviewOverview.png",
"renders\decimate_preview_paint_snap_v1B\02_SelectedMeshesPreview.png",
"renders\decimate_preview_paint_snap_v1B\03_ParkingPaintSnapImproved.png",
"renders\decimate_preview_paint_snap_v1B\DecimatePreviewPaintSnap_report.txt",
"renders\decimate_preview_paint_snap_v1B\DecimatePreviewPaintSnap_status.json",
"reports\decimate_preview_paint_snap_v1B\Decimate_Preview_Paint_Snap_v1B.md",
"reports\decimate_preview_paint_snap_v1B\decimate_preview_paint_snap_v1B.json",
"renders\current_review\01_DecimatePreviewOverview.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== DECIMATE PREVIEW / PAINT SNAP PASS ==="
Write-Host "Added non-destructive decimate preview modifiers to hoodie, utility box, and trash can lid."
Write-Host "No automatic destructive decimation was applied."
Write-Host "Improved parking paint snap by repositioning paint strips to sit just above the asphalt and keeping shrinkwrap preview modifiers."
Write-Host "No lights, car, storefront, sky/world/HDRI, no-parking sign, traffic cone, cargo pants, or shoes were modified."
Write-Host "Current review renders updated."
Write-Host "Backup: $BackupRoot"
