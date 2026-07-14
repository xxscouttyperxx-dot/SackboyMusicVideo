param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",[string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== SEAM PATCH RECOVERY V1I ==="
Write-Host "Purpose: fixed recovery after v1G saved the blend but crashed while writing final status."
Write-Host "Mode: audit/render/report only. No geometry changes and no new Backups blend files."
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\seam_patch_recovery_v1I.py")){throw "Missing seam_patch_recovery_v1I.py"}
$beforeBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\seam_patch_recovery_v1I.py"
if($LASTEXITCODE -ne 0){throw "Blender seam patch recovery v1I failed with exit code $LASTEXITCODE"}
$afterBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBlendTime -ne $beforeBlendTime){throw "Safety stop: .blend timestamp changed. Recovery package is audit/render/report only."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups folder blend-file count changed."}
Write-Host "=== SEAM PATCH RECOVERY V1I COMPLETE ==="
Write-Host "Reports: reports\seam_patch_recovery_v1I"
Write-Host "Renders: renders\current_review"
Write-Host "No .blend save detected."
Write-Host "No new Backups .blend files detected."
