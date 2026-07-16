param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only F2-binding scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-F2BindWeightsV1.ps1",
    "Validate-F2BindWeightsV1.ps1",
    "Publish-F2BindWeightsReports.ps1",
    "Optional-PushF2BindWeightsBlendOnly.ps1",
    "README-F2BindWeightsV1.txt",
    "blender/scripts/f2_bind_weights_v1.py",
    "reports/f2_bind_weights_v1"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add F2-only binding and weights v1 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
