$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
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
Write-Host "=== DECIMATE PREVIEW / PAINT SNAP VALIDATION PASS ==="
