$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@("renders\storefront_parking_v1c\01_StorefrontScale.png","renders\storefront_parking_v1c\02_ParkingLampLayout.png","renders\storefront_parking_v1c\03_SkyStoreHero.png","renders\storefront_parking_v1c\StorefrontParkingV1C_status.json","renders\storefront_parking_v1c\StorefrontParkingV1C_report.txt","renders\current_review\01_StorefrontScale.png")
foreach($Rel in $Expected){ if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"} }
Write-Host "=== STOREFRONT / PARKING V1C VALIDATION PASS ==="
