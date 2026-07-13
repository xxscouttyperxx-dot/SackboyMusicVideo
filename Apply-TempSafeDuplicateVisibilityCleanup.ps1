$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\TempSafeDuplicateVisibilityCleanup-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_TempSafeDuplicateVisibilityCleanup.blend") -Force
Copy-Item (Join-Path $PatchScripts "temp_safe_duplicate_visibility_cleanup_v1.py") (Join-Path $Scripts "temp_safe_duplicate_visibility_cleanup_v1.py") -Force

Write-Host "[TempSafeDuplicateVisibilityCleanup] Cleaning old package root files..."
$Keep=@("Apply-TempSafeDuplicateVisibilityCleanup.ps1","Validate-TempSafeDuplicateVisibilityCleanup.ps1","Publish-CurrentReview.ps1","README-TempSafeDuplicateVisibilityCleanup.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[TempSafeDuplicateVisibilityCleanup] Applying conservative hidden-helper archive cleanup..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "temp_safe_duplicate_visibility_cleanup_v1.py")
if($LASTEXITCODE -ne 0){throw "Temp safe duplicate visibility cleanup failed."}

$Expected=@(
"reports\temp_safe_duplicate_visibility_cleanup_v1\Temp_Safe_Duplicate_Visibility_Cleanup_v1.md",
"reports\temp_safe_duplicate_visibility_cleanup_v1\TempSafeDuplicateVisibilityCleanup_report.txt",
"reports\temp_safe_duplicate_visibility_cleanup_v1\TempSafeDuplicateVisibilityCleanup_status.json",
"reports\temp_safe_duplicate_visibility_cleanup_v1\temp_safe_duplicate_visibility_cleanup_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== TEMP SAFE DUPLICATE VISIBILITY CLEANUP PASS ==="
Write-Host "No objects were deleted."
Write-Host "No currently visible objects were hidden."
Write-Host "Only safe hidden helper objects were render-disabled/select-locked and linked to an archive collection."
Write-Host "Backup: $BackupRoot"
