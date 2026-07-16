param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

Write-Host "=== SACKBOY F2-ONLY BIND / WEIGHTS V1 ==="
Write-Host "Binds only F2 to the approved custom armature."
Write-Host "Clothing, eyes, shoes, effects, cameras, lights, and environment remain untouched."
Write-Host "No test pose or animation is created in this stage."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\f2_bind_weights_v1.py")){throw "Missing Blender script"}

$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\f2_bind_weights_v1.py"
if($LASTEXITCODE -ne 0){throw "Blender F2 binding failed with exit code $LASTEXITCODE"}

$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "F2 was bound and weighted."
Write-Host "No clothing or accessory binding occurred."
Write-Host "No test pose or animation was created."
