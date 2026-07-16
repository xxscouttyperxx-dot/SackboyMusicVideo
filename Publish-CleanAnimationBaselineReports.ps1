param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only clean-baseline scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-CleanAnimationBaselineV1.ps1",
    "Validate-CleanAnimationBaselineV1.ps1",
    "Publish-CleanAnimationBaselineReports.ps1",
    "Optional-PushCleanBaselineBlendOnly.ps1",
    "README-CleanAnimationBaselineV1.txt",
    "blender/scripts/clean_animation_baseline_v1.py",
    "reports/clean_animation_baseline_v1"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add clean animation baseline v1 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
