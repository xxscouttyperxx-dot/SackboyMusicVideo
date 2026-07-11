$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\StorefrontParkingSkyV1B-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){ if(-not(Test-Path $Item)){throw "Required item missing: $Item"} }

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_StorefrontParkingSky.blend") -Force
Copy-Item (Join-Path $PatchScripts "storefront_parking_sky_v1.py") (Join-Path $Scripts "storefront_parking_sky_v1.py") -Force

Write-Host "[StorefrontParkingSky] Cleaning old package root files..."
$Keep=@("Apply-StorefrontParkingSkyV1B.ps1","Validate-StorefrontParkingSkyV1B.ps1","Publish-CurrentReview.ps1","Clean-PackageRoot.ps1","README-StorefrontParkingSkyV1B.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-Step*.ps1","Validate-Step*.ps1","README-Step*.txt","Apply-Production*.ps1","Validate-Production*.ps1","README-Production*.txt","Apply-Project*.ps1","Validate-Project*.ps1","README-Project*.txt","Apply-HeroCar*.ps1","Validate-HeroCar*.ps1","README-HeroCar*.txt","Apply-LampSidewalkSkyCleanup.ps1","Validate-LampSidewalkSkyCleanup.ps1","README-LampSidewalkSkyCleanup.txt","Apply-PublishFix.ps1","README-PublishFix.txt")
foreach($Pattern in $Patterns){ Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue | Where-Object {$Keep -notcontains $_.Name} | Remove-Item -Force }

Write-Host "[StorefrontParkingSky] Rebuilding storefront scale, sidewalk/curb, H parking, lamps, and visible sky..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "storefront_parking_sky_v1.py")
if($LASTEXITCODE -ne 0){throw "Storefront/Parking/Sky v1B failed."}

$Expected=@("renders\storefront_parking_sky_v1\01_StorefrontScale.png","renders\storefront_parking_sky_v1\02_ParkingLampLayout.png","renders\storefront_parking_sky_v1\03_SkyStoreHero.png","renders\storefront_parking_sky_v1\StorefrontParkingSky_status.json","renders\storefront_parking_sky_v1\StorefrontParkingSky_report.txt","renders\current_review\01_StorefrontScale.png")
foreach($Rel in $Expected){ if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"} }

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== STOREFRONT / PARKING / SKY V1B PASS ==="
Write-Host "Signs removed; storefronts rebuilt larger and farther apart."
Write-Host "Glass reaches sidewalk; conjoined frames and double-door frame sections created."
Write-Host "Sidewalk widened with curb edge and indent groove."
Write-Host "Parking spaces rebuilt as H-shaped layout."
Write-Host "Lamp posts moved to parking-space quarter intersections."
Write-Host "HDRI world strengthened and visible sky backdrop added."
Write-Host "Current review renders updated."
Write-Host "Backup: $BackupRoot"
