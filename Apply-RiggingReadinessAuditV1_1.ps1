param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

Write-Host "=== RIGGING READINESS AUDIT V1.1 ==="
Write-Host "Mode: strictly read-only. No scene edits, no render-setting edits, no .blend save, no Backups writes."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\rigging_readiness_audit_v1.py")){throw "Missing audit script"}

$blend = Get-Item ".\blender\sackboy_scene.blend"
$beforeTime = $blend.LastWriteTimeUtc
$beforeSize = $blend.Length
$beforeBackups = @(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\rigging_readiness_audit_v1.py"
if($LASTEXITCODE -ne 0){throw "Blender rigging readiness audit failed with exit code $LASTEXITCODE"}

$after = Get-Item ".\blender\sackboy_scene.blend"
$afterBackups = @(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

if($after.LastWriteTimeUtc -ne $beforeTime){throw "Safety stop: .blend timestamp changed during read-only audit."}
if($after.Length -ne $beforeSize){throw "Safety stop: .blend size changed during read-only audit."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== AUDIT COMPLETE ==="
Write-Host "Reports: reports\rigging_readiness_audit_v1"
Write-Host "No .blend save detected."
Write-Host "No Backups .blend creation detected."
