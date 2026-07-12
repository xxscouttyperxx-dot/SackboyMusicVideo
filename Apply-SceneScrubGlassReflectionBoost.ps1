$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\SceneScrubGlassReflectionBoost-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_SceneScrubGlassReflectionBoost.blend") -Force
Copy-Item (Join-Path $PatchScripts "scene_scrub_glass_reflection_boost_v1.py") (Join-Path $Scripts "scene_scrub_glass_reflection_boost_v1.py") -Force

Write-Host "[SceneScrubGlassReflectionBoost] Cleaning old package root files..."
$Keep=@("Apply-SceneScrubGlassReflectionBoost.ps1","Validate-SceneScrubGlassReflectionBoost.ps1","Publish-CurrentReview.ps1","README-SceneScrubGlassReflectionBoost.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[SceneScrubGlassReflectionBoost] Removing unwanted edge frames, scrubbing hidden duplicate backups, and boosting glass reflection lights..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "scene_scrub_glass_reflection_boost_v1.py")
if($LASTEXITCODE -ne 0){throw "Scene scrub / glass reflection boost failed."}

$Expected=@(
"renders\scene_scrub_glass_reflection_boost_v1\01_ParkingEdgeScrubCheck.png",
"renders\scene_scrub_glass_reflection_boost_v1\02_GlassReflectionBoostCheck.png",
"renders\scene_scrub_glass_reflection_boost_v1\03_CharacterFitReadyCheck.png",
"renders\scene_scrub_glass_reflection_boost_v1\SceneScrubGlassReflectionBoost_report.txt",
"renders\scene_scrub_glass_reflection_boost_v1\SceneScrubGlassReflectionBoost_status.json",
"reports\scene_scrub_glass_reflection_boost_v1\Scene_Scrub_Glass_Reflection_Boost_v1.md",
"reports\scene_scrub_glass_reflection_boost_v1\scene_scrub_glass_reflection_boost_v1.json",
"renders\current_review\01_ParkingEdgeScrubCheck.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== SCENE SCRUB / GLASS REFLECTION BOOST PASS ==="
Write-Host "Targeted ENV_Frame* parking-edge objects were removed; white parking paint strips were preserved."
Write-Host "Hidden/generated duplicate backup objects were scrubbed to reduce outliner clutter."
Write-Host "Far-end red/white/amber/green reflection spotlights were boosted and glass materials tuned."
Write-Host "HERO_CyanUnderglow_Area was locked to its under-car location."
Write-Host "Character deformation was not applied yet."
Write-Host "Backup: $BackupRoot"
