param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",[string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== COLLAR PARALLEL SNAP V1N ==="
Write-Host "Purpose: collar-only aggressive parallel seam snap for remaining large hood/sweater gap."
Write-Host "Rules: collar only; hoodie only; reversible shape key; no topology changes; no Backups blend writes; no .blend1 staging."
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\collar_parallel_snap_v1N.py")){throw "Missing collar_parallel_snap_v1N.py"}
$beforeBlendSize=(Get-Item ".\blender\sackboy_scene.blend").Length
$beforeBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\collar_parallel_snap_v1N.py"
if($LASTEXITCODE -ne 0){throw "Blender collar parallel snap v1N failed with exit code $LASTEXITCODE"}
$afterBlend=Get-Item ".\blender\sackboy_scene.blend"
$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBlend.LastWriteTimeUtc -eq $beforeBlendTime){throw "Safety stop: blend timestamp did not change; v1N did not save."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups folder blend-file count changed."}
$deltaKB=[math]::Round(($afterBlend.Length-$beforeBlendSize)/1KB,0)
Write-Host "=== COLLAR PARALLEL SNAP V1N COMPLETE ==="
Write-Host "Reports: reports\collar_parallel_snap_v1N"
Write-Host "Renders: renders\current_review"
Write-Host "Blend saved successfully. Size delta (KB): $deltaKB"
Write-Host "No new Backups .blend files detected."
