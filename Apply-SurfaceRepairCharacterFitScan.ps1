$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\SurfaceRepairCharacterFitScan-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_SurfaceRepairCharacterFitScan_v1B.blend") -Force
Copy-Item (Join-Path $PatchScripts "surface_repair_character_fit_scan_v1B.py") (Join-Path $Scripts "surface_repair_character_fit_scan_v1B.py") -Force

Write-Host "[SurfaceRepairCharacterFitScan v1B] Cleaning old package root files..."
$Keep=@("Apply-SurfaceRepairCharacterFitScan.ps1","Validate-SurfaceRepairCharacterFitScan.ps1","Publish-CurrentReview.ps1","README-SurfaceRepairCharacterFitScan.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[SurfaceRepairCharacterFitScan v1B] Repairing asphalt/paint/hatch and scanning character/clothing fit..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "surface_repair_character_fit_scan_v1B.py")
if($LASTEXITCODE -ne 0){throw "Surface repair / character fit scan v1B failed."}

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

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== SURFACE REPAIR / CHARACTER FIT SCAN v1B PASS ==="
Write-Host "ENV_Asphalt is visible and flat."
Write-Host "Parking paint strips are flattened to zero-height planes just above the asphalt."
Write-Host "Manhole/hatch objects were raised back onto the asphalt surface."
Write-Host "Existing lights were scanned and preserved. No new reflection lights were added."
Write-Host "Character/clothing measurements were recorded; no body or clothing deformation was applied yet."
Write-Host "Backup: $BackupRoot"
