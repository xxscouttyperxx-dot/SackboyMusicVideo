$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\SceneCleanupFlatAsphalt-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_SceneCleanupFlatAsphalt_v1B.blend") -Force
Copy-Item (Join-Path $PatchScripts "scene_cleanup_flat_asphalt_v1B.py") (Join-Path $Scripts "scene_cleanup_flat_asphalt_v1B.py") -Force

Write-Host "[SceneCleanupFlatAsphalt v1B] Cleaning old package root files..."
$Keep=@("Apply-SceneCleanupFlatAsphalt.ps1","Validate-SceneCleanupFlatAsphalt.ps1","Publish-CurrentReview.ps1","README-SceneCleanupFlatAsphalt.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[SceneCleanupFlatAsphalt v1B] Flattening asphalt, snapping paint strips, scanning lights, and cleaning temp cameras..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "scene_cleanup_flat_asphalt_v1B.py")
if($LASTEXITCODE -ne 0){throw "Scene cleanup / flat asphalt v1B failed."}

$Expected=@(
"renders\scene_cleanup_flat_asphalt_v1B\01_FlatAsphaltPaintCheck.png",
"renders\scene_cleanup_flat_asphalt_v1B\02_DecimatePreviewCheck.png",
"renders\scene_cleanup_flat_asphalt_v1B\SceneCleanupFlatAsphalt_report.txt",
"renders\scene_cleanup_flat_asphalt_v1B\SceneCleanupFlatAsphalt_status.json",
"reports\scene_cleanup_flat_asphalt_v1B\Scene_Cleanup_Flat_Asphalt_v1B.md",
"reports\scene_cleanup_flat_asphalt_v1B\scene_cleanup_flat_asphalt_v1B.json",
"renders\current_review\01_FlatAsphaltPaintCheck.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== SCENE CLEANUP / FLAT ASPHALT v1B PASS ==="
Write-Host "Current manually tuned lights were scanned and preserved."
Write-Host "Active asphalt was flattened; bumpy imported asphalt was hidden after material transfer where available."
Write-Host "Parking paint strips were repositioned directly onto the flat asphalt surface."
Write-Host "Temporary package review cameras were cleaned."
Write-Host "Decimate preview modifiers were verified, not changed."
Write-Host "No new reflection lights were added in this pass."
Write-Host "Backup: $BackupRoot"
