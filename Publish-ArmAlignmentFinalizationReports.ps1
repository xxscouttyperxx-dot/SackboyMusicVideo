param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only final arm-alignment scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-ArmAlignmentFinalizationV2.ps1",
    "Validate-ArmAlignmentFinalizationV2.ps1",
    "Publish-ArmAlignmentFinalizationReports.ps1",
    "Optional-PushArmAlignmentFinalBlendOnly.ps1",
    "README-ArmAlignmentFinalizationV2.txt",
    "blender/scripts/arm_alignment_finalization_v2.py",
    "reports/arm_alignment_finalization_v2"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add final Sackboy arm alignment v2 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
