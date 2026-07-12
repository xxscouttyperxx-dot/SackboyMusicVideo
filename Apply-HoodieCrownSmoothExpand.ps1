$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieCrownSmoothExpand-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieCrownSmoothExpand.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_crown_smooth_expand_v1.py") (Join-Path $Scripts "hoodie_crown_smooth_expand_v1.py") -Force

Write-Host "[HoodieCrownSmoothExpand] Cleaning old package root files..."
$Keep=@("Apply-HoodieCrownSmoothExpand.ps1","Validate-HoodieCrownSmoothExpand.ps1","Publish-CurrentReview.ps1","README-HoodieCrownSmoothExpand.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieCrownSmoothExpand] Smoothing hood top, expanding crown further, and fixing sleeve elbow dips..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_crown_smooth_expand_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie crown smooth expand failed."}

$Expected=@(
"renders\hoodie_crown_smooth_expand_v1\01_HoodTopFront.png",
"renders\hoodie_crown_smooth_expand_v1\02_HoodTopProfile.png",
"renders\hoodie_crown_smooth_expand_v1\03_SleeveElbowCheck.png",
"renders\hoodie_crown_smooth_expand_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_crown_smooth_expand_v1\HoodieCrownSmoothExpand_report.txt",
"renders\hoodie_crown_smooth_expand_v1\HoodieCrownSmoothExpand_status.json",
"reports\hoodie_crown_smooth_expand_v1\Hoodie_Crown_Smooth_Expand_v1.md",
"reports\hoodie_crown_smooth_expand_v1\hoodie_crown_smooth_expand_v1.json",
"renders\current_review\01_HoodTopFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE CROWN SMOOTH EXPAND PASS ==="
Write-Host "Hood crown was expanded further and the top-cap dip artifact was smoothed."
Write-Host "Sleeve elbow valley was lifted/softened to reduce the camel-hump look."
Write-Host "F2 character BODYFIT shape keys remain disabled; character baseline is preserved."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
