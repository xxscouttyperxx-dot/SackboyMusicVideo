$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"reports\scene_collections_organization_v1\Scene_Collections_Organization_v1.md",
"reports\scene_collections_organization_v1\SceneCollectionsOrganization_report.txt",
"reports\scene_collections_organization_v1\SceneCollectionsOrganization_status.json",
"reports\scene_collections_organization_v1\scene_collections_organization_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== SCENE COLLECTIONS ORGANIZATION VALIDATION PASS ==="
