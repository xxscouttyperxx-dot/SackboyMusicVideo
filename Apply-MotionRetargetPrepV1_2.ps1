param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$PreflightPath=".\blender\scripts\preflight_motion_retarget_prep_v1_2.py"
$ScriptPath=".\blender\scripts\motion_retarget_prep_v1_2.py"

Write-Host "=== SACKBOY MOTION RETARGET PREP V1.2 ==="
Write-Host "Normalizes animated protected-object comparisons to the same frame."
Write-Host "The project opens only after collection and protected-frame regressions pass."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path $PreflightPath)){throw "Missing corrected Blender preflight: $PreflightPath"}
if(!(Test-Path $ScriptPath)){throw "Missing corrected production script: $ScriptPath"}

$preflightText=Get-Content $PreflightPath -Raw
$scriptText=Get-Content $ScriptPath -Raw

if($preflightText -notmatch 'SCRIPT_VERSION="1\.2"'){
    throw "Safety stop: Stage 12 v1.2 preflight identity marker was not found."
}
if($scriptText -notmatch 'SCRIPT_VERSION="1\.2"'){
    throw "Safety stop: Stage 12 v1.2 production identity marker was not found."
}
if($preflightText -notmatch 'protected_frame_regression'){
    throw "Safety stop: animated protected-object regression marker was not found."
}
if($scriptText -notmatch 'SAME_FRAME_EVALUATED_STATE'){
    throw "Safety stop: same-frame protected snapshot marker was not found."
}
if($scriptText -notmatch 'ProtectedObjectDiagnosticV1_2\.json'){
    throw "Safety stop: protected-object diagnostic marker was not found."
}
if($scriptText -notmatch 'scene\.frame_set\(protected_check_frame\)'){
    throw "Safety stop: protected comparison frame normalization was not found."
}

Write-Host "Verified Stage 12 v1.2 scripts and same-frame protected-object logic."
Write-Host "Running Blender collection and protected-frame preflight tests..."

& $BlenderExe --background --factory-startup --python-exit-code 1 --python $PreflightPath
if($LASTEXITCODE -ne 0){throw "Blender Stage 12 v1.2 preflight failed with exit code $LASTEXITCODE"}

Write-Host "Blender Stage 12 v1.2 preflight passed."
Write-Host "Opening the project and preparing the retarget workflow..."

$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python $ScriptPath
if($LASTEXITCODE -ne 0){throw "Blender motion-retarget preparation failed with exit code $LASTEXITCODE"}

$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Controls-only rig display is now the default."
Write-Host "Use Set-RigViewFullSkeletonV1_2.ps1 to show the deform skeleton."
Write-Host "Use Set-RigViewControlsOnlyV1_2.ps1 to return to the clean animator view."
