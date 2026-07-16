param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only Stage 12 v1.2 scripts, configs, folder READMEs, and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-MotionRetargetPrepV1_2.ps1",
    "Validate-MotionRetargetPrepV1_2.ps1",
    "Set-RigViewControlsOnlyV1_2.ps1",
    "Set-RigViewFullSkeletonV1_2.ps1",
    "Publish-MotionRetargetPrepReportsV1_2.ps1",
    "Optional-PushMotionRetargetPrepBlendOnlyV1_2.ps1",
    "README-MotionRetargetPrepV1_2.txt",
    "blender/scripts/preflight_motion_retarget_prep_v1_2.py",
    "blender/scripts/motion_retarget_prep_v1_2.py",
    "blender/scripts/rig_view_mode_v1_2.py",
    "configs/SackboyRetargetProfileV1.json",
    "motion/reference",
    "motion/extracted",
    "motion/retargeted",
    "reports/motion_retarget_prep_v1_2"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged Stage 12 v1.2 report changes."
}else{
    git commit -m "Add motion extraction and retarget preparation v1.2"
}
git push origin main
Write-Host "[ReportsOnly] Done."
