param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",[string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== RESIDUAL SEAM CONSOLIDATION V1F ==="
Write-Host "Fixed v1E. Hoodie only; no Backups blend writes; close-up renders hide Sackboy/body/accessories."
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\residual_seam_consolidation_v1F.py")){throw "Missing residual_seam_consolidation_v1F.py"}
$beforeBlendSize=(Get-Item ".\blender\sackboy_scene.blend").Length
$beforeBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\residual_seam_consolidation_v1F.py"
if($LASTEXITCODE -ne 0){throw "Blender residual seam consolidation v1F failed with exit code $LASTEXITCODE"}
$afterBlend=Get-Item ".\blender\sackboy_scene.blend"
$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBlend.LastWriteTimeUtc -eq $beforeBlendTime){throw "Safety stop: blend timestamp did not change."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups folder blend-file count changed."}
$deltaKB=[math]::Round(($afterBlend.Length-$beforeBlendSize)/1KB,0)
Write-Host "=== RESIDUAL SEAM CONSOLIDATION V1F COMPLETE ==="
Write-Host "Reports: reports\residual_seam_consolidation_v1F"
Write-Host "Renders: renders\current_review"
Write-Host "Blend saved successfully. Size delta (KB): $deltaKB"
Write-Host "No new Backups .blend files detected."
