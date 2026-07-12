$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

git -C $Root config http.postBuffer 1048576000
git -C $Root config http.version HTTP/1.1
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

Write-Host "[Publish] Cleaning stale package files..."
$Keep=@("Apply-HoodieDomeSideDepressionFix_v1B.ps1","Validate-HoodieDomeSideDepressionFix_v1B.ps1","Publish-CurrentReview.ps1","README-HoodieDomeSideDepressionFix_v1B.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

GitAddExistingOrDeleted @(
    ".gitignore",
    ".gitattributes",
    "blender\sackboy_scene.blend",
    "blender\scripts",
    "scene_manifest.json",
    "reports\project_workflow_audit",
    "reports\hoodie_dome_side_depression_fix_v1B",
    "reports\hoodie_camera_count_side_bowl_fix_v1",
    "renders\current_review",
    "Apply-HoodieDomeSideDepressionFix_v1B.ps1",
    "Validate-HoodieDomeSideDepressionFix_v1B.ps1",
    "Publish-CurrentReview.ps1",
    "README-HoodieDomeSideDepressionFix_v1B.txt",
    "Apply-HoodieDomeSideDepressionFix.ps1",
    "Validate-HoodieDomeSideDepressionFix.ps1",
    "README-HoodieDomeSideDepressionFix.txt"
)

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[Publish] Nothing to commit."
} else {
    git -C $Root commit -m "Fix hoodie side depressions into dome shape"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}

git -C $Root lfs push origin main
if($LASTEXITCODE -ne 0){
    Write-Host "[Publish] git lfs push failed once; retrying..."
    Start-Sleep -Seconds 5
    git -C $Root lfs push origin main
}
git -C $Root push origin main
if($LASTEXITCODE -ne 0){throw "git push failed"}
Write-Host "[Publish] Done."
