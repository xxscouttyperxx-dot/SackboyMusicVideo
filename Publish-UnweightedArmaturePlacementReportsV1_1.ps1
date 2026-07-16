param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only armature-placement scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-UnweightedArmaturePlacementV1_1.ps1",
    "Validate-UnweightedArmaturePlacementV1_1.ps1",
    "Publish-UnweightedArmaturePlacementReportsV1_1.ps1",
    "Optional-PushUnweightedArmatureBlendOnlyV1_1.ps1",
    "README-UnweightedArmaturePlacementV1_1.txt",
    "blender/scripts/unweighted_armature_placement_v1.py",
    "reports/unweighted_armature_placement_v1"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add unweighted Sackboy armature placement v1.1 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
