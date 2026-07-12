$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieBowlRimRefine-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieBowlRimRefine.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_bowl_rim_refine_v1.py") (Join-Path $Scripts "hoodie_bowl_rim_refine_v1.py") -Force

Write-Host "[HoodieBowlRimRefine] Cleaning old package root files..."
$Keep=@("Apply-HoodieBowlRimRefine.ps1","Validate-HoodieBowlRimRefine.ps1","Publish-CurrentReview.ps1","README-HoodieBowlRimRefine.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieBowlRimRefine] Refining hood bowl/rim and rendering Workbench evidence..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_bowl_rim_refine_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie bowl rim refine failed."}

$Expected=@(
"renders\hoodie_bowl_rim_refine_v1\01_HoodieMaterialPreviewShape.png",
"renders\hoodie_bowl_rim_refine_v1\02_HoodieSolidGrayShape.png",
"renders\hoodie_bowl_rim_refine_v1\03_HoodieWireEdgeShape.png",
"renders\hoodie_bowl_rim_refine_v1\04_HoodieScenePreserved.png",
"renders\hoodie_bowl_rim_refine_v1\HoodieBowlRimRefine_report.txt",
"renders\hoodie_bowl_rim_refine_v1\HoodieBowlRimRefine_status.json",
"reports\hoodie_bowl_rim_refine_v1\Hoodie_Bowl_Rim_Refine_v1.md",
"reports\hoodie_bowl_rim_refine_v1\hoodie_bowl_rim_refine_v1.json",
"renders\current_review\01_HoodieMaterialPreviewShape.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE BOWL RIM REFINE PASS ==="
Write-Host "Hood ridge was lifted/feathered, rim was vertically widened, and lower sides were opened for a more concave bowl."
Write-Host "Review renders are 960x540 Workbench/material/solid/wire evidence views."
Write-Host "Vertex/face counts and dimensional deltas were written to the report."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
