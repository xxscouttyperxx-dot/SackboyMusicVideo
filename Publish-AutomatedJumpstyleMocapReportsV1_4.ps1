param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging automated jumpstyle v1.4 scripts, compact tracking data, and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"
Unstage-IfTracked "motion/reference/dance_reference.mp4"
Unstage-IfTracked "motion/extracted/dance_reference_tracking_overlay_v1.mp4"
Unstage-IfTracked "tools/wheels"
Unstage-IfTracked "Tools/jumpstyle-mocap-env"

$paths=@(
    "Run-AutomatedJumpstyleMocapV1_4.ps1",
    "Validate-AutomatedJumpstyleMocapV1_3.ps1",
    "Publish-AutomatedJumpstyleMocapReportsV1_4.ps1",
    "Optional-PushAutomatedJumpstyleMocapBlendOnlyV1_3.ps1",
    "README-AutomatedJumpstyleMocapV1_4-Hotfix.txt",
    "tools/mocap/validate_pose_cache_v1.py",
    "blender/scripts/preflight_jumpstyle_retarget_v1_3.py",
    "blender/scripts/apply_jumpstyle_retarget_v1_3.py",
    "motion/reference/SourceVideoAnalysisV1.json",
    "motion/extracted/dance_reference_pose_processed_v1.json",
    "reports/jumpstyle_mocap_v1"
)
foreach($path in $paths){if(Test-Path $path){git add -- "$path"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"
Unstage-IfTracked "motion/reference/dance_reference.mp4"
Unstage-IfTracked "motion/extracted/dance_reference_tracking_overlay_v1.mp4"
Unstage-IfTracked "tools/wheels"
Unstage-IfTracked "Tools/jumpstyle-mocap-env"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged automated mocap report changes."
}else{
    git commit -m "Add automated jumpstyle retarget and diagnostics"
}
git push origin main
Write-Host "[ReportsOnly] Done."
