param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$ScriptPath=".\blender\scripts\f2_deformation_tests_v1_2.py"

Write-Host "=== SACKBOY F2 DEFORMATION TESTS V1.2 ==="
Write-Host "Runs the corrected v1.2 script by its exact filename."
Write-Host "Creates controlled F2-only poses outside the production range."
Write-Host "No clothing/accessory binding, rest-bone edits, or production-frame changes."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path $ScriptPath)){throw "Missing corrected Blender script: $ScriptPath"}

$scriptText=Get-Content $ScriptPath -Raw
if($scriptText -notmatch 'SCRIPT_VERSION="1\.2"'){
    throw "Safety stop: corrected v1.2 script identity marker was not found."
}
if($scriptText -notmatch 'scene\.frame_set\(original_frame\)[\s\S]*# ---------- safety snapshots ----------'){
    throw "Safety stop: same-frame protected-object comparison fix was not found."
}

Write-Host "Verified script: $ScriptPath"
Write-Host "Verified version marker: 1.2"
Write-Host "Verified same-frame protected-object safety fix."

$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python $ScriptPath
if($LASTEXITCODE -ne 0){throw "Blender deformation-test creation failed with exit code $LASTEXITCODE"}

$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Action created: F2_DEFORMATION_TEST_V1_2"
Write-Host "Production frames 1-120 remain at rest."
Write-Host "Test frames: 205, 215, 225, 235, 245, 255, 265"
