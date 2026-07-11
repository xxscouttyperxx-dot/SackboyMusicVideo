$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\scene_cleanup_flat_asphalt_v1B\01_FlatAsphaltPaintCheck.png",
"renders\scene_cleanup_flat_asphalt_v1B\02_DecimatePreviewCheck.png",
"renders\scene_cleanup_flat_asphalt_v1B\SceneCleanupFlatAsphalt_report.txt",
"renders\scene_cleanup_flat_asphalt_v1B\SceneCleanupFlatAsphalt_status.json",
"reports\scene_cleanup_flat_asphalt_v1B\Scene_Cleanup_Flat_Asphalt_v1B.md",
"reports\scene_cleanup_flat_asphalt_v1B\scene_cleanup_flat_asphalt_v1B.json",
"renders\current_review\01_FlatAsphaltPaintCheck.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== SCENE CLEANUP / FLAT ASPHALT v1B VALIDATION PASS ==="
