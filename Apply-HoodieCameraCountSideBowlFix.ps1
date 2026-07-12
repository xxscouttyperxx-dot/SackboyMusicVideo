$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieCameraCountSideBowlFix-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieCameraCountSideBowlFix.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_camera_count_side_bowl_fix_v1.py") (Join-Path $Scripts "hoodie_camera_count_side_bowl_fix_v1.py") -Force

Write-Host "[HoodieCameraCountSideBowlFix] Cleaning old package root files..."
$Keep=@("Apply-HoodieCameraCountSideBowlFix.ps1","Validate-HoodieCameraCountSideBowlFix.ps1","Publish-CurrentReview.ps1","README-HoodieCameraCountSideBowlFix.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieCameraCountSideBowlFix] Applying camera inventory cleanup and side/back bowl fix..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_camera_count_side_bowl_fix_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie camera count side bowl fix failed."}

$Expected=@(
"renders\current_review\01_HoodFrontMaterial.png",
"renders\current_review\02_HoodLeftSideGray.png",
"renders\current_review\03_HoodRightSideGray.png",
"renders\current_review\04_HoodTopGray.png",
"renders\current_review\05_HoodIsolatedWireCheck.png",
"renders\current_review\06_ScenePreserved.png",
"renders\Project changes\HoodieCameraCountSideBowlFix_report.txt",
"renders\Project changes\HoodieCameraCountSideBowlFix_status.json",
"reports\hoodie_camera_count_side_bowl_fix_v1\Hoodie_Camera_Count_Side_Bowl_Fix_v1.md",
"reports\hoodie_camera_count_side_bowl_fix_v1\hoodie_camera_count_side_bowl_fix_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE CAMERA COUNT / SIDE BOWL FIX PASS ==="
Write-Host "Camera inventory reset to 12 total cameras: 9 visible + 3 hidden animation cameras."
Write-Host "Project change text/json files now go to renders\Project changes."
Write-Host "Current review was cleaned and now contains only current images."
Write-Host "Lower hood sides were pulled out/down, shoulder collars raised, and rear hood droop/protrusion rounded."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
