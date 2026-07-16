param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only dressed-rig/control v1.8 scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-DressedRigControlsV1_8.ps1",
    "Validate-DressedRigControlsV1_8.ps1",
    "Publish-DressedRigControlsReportsV1_8.ps1",
    "Optional-PushDressedRigControlsBlendOnlyV1_8.ps1",
    "README-DressedRigControlsV1_8.txt",
    "blender/scripts/preflight_dressed_rig_controls_v1_8.py",
    "blender/scripts/dressed_rig_controls_v1_8.py",
    "reports/dressed_rig_controls_v1_8"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add root-cause-fixed dressed rig controls v1.8 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
