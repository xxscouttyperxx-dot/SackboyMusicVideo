$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
git -C $Root config http.version HTTP/1.1
git -C $Root config http.postBuffer 1048576000
git -C $Root config lfs.concurrenttransfers 1
git -C $Root config lfs.basictransfersonly true
git -C $Root config lfs.activitytimeout 300
git -C $Root config lfs.dialtimeout 300
git -C $Root config lfs.tlstimeout 300
git -C $Root config lfs.transfer.maxretries 10
git -C $Root config lfs.transfer.maxretrydelay 30
git -C $Root checkout -- "blender/sackboy_scene.blend1" 2>$null

function GitAddExistingOrDeleted {
    param([string[]]$Paths)
    foreach($Rel in $Paths){
        $Full = Join-Path $Root $Rel
        if(Test-Path $Full){
            git -C $Root add -A -- $Rel
            if($LASTEXITCODE -ne 0){throw "git add failed: $Rel"}
        } else {
            $Tracked = git -C $Root ls-files -- $Rel
            if(-not [string]::IsNullOrWhiteSpace($Tracked)){
                git -C $Root add -A -- $Rel
                if($LASTEXITCODE -ne 0){throw "git add failed deleted: $Rel"}
            }
        }
    }
}

Write-Host "[Publish] Staging current baseline annotation outputs and current blend..."
GitAddExistingOrDeleted @(
    "blender\sackboy_scene.blend",
    "blender\scripts",
    "reports",
    "renders\current_review",
    "Apply-CurrentBaselineAnnotation.ps1",
    "Validate-CurrentBaselineAnnotation.ps1",
    "Publish-CurrentReview.ps1",
    "README-CurrentBaselineAnnotation.txt"
)

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[Publish] Nothing to commit."
} else {
    git -C $Root commit -m "Annotate current baseline after manual cleanup"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}

for($i=1; $i -le 3; $i++){
    Write-Host "[Publish] git lfs push attempt $i of 3..."
    git -C $Root lfs push origin main
    if($LASTEXITCODE -eq 0){ break }
    if($i -eq 3){ throw "git lfs push failed after 3 attempts" }
    Start-Sleep -Seconds (15 * $i)
}

git -C $Root push origin main
if($LASTEXITCODE -ne 0){throw "git push failed"}
Write-Host "[Publish] Done."
