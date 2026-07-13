$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
Write-Host "=== TRY PUSH BLEND ONLY ==="
git config http.version HTTP/1.1
git config http.postBuffer 1048576000
git config lfs.concurrenttransfers 1
git config lfs.basictransfersonly true
git config lfs.activitytimeout 300
git config lfs.dialtimeout 300
git config lfs.tlstimeout 300
git config lfs.transfer.maxretries 20
git config lfs.transfer.maxretrydelay 30
git add -A -- "blender\sackboy_scene.blend"
git checkout -- "blender\sackboy_scene.blend1" 2>$null
$Status = git status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "Nothing to commit."
} else {
    git commit -m "Update blend with v1B seam diagnostic cameras"
}
git lfs push origin main
if($LASTEXITCODE -eq 0){
    git push origin main
    if($LASTEXITCODE -eq 0){ Write-Host "Blend push succeeded."; exit 0 }
}
Write-Host "Blend push failed or nothing changed. Local blend is safe."
exit 1
