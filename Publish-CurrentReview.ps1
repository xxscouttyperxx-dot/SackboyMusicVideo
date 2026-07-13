$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

git -C $Root config http.postBuffer 1048576000
git -C $Root config http.version HTTP/1.1
git -C $Root config lfs.activitytimeout 120
git -C $Root config lfs.dialtimeout 120
git -C $Root config lfs.tlstimeout 120
git -C $Root config lfs.transfer.maxretries 10
git -C $Root config lfs.transfer.maxretrydelay 10
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

GitAddExistingOrDeleted @(
    ".gitignore",
    ".gitattributes",
    "blender\sackboy_scene.blend",
    "blender\scripts",
    "scene_manifest.json",
    "reports",
    "renders\current_review",
    "Apply-CollectionVisibilityFixRetryPush.ps1",
    "Validate-CollectionVisibilityFixRetryPush.ps1",
    "Publish-CurrentReview.ps1",
    "README-CollectionVisibilityFixRetryPush.txt",
    "Apply-SceneCollectionsOrganization.ps1",
    "Validate-SceneCollectionsOrganization.ps1",
    "README-SceneCollectionsOrganization.txt"
)

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[Publish] Nothing new to commit. Will retry push of existing local commits."
} else {
    git -C $Root commit -m "Fix hidden collection visibility after organization"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}

for($i=1; $i -le 5; $i++){
    Write-Host "[Publish] git lfs push attempt $i of 5..."
    git -C $Root lfs push origin main
    if($LASTEXITCODE -eq 0){ break }
    if($i -eq 5){ throw "git lfs push failed after 5 attempts" }
    Start-Sleep -Seconds (10 * $i)
}

for($i=1; $i -le 5; $i++){
    Write-Host "[Publish] git push attempt $i of 5..."
    git -C $Root push origin main
    if($LASTEXITCODE -eq 0){ break }
    if($i -eq 5){ throw "git push failed after 5 attempts" }
    Start-Sleep -Seconds (10 * $i)
}

Write-Host "[Publish] Done."
