param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only F2 deformation-test v1.2 scripts and reports."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-F2DeformationTestsV1_2.ps1",
    "Validate-F2DeformationTestsV1_2.ps1",
    "Publish-F2DeformationTestsReportsV1_2.ps1",
    "Optional-PushF2DeformationTestsBlendOnlyV1_2.ps1",
    "README-F2DeformationTestsV1_2.txt",
    "blender/scripts/f2_deformation_tests_v1_2.py",
    "reports/f2_deformation_tests_v1_2"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add corrected F2 deformation test poses v1.2 reports"
}
git push origin main
Write-Host "[ReportsOnly] Done."
