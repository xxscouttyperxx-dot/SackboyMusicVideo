param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked=git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only character spatial/hierarchy audit reports and scripts."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths=@(
    "Apply-CharacterSpatialHierarchyAuditV1.ps1",
    "Validate-CharacterSpatialHierarchyAuditV1.ps1",
    "Publish-CharacterSpatialHierarchyAuditReports.ps1",
    "README-CharacterSpatialHierarchyAuditV1.txt",
    "blender/scripts/character_spatial_hierarchy_audit_v1.py",
    "reports/character_spatial_hierarchy_audit_v1"
)
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add character spatial hierarchy audit v1"
}
git push origin main
Write-Host "[ReportsOnly] Done."
