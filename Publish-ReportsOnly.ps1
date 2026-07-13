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

Write-Host "[PublishReportsOnly] Staging reports/renders/scripts only. Blend is intentionally NOT staged."
GitAddExistingOrDeleted @(
    "blender\scripts\diagnostic_cameras_mesh_export_v1.py",
    "reports\diagnostic_cameras_mesh_export_v1",
    "renders\current_review",
    "Apply-DiagnosticCamerasMeshExport.ps1",
    "Validate-DiagnosticCamerasMeshExport.ps1",
    "Publish-ReportsOnly.ps1",
    "Try-PushBlendOnly.ps1",
    "README-DiagnosticCamerasMeshExport.txt"
)

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[PublishReportsOnly] Nothing to commit."
} else {
    git -C $Root commit -m "Add diagnostic cameras mesh export reports"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}
git -C $Root push origin main
if($LASTEXITCODE -ne 0){throw "git push failed"}
Write-Host "[PublishReportsOnly] Done."
