$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
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
Write-Host "=== PARKING TEXTURE DECAL / FIT PREP VALIDATION PASS ==="
