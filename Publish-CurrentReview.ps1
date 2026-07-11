$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function GitAddExistingOrDeleted {
    param(
        [string[]]$Paths
    )

    foreach($Rel in $Paths){
        $Full = Join-Path $Root $Rel

        if(Test-Path $Full){
            git -C $Root add -A -- $Rel
            if($LASTEXITCODE -ne 0){ throw "git add failed for existing path: $Rel" }
        } else {
            # Stage deletion only if Git already knows about this path.
            $Tracked = git -C $Root ls-files -- $Rel
            if(-not [string]::IsNullOrWhiteSpace($Tracked)){
                git -C $Root add -A -- $Rel
                if($LASTEXITCODE -ne 0){ throw "git add failed for deleted tracked path: $Rel" }
            }
        }
    }
}

Write-Host "[PublishFix] Cleaning stale package files from project root..."
$Keep = @(
    "Apply-LampSidewalkSkyCleanup.ps1",
    "Validate-LampSidewalkSkyCleanup.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-LampSidewalkSkyCleanup.txt",
    "README_FIRST.txt",
    "Run-BuildAll.ps1",
    "Run-DiagnosticRenders.ps1"
)

$Patterns = @(
    "Apply-Step*.ps1",
    "Validate-Step*.ps1",
    "README-Step*.txt",
    "Apply-Production*.ps1",
    "Validate-Production*.ps1",
    "README-Production*.txt",
    "Apply-Project*.ps1",
    "Validate-Project*.ps1",
    "README-Project*.txt",
    "Apply-HeroCarHDRIIntegration.ps1",
    "Validate-HeroCarHDRIIntegration.ps1",
    "README-HeroCarHDRIIntegration.txt"
)

foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { $Keep -notcontains $_.Name } |
        Remove-Item -Force
}

Write-Host "[PublishFix] Staging scene, current review, scripts, reports, and root cleanup..."

GitAddExistingOrDeleted @(
    ".gitignore",
    ".gitattributes",
    "blender\sackboy_scene.blend",
    "blender\sackboy_scene.blend1",
    "blender\scripts",
    "scene_manifest.json",
    "reports\project_workflow_audit",
    "renders\current_review",
    "Apply-LampSidewalkSkyCleanup.ps1",
    "Validate-LampSidewalkSkyCleanup.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-LampSidewalkSkyCleanup.txt",
    "Apply-ProjectCleanupReset.ps1",
    "README-ProjectCleanupReset.txt",
    "Validate-ProjectCleanupReset.ps1",
    "Apply-HeroCarHDRIIntegration.ps1",
    "Validate-HeroCarHDRIIntegration.ps1",
    "README-HeroCarHDRIIntegration.txt",
    "Apply-ProjectWorkflowAudit.ps1",
    "Validate-ProjectWorkflowAudit.ps1",
    "README-ProjectWorkflowAudit.txt"
)

if(Test-Path (Join-Path $Root "NightSkyHDRI003_1K")){
    git -C $Root add -A -- NightSkyHDRI003_1K
    if($LASTEXITCODE -ne 0){ throw "git add failed for NightSkyHDRI003_1K" }
}

if(Test-Path (Join-Path $Root "blender\assets")){
    git -C $Root add -A -- blender\assets
    if($LASTEXITCODE -ne 0){ throw "git add failed for blender/assets" }
}

Write-Host "[PublishFix] Git status after staging:"
git -C $Root status --short

$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[PublishFix] Nothing to commit."
} else {
    git -C $Root commit -m "Update lamp sidewalk sky cleanup and current review"
    if($LASTEXITCODE -ne 0){ throw "git commit failed" }
}

git -C $Root push origin main
if($LASTEXITCODE -ne 0){ throw "git push failed" }

Write-Host "[PublishFix] Done."
