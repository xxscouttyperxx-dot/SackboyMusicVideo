$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\GridParkingReflectionLights-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_GridParkingReflectionLights.blend") -Force
Copy-Item (Join-Path $PatchScripts "grid_parking_reflection_lights_v1.py") (Join-Path $Scripts "grid_parking_reflection_lights_v1.py") -Force

Write-Host "[GridParkingReflectionLights] Cleaning old package root files..."
$Keep=@("Apply-GridParkingReflectionLights.ps1","Validate-GridParkingReflectionLights.ps1","Publish-CurrentReview.ps1","README-GridParkingReflectionLights.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[GridParkingReflectionLights] Lowering imported asphalt to grid, restoring original paint strips, locking underglow, and adding reflection lights..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "grid_parking_reflection_lights_v1.py")
if($LASTEXITCODE -ne 0){throw "Grid parking / reflection lights failed."}

$Expected=@(
"renders\grid_parking_reflection_lights_v1\01_GridAsphaltPaintRestored.png",
"renders\grid_parking_reflection_lights_v1\02_ReflectionLightsFarEnd.png",
"renders\grid_parking_reflection_lights_v1\03_CharacterFitNextCheck.png",
"renders\grid_parking_reflection_lights_v1\GridParkingReflectionLights_report.txt",
"renders\grid_parking_reflection_lights_v1\GridParkingReflectionLights_status.json",
"reports\grid_parking_reflection_lights_v1\Grid_Parking_Reflection_Lights_v1.md",
"reports\grid_parking_reflection_lights_v1\grid_parking_reflection_lights_v1.json",
"renders\current_review\01_GridAsphaltPaintRestored.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== GRID PARKING / REFLECTION LIGHTS PASS ==="
Write-Host "Imported asphalt was flattened/lowered to the grid."
Write-Host "Original parking paint strip meshes were restored at grid level."
Write-Host "HERO_CyanUnderglow_Area was locked to its under-car location."
Write-Host "Far-end red/white/amber/green reflection spotlights were added. No blue."
Write-Host "Character deformation was not applied yet; fit scan and next plan were recorded."
Write-Host "Backup: $BackupRoot"
