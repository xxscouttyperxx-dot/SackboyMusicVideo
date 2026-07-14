param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",[string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== SEAM ZONE EDIT-STYLE AUDIT V1J ==="
Write-Host "Purpose: diagnostic only. Solid/edit-mode style boundary overlay renders and zone counts."
Write-Host "Rules: no geometry changes, no .blend save, no Backups blend files."
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\seam_zone_edit_style_audit_v1J.py")){throw "Missing seam_zone_edit_style_audit_v1J.py"}
$beforeBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\seam_zone_edit_style_audit_v1J.py"
if($LASTEXITCODE -ne 0){throw "Blender seam zone edit-style audit v1J failed with exit code $LASTEXITCODE"}
$afterBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBlendTime -ne $beforeBlendTime){throw "Safety stop: .blend timestamp changed. This package is diagnostic only."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups folder blend-file count changed."}
Write-Host "=== SEAM ZONE EDIT-STYLE AUDIT V1J COMPLETE ==="
Write-Host "Reports: reports\seam_zone_edit_style_audit_v1J"
Write-Host "Renders: renders\current_review"
Write-Host "No .blend save detected."
Write-Host "No new Backups .blend files detected."
