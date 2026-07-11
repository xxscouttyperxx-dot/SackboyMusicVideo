$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\wardrobe_cleanup_asset_intake_v1\01_WardrobeCleanupFront.png",
"renders\wardrobe_cleanup_asset_intake_v1\02_ShoeGraphicCleanup.png",
"renders\wardrobe_cleanup_asset_intake_v1\03_ImportedClothingCandidates.png",
"renders\wardrobe_cleanup_asset_intake_v1\WardrobeCleanupAssetIntake_status.json",
"renders\wardrobe_cleanup_asset_intake_v1\WardrobeCleanupAssetIntake_report.txt",
"renders\current_review\01_WardrobeCleanupFront.png",
"reports\wardrobe_asset_notes\Wardrobe_Asset_Intake_Notes.txt"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== WARDROBE CLEANUP / ASSET INTAKE VALIDATION PASS ==="
