$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieCameraCleanupShapeFix-"+(Get-Date -Format "yyyyMMdd-HHmmss"))
foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){if(-not(Test-Path $Item)){throw "Required item missing: $Item"}}
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieCameraCleanupShapeFix.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_camera_cleanup_shape_fix_v1.py") (Join-Path $Scripts "hoodie_camera_cleanup_shape_fix_v1.py") -Force
Write-Host "[HoodieCameraCleanupShapeFix] Cleaning old package root files..."
$Keep=@("Apply-HoodieCameraCleanupShapeFix.ps1","Validate-HoodieCameraCleanupShapeFix.ps1","Publish-CurrentReview.ps1","README-HoodieCameraCleanupShapeFix.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue | Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } | Remove-Item -Force}
Write-Host "[HoodieCameraCleanupShapeFix] Cleaning cameras, isolating wire render, and fixing hoodie shape..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_camera_cleanup_shape_fix_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie camera cleanup shape fix failed."}
$Expected=@(
"renders\hoodie_camera_cleanup_shape_fix_v1\01_HoodieMaterialShape.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\02_HoodieLeftSideGray.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\03_HoodieRightSideGray.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\04_HoodieIsolatedWireCheck.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\05_HoodieScenePreserved.png",
"renders\hoodie_camera_cleanup_shape_fix_v1\HoodieCameraCleanupShapeFix_report.txt",
"renders\hoodie_camera_cleanup_shape_fix_v1\HoodieCameraCleanupShapeFix_status.json",
"reports\hoodie_camera_cleanup_shape_fix_v1\Hoodie_Camera_Cleanup_Shape_Fix_v1.md",
"reports\hoodie_camera_cleanup_shape_fix_v1\hoodie_camera_cleanup_shape_fix_v1.json",
"renders\current_review\01_HoodieMaterialShape.png"
)
foreach($Rel in $Expected){if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}}
$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}
Write-Host ""
Write-Host "=== HOODIE CAMERA CLEANUP / SHAPE FIX PASS ==="
Write-Host "Old review camera duplicates were removed and a minimal camera set was recreated."
Write-Host "Wire render is now isolated to the hoodie so scene/camera/light wireframes do not look like hoodie spikes."
Write-Host "Shoulder collars were raised, lower hood sides pulled out/down, and rear hood protrusion feathered."
Write-Host "Vertex/face counts and dimensional deltas were written to the report."
Write-Host "F2 BODYFIT shape keys remain disabled; scene and reflections were preserved."
Write-Host "Backup: $BackupRoot"
