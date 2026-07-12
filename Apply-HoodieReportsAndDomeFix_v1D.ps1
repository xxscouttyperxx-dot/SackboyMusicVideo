$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieReportsAndDomeFix_v1D-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieReportsAndDomeFix_v1D.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_reports_and_dome_fix_v1D.py") (Join-Path $Scripts "hoodie_reports_and_dome_fix_v1D.py") -Force

Write-Host "[HoodieReportsAndDomeFix_v1D] Cleaning old package root files..."
$Keep=@("Apply-HoodieReportsAndDomeFix_v1D.ps1","Validate-HoodieReportsAndDomeFix_v1D.ps1","Publish-CurrentReview.ps1","README-HoodieReportsAndDomeFix_v1D.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieReportsAndDomeFix_v1D] Migrating reports and applying front-view/dome correction..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_reports_and_dome_fix_v1D.py")
if($LASTEXITCODE -ne 0){throw "Hoodie reports and dome fix v1D failed."}

$Expected=@(
"renders\current_review\01_HoodFrontLowAngleMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"reports\hoodie_reports_and_dome_fix_v1D\HoodieReportsAndDomeFix_v1D_report.txt",
"reports\hoodie_reports_and_dome_fix_v1D\HoodieReportsAndDomeFix_v1D_status.json",
"reports\hoodie_reports_and_dome_fix_v1D\Hoodie_Reports_And_Dome_Fix_v1D.md",
"reports\hoodie_reports_and_dome_fix_v1D\hoodie_reports_and_dome_fix_v1D.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE REPORTS AND DOME FIX v1D PASS ==="
Write-Host "Project changes text/json files were moved under reports folders."
Write-Host "Front hood camera was lowered and aimed upward."
Write-Host "Remaining side depressions/droop received a directional correction."
Write-Host "Current_review was cleaned and contains only current images."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
