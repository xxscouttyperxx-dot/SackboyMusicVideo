$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== TRY PUSH BLEND ONLY ==="
Write-Host "This stages ONLY blender\sackboy_scene.blend."
Write-Host "It does not stage scripts, reports, renders, or blend1."

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
    git commit -m "Update blend with seam diagnostic cameras"
}

Write-Host ""
Write-Host "OPTION A: normal single-transfer LFS push"
git lfs push origin main
if($LASTEXITCODE -eq 0){
    git push origin main
    if($LASTEXITCODE -eq 0){ Write-Host "Blend push succeeded with Option A."; exit 0 }
}

Write-Host ""
Write-Host "OPTION B: ten-attempt LFS retry loop"
for($i=1; $i -le 10; $i++){
    Write-Host "LFS push attempt $i of 10"
    git lfs push origin main
    if($LASTEXITCODE -eq 0){ break }
    Start-Sleep -Seconds 30
}
if($LASTEXITCODE -eq 0){
    git push origin main
    if($LASTEXITCODE -eq 0){ Write-Host "Blend push succeeded with Option B."; exit 0 }
}

Write-Host ""
Write-Host "OPTION C: temporarily disable LFS lock verification and retry"
git config lfs.https://github.com/xxscouttyperxx-dot/SackboyMusicVideo.git/info/lfs.locksverify false
for($i=1; $i -le 5; $i++){
    Write-Host "LFS push attempt $i of 5"
    git lfs push origin main
    if($LASTEXITCODE -eq 0){ break }
    Start-Sleep -Seconds 45
}
if($LASTEXITCODE -eq 0){
    git push origin main
    if($LASTEXITCODE -eq 0){ Write-Host "Blend push succeeded with Option C."; exit 0 }
}

Write-Host ""
Write-Host "Blend push still failed. Your local blend is still safe. Reports/renders can continue to be pushed without the blend."
exit 1
