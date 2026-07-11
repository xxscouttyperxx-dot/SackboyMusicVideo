$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\surface_repair_character_fit_scan_v1B\01_SurfacePaintLowAngle.png",
"renders\surface_repair_character_fit_scan_v1B\02_SurfacePaintTopCheck.png",
"renders\surface_repair_character_fit_scan_v1B\03_CharacterFitScan.png",
"renders\surface_repair_character_fit_scan_v1B\SurfaceRepairCharacterFitScan_report.txt",
"renders\surface_repair_character_fit_scan_v1B\SurfaceRepairCharacterFitScan_status.json",
"reports\surface_repair_character_fit_scan_v1B\Surface_Repair_Character_Fit_Scan_v1B.md",
"reports\surface_repair_character_fit_scan_v1B\surface_repair_character_fit_scan_v1B.json",
"renders\current_review\01_SurfacePaintLowAngle.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== SURFACE REPAIR / CHARACTER FIT SCAN v1B VALIDATION PASS ==="
