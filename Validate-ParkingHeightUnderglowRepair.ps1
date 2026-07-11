$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\parking_height_underglow_repair_v1\01_LoweredAsphaltPaintDecals.png",
"renders\parking_height_underglow_repair_v1\02_UnderglowRestoredCheck.png",
"renders\parking_height_underglow_repair_v1\03_CharacterHeightCheck.png",
"renders\parking_height_underglow_repair_v1\ParkingHeightUnderglowRepair_report.txt",
"renders\parking_height_underglow_repair_v1\ParkingHeightUnderglowRepair_status.json",
"reports\parking_height_underglow_repair_v1\Parking_Height_Underglow_Repair_v1.md",
"reports\parking_height_underglow_repair_v1\parking_height_underglow_repair_v1.json",
"renders\current_review\01_LoweredAsphaltPaintDecals.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== PARKING HEIGHT / UNDERGLOW REPAIR VALIDATION PASS ==="
