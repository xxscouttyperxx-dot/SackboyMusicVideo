param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$ScriptPath=".\blender\scripts\clothing_accessory_bind_v1.py"

Write-Host "=== SACKBOY CLOTHING / ACCESSORY BIND V1 ==="
Write-Host "Transfers approved F2 weights to hoodie and pants."
Write-Host "Rigidly attaches eyes to head and shoes to their foot bones."
Write-Host "Preserves the existing F2 deformation-test action and protected scene."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path $ScriptPath)){throw "Missing Blender script: $ScriptPath"}

$scriptText=Get-Content $ScriptPath -Raw
if($scriptText -notmatch 'SCRIPT_VERSION="1\.0"'){
    throw "Safety stop: clothing/accessory binding script identity marker is missing."
}

$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python $ScriptPath
if($LASTEXITCODE -ne 0){throw "Blender clothing/accessory binding failed with exit code $LASTEXITCODE"}

$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Hoodie and pants received transferred F2 weights."
Write-Host "Eyes were attached to head; shoes were attached to foot bones."
Write-Host "Existing deformation-test action was preserved."
