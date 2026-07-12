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
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_SceneScrubGlassReflectionBoost_v1B.blend") -Force
Copy-Item (Join-Path $PatchScripts "scene_scrub_glass_reflection_boost_v1B.py") (Join-Path $Scripts "scene_scrub_glass_reflection_boost_v1B.py") -Force

Write-Host "[SceneScrubGlassReflectionBoost v1B] Cleaning old package root files..."
$Keep=@("Apply-SceneScrubGlassReflectionBoost.ps1","Validate-SceneScrubGlassReflectionBoost.ps1","Publish-CurrentReview.ps1","README-SceneScrubGlassReflectionBoost.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[SceneScrubGlassReflectionBoost v1B] Scrubbing duplicates/rejected frames and building corrected reflection setup..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "scene_scrub_glass_reflection_boost_v1B.py")
if($LASTEXITCODE -ne 0){throw "Scene scrub / glass reflection boost v1B failed."}

$Expected=@(
"renders\scene_scrub_glass_reflection_boost_v1B\01_SceneScrub_Overview.png",
"renders\scene_scrub_glass_reflection_boost_v1B\02_GlassReflectionBoost.png",
"renders\scene_scrub_glass_reflection_boost_v1B\03_ReflectionTrafficSetup.png",
"renders\scene_scrub_glass_reflection_boost_v1B\04_CharacterFitReady.png",
"renders\scene_scrub_glass_reflection_boost_v1B\SceneScrubGlassReflectionBoost_report.txt",
"renders\scene_scrub_glass_reflection_boost_v1B\SceneScrubGlassReflectionBoost_status.json",
"reports\scene_scrub_glass_reflection_boost_v1B\Scene_Scrub_Glass_Reflection_Boost_v1B.md",
"reports\scene_scrub_glass_reflection_boost_v1B\scene_scrub_glass_reflection_boost_v1B.json",
"renders\current_review\01_SceneScrub_Overview.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== SCENE SCRUB / GLASS REFLECTION BOOST v1B PASS ==="
Write-Host "Rejected ENV_Frame* parking-edge objects were removed; white parking paint strips were preserved."
Write-Host "Hidden/generated clutter and stale helper duplicates were scrubbed."
Write-Host "Reflection setup now uses red/yellow/green lights and camera-invisible emissive reflection cards."
Write-Host "Extra fourth/white reflection light was removed."
Write-Host "HERO_CyanUnderglow_Area was locked to the under-car location."
Write-Host "Character deformation was not applied yet."
Write-Host "Backup: $BackupRoot"
