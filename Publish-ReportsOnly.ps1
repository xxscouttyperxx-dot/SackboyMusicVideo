$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

git -C $Root checkout -- "blender/sackboy_scene.blend" 2>$null
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

Write-Host "[PublishReportsOnly] Staging v1B reports/renders/scripts only. Blend is intentionally NOT staged."
GitAddExistingOrDeleted @(
    "blender\scripts\body_target_seam_audit_fix_v1B.py",
    "reports\body_target_seam_audit_fix_v1B",
    "renders\current_review",
    "Apply-BodyTargetSeamAuditFix.ps1",
    "Validate-BodyTargetSeamAuditFix.ps1",
    "Publish-ReportsOnly.ps1",
    "Try-PushBlendOnly.ps1",
    "README-BodyTargetSeamAuditFix.txt"
)

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[PublishReportsOnly] Nothing to commit."
} else {
    git -C $Root commit -m "Fix body target seam audit exports"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}
git -C $Root push origin main
if($LASTEXITCODE -ne 0){throw "git push failed"}
Write-Host "[PublishReportsOnly] Done."
