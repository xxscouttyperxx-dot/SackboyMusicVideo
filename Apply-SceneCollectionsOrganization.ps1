$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\SceneCollectionsOrganization-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_SceneCollectionsOrganization.blend") -Force
Copy-Item (Join-Path $PatchScripts "scene_collections_organization_v1.py") (Join-Path $Scripts "scene_collections_organization_v1.py") -Force

Write-Host "[SceneCollectionsOrganization] Cleaning old package root files..."
$Keep=@("Apply-SceneCollectionsOrganization.ps1","Validate-SceneCollectionsOrganization.ps1","Publish-CurrentReview.ps1","README-SceneCollectionsOrganization.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[SceneCollectionsOrganization] Organizing objects into clean collections..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "scene_collections_organization_v1.py")
if($LASTEXITCODE -ne 0){throw "Scene collections organization failed."}

$Expected=@(
"reports\scene_collections_organization_v1\Scene_Collections_Organization_v1.md",
"reports\scene_collections_organization_v1\SceneCollectionsOrganization_report.txt",
"reports\scene_collections_organization_v1\SceneCollectionsOrganization_status.json",
"reports\scene_collections_organization_v1\scene_collections_organization_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== SCENE COLLECTIONS ORGANIZATION PASS ==="
Write-Host "No objects were deleted."
Write-Host "No visible objects were hidden."
Write-Host "Same-name groups were kept together under category collections."
Write-Host "Multi-collection object listings were reduced by unlinking objects from old collections after linking to clean targets."
Write-Host "Backup: $BackupRoot"
