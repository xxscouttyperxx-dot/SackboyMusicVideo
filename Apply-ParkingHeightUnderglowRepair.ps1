$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\ParkingHeightUnderglowRepair-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_ParkingHeightUnderglowRepair.blend") -Force
Copy-Item (Join-Path $PatchScripts "parking_height_underglow_repair_v1.py") (Join-Path $Scripts "parking_height_underglow_repair_v1.py") -Force

Write-Host "[ParkingHeightUnderglowRepair] Cleaning old package root files..."
$Keep=@("Apply-ParkingHeightUnderglowRepair.ps1","Validate-ParkingHeightUnderglowRepair.ps1","Publish-CurrentReview.ps1","README-ParkingHeightUnderglowRepair.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[ParkingHeightUnderglowRepair] Lowering imported asphalt, rebuilding decals, removing bad plaza decal, and restoring underglow..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "parking_height_underglow_repair_v1.py")
if($LASTEXITCODE -ne 0){throw "Parking height / underglow repair failed."}

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

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== PARKING HEIGHT / UNDERGLOW REPAIR PASS ==="
Write-Host "Imported asphalt was lowered and flattened to the previous clean surface height."
Write-Host "Bad PARKING_DECAL_*ENV_PlazaShell decal was removed."
Write-Host "Old raised paint meshes remain hidden; flat decals were rebuilt."
Write-Host "HERO_CyanUnderglow_Area was restored to the locked location under the car."
Write-Host "No far-end reflection lights were added in this repair pass."
Write-Host "Backup: $BackupRoot"
