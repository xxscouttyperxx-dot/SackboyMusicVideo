param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

Write-Host "=== OPTIONAL PUSH AUTOMATED JUMPSTYLE MOCAP BLEND ONLY V1.3 ==="
Write-Host "Stages ONLY blender\sackboy_scene.blend."

git restore --staged . 2>$null
git add -- "blender/sackboy_scene.blend"
git status --short

git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "No staged blend changes detected."
    exit 0
}

git commit -m "Add automatically retargeted jumpstyle animation"

git -c lfs.concurrenttransfers=1 `
    -c lfs.activitytimeout=900 `
    -c lfs.dialtimeout=900 `
    -c lfs.tlstimeout=900 `
    -c lfs.transfer.maxretries=50 `
    -c lfs.transfer.maxretrydelay=60 `
    lfs push origin main
if($LASTEXITCODE -ne 0){throw "LFS push failed"}

git push origin main
if($LASTEXITCODE -ne 0){throw "Git push failed"}

Write-Host "Automated jumpstyle mocap blend push succeeded."
