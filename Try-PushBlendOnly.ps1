param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== TRY PUSH BLEND ONLY ==="; Write-Host "Stages ONLY blender\sackboy_scene.blend."
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
git restore --staged . 2>$null
git add -- "blender/sackboy_scene.blend"
git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){Write-Host "No staged blend changes detected."; exit 0}
git commit -m "Update blend with collar bridge repair v1O"
git -c lfs.concurrenttransfers=1 -c lfs.activitytimeout=900 -c lfs.dialtimeout=900 -c lfs.tlstimeout=900 -c lfs.transfer.maxretries=50 -c lfs.transfer.maxretrydelay=60 lfs push origin main
if($LASTEXITCODE -ne 0){throw "Blend LFS push failed."}
git push origin main
if($LASTEXITCODE -ne 0){throw "Blend git push failed."}
Write-Host "Blend push succeeded."
