param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only lower-body alignment scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-LowerBodyFootAlignmentV1.ps1",
    "Validate-LowerBodyFootAlignmentV1.ps1",
    "Publish-LowerBodyFootAlignmentReports.ps1",
    "Optional-PushLowerBodyFootAlignmentBlendOnly.ps1",
    "README-LowerBodyFootAlignmentV1.txt",
    "blender/scripts/lower_body_foot_alignment_v1.py",
    "reports/lower_body_foot_alignment_v1"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add Sackboy lower-body foot alignment v1 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
