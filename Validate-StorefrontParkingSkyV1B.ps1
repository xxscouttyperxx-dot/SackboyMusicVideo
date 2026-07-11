$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@("renders\storefront_parking_sky_v1\01_StorefrontScale.png","renders\storefront_parking_sky_v1\02_ParkingLampLayout.png","renders\storefront_parking_sky_v1\03_SkyStoreHero.png","renders\storefront_parking_sky_v1\StorefrontParkingSky_status.json","renders\storefront_parking_sky_v1\StorefrontParkingSky_report.txt","renders\current_review\01_StorefrontScale.png")
foreach($Rel in $Expected){ if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"} }
Write-Host "=== STOREFRONT / PARKING / SKY V1B VALIDATION PASS ==="
