$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\ParkingTextureDecalFitPrep-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_ParkingTextureDecalFitPrep.blend") -Force
Copy-Item (Join-Path $PatchScripts "parking_texture_decal_fit_prep_v1.py") (Join-Path $Scripts "parking_texture_decal_fit_prep_v1.py") -Force

Write-Host "[ParkingTextureDecalFitPrep] Cleaning old package root files..."
$Keep=@("Apply-ParkingTextureDecalFitPrep.ps1","Validate-ParkingTextureDecalFitPrep.ps1","Publish-CurrentReview.ps1","README-ParkingTextureDecalFitPrep.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[ParkingTextureDecalFitPrep] Making imported asphalt active, rebuilding paint as flat decals, and scanning fit data..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "parking_texture_decal_fit_prep_v1.py")
if($LASTEXITCODE -ne 0){throw "Parking texture decal / fit prep failed."}

$Expected=@(
"renders\parking_texture_decal_fit_prep_v1\01_PaintDecalLowAngle.png",
"renders\parking_texture_decal_fit_prep_v1\02_PaintDecalTopCheck.png",
"renders\parking_texture_decal_fit_prep_v1\03_CharacterFitPrepScan.png",
"renders\parking_texture_decal_fit_prep_v1\ParkingTextureDecalFitPrep_report.txt",
"renders\parking_texture_decal_fit_prep_v1\ParkingTextureDecalFitPrep_status.json",
"reports\parking_texture_decal_fit_prep_v1\Parking_Texture_Decal_Fit_Prep_v1.md",
"reports\parking_texture_decal_fit_prep_v1\parking_texture_decal_fit_prep_v1.json",
"renders\current_review\01_PaintDecalLowAngle.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== PARKING TEXTURE DECAL / FIT PREP PASS ==="
Write-Host "Imported Asphalt ground is visible and flattened."
Write-Host "ENV_Asphalt was hidden to avoid z-fighting with the imported asphalt."
Write-Host "Old raised paint-strip meshes were hidden and replaced with flat decal planes."
Write-Host "Hatch/manhole was placed on the active asphalt surface."
Write-Host "Existing lights were scanned and preserved. No reflection lights were added."
Write-Host "Character/clothing measurements were recorded; no body or clothing deformation was applied yet."
Write-Host "Backup: $BackupRoot"
