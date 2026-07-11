$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\StorefrontParkingV1C-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){ if(-not(Test-Path $Item)){throw "Required item missing: $Item"} }

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_StorefrontParkingV1C.blend") -Force
Copy-Item (Join-Path $PatchScripts "storefront_parking_v1c.py") (Join-Path $Scripts "storefront_parking_v1c.py") -Force

Write-Host "[StorefrontParkingV1C] Cleaning old package root files..."
$Keep=@("Apply-StorefrontParkingV1C.ps1","Validate-StorefrontParkingV1C.ps1","Publish-CurrentReview.ps1","Clean-PackageRoot.ps1","README-StorefrontParkingV1C.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-Step*.ps1","Validate-Step*.ps1","README-Step*.txt","Apply-Production*.ps1","Validate-Production*.ps1","README-Production*.txt","Apply-Project*.ps1","Validate-Project*.ps1","README-Project*.txt","Apply-HeroCar*.ps1","Validate-HeroCar*.ps1","README-HeroCar*.txt","Apply-LampSidewalkSkyCleanup.ps1","Validate-LampSidewalkSkyCleanup.ps1","README-LampSidewalkSkyCleanup.txt","Apply-PublishFix.ps1","README-PublishFix.txt")
foreach($Pattern in $Patterns){ Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue | Where-Object {$Keep -notcontains $_.Name} | Remove-Item -Force }

Write-Host "[StorefrontParkingV1C] Rebuilding storefront scale, sidewalk/curb, H parking, lamps, and visible storefront cleanup..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "storefront_parking_v1c.py")
if($LASTEXITCODE -ne 0){throw "Storefront/Parking v1C failed."}

$Expected=@("renders\storefront_parking_v1c\01_StorefrontScale.png","renders\storefront_parking_v1c\02_ParkingLampLayout.png","renders\storefront_parking_v1c\03_SkyStoreHero.png","renders\storefront_parking_v1c\StorefrontParkingV1C_status.json","renders\storefront_parking_v1c\StorefrontParkingV1C_report.txt","renders\current_review\01_StorefrontScale.png")
foreach($Rel in $Expected){ if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"} }

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== STOREFRONT / PARKING V1C PASS ==="
Write-Host "Signs removed; storefronts rebuilt larger and farther apart."
Write-Host "Glass reaches sidewalk; conjoined frames and double-door frame sections created."
Write-Host "Sidewalk widened with curb edge and indent groove."
Write-Host "Parking spaces rebuilt as H-shaped layout."
Write-Host "Lamp posts moved to parking-space quarter intersections."
Write-Host "HDRI world strengthened and visible sky backdrop added."
Write-Host "Current review renders updated."
Write-Host "Backup: $BackupRoot"
