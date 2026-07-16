param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

Write-Host "=== CLEAN ANIMATION BASELINE V1 ==="
Write-Host "Approved scope only: F2, hoodie, pants, eyes, shoe meshes, and Shoes Empty."
Write-Host "No armature creation. No global origin cleanup. No effect-object edits. No backup blend creation."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\clean_animation_baseline_v1.py")){throw "Missing Blender script"}

$beforeBackups = @(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\clean_animation_baseline_v1.py"
if($LASTEXITCODE -ne 0){throw "Blender clean baseline script failed with exit code $LASTEXITCODE"}

$afterBackups = @(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Blend saved: blender\sackboy_scene.blend"
Write-Host "Report: reports\clean_animation_baseline_v1"
Write-Host "No armature was created."
Write-Host "No backup blend was created."
