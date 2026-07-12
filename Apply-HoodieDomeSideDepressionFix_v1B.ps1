$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieDomeSideDepressionFix_v1B-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieDomeSideDepressionFix_v1B.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_dome_side_depression_fix_v1B.py") (Join-Path $Scripts "hoodie_dome_side_depression_fix_v1B.py") -Force

Write-Host "[HoodieDomeSideDepressionFix_v1B] Cleaning old package root files..."
$Keep=@("Apply-HoodieDomeSideDepressionFix_v1B.ps1","Validate-HoodieDomeSideDepressionFix_v1B.ps1","Publish-CurrentReview.ps1","README-HoodieDomeSideDepressionFix_v1B.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieDomeSideDepressionFix_v1B] Applying side depression / half-dome hood fix..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_dome_side_depression_fix_v1B.py")
if($LASTEXITCODE -ne 0){throw "Hoodie dome side depression fix v1B failed."}

$Expected=@(
"renders\current_review\01_HoodFrontMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"reports\hoodie_dome_side_depression_fix_v1B\HoodieDomeSideDepressionFix_v1B_report.txt",
"reports\hoodie_dome_side_depression_fix_v1B\HoodieDomeSideDepressionFix_v1B_status.json",
"reports\hoodie_dome_side_depression_fix_v1B\Hoodie_Dome_Side_Depression_Fix_v1B.md",
"reports\hoodie_dome_side_depression_fix_v1B\hoodie_dome_side_depression_fix_v1B.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE DOME SIDE DEPRESSION FIX v1B PASS ==="
Write-Host "Side depressions were rounded/feathered into the hood shell."
Write-Host "Back droop/protrusion was rounded into the side-profile silhouette."
Write-Host "Front rim/opening was preserved as the intentional break in the dome."
Write-Host "Current_review was cleaned and contains only current images."
Write-Host "Text/json outputs were written to reports\hoodie_dome_side_depression_fix_v1B."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
