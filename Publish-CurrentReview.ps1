$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

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
$Keep=@(
    "Apply-CharacterWardrobePrep.ps1",
    "Validate-CharacterWardrobePrep.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-CharacterWardrobePrep.txt",
    "README_FIRST.txt",
    "Run-BuildAll.ps1",
    "Run-DiagnosticRenders.ps1"
)
$Patterns=@(
    "Apply-Step*.ps1",
    "Validate-Step*.ps1",
    "README-Step*.txt",
    "Apply-Production*.ps1",
    "Validate-Production*.ps1",
    "README-Production*.txt",
    "Apply-Project*.ps1",
    "Validate-Project*.ps1",
    "README-Project*.txt",
    "Apply-HeroCar*.ps1",
    "Validate-HeroCar*.ps1",
    "README-HeroCar*.txt",
    "Apply-LampSidewalkSkyCleanup.ps1",
    "Validate-LampSidewalkSkyCleanup.ps1",
    "README-LampSidewalkSkyCleanup.txt",
    "Apply-StorefrontParking*.ps1",
    "Validate-StorefrontParking*.ps1",
    "README-StorefrontParking*.txt",
    "Apply-AmbientCarGlassPolish.ps1",
    "Validate-AmbientCarGlassPolish.ps1",
    "README-AmbientCarGlassPolish.txt",
    "Apply-PublishFix.ps1",
    "README-PublishFix.txt"
)
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$Keep -notcontains $_.Name} |
        Remove-Item -Force
}

GitAddExistingOrDeleted @(
    ".gitignore",
    ".gitattributes",
    "blender\sackboy_scene.blend",
    "blender\sackboy_scene.blend1",
    "blender\scripts",
    "scene_manifest.json",
    "reports\project_workflow_audit",
    "renders\current_review",
    "Apply-CharacterWardrobePrep.ps1",
    "Validate-CharacterWardrobePrep.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-CharacterWardrobePrep.txt",
    "Apply-AmbientCarGlassPolish.ps1",
    "Validate-AmbientCarGlassPolish.ps1",
    "README-AmbientCarGlassPolish.txt"
)

if(Test-Path (Join-Path $Root "NightSkyHDRI003_1K")){
    git -C $Root add -A -- NightSkyHDRI003_1K
    if($LASTEXITCODE -ne 0){throw "git add failed HDRI"}
}
if(Test-Path (Join-Path $Root "blender\assets")){
    git -C $Root add -A -- blender\assets
    if($LASTEXITCODE -ne 0){throw "git add failed assets"}
}

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[Publish] Nothing to commit."
} else {
    git -C $Root commit -m "Add character wardrobe prep and current review"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}
git -C $Root push origin main
if($LASTEXITCODE -ne 0){throw "git push failed"}
Write-Host "[Publish] Done."
