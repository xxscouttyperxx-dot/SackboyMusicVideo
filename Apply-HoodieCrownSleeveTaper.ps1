$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieCrownSleeveTaper-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieCrownSleeveTaper.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_crown_sleeve_taper_v1.py") (Join-Path $Scripts "hoodie_crown_sleeve_taper_v1.py") -Force

Write-Host "[HoodieCrownSleeveTaper] Cleaning old package root files..."
$Keep=@("Apply-HoodieCrownSleeveTaper.ps1","Validate-HoodieCrownSleeveTaper.ps1","Publish-CurrentReview.ps1","README-HoodieCrownSleeveTaper.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieCrownSleeveTaper] Expanding hood crown and tapering sleeves..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_crown_sleeve_taper_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie crown sleeve taper failed."}

$Expected=@(
"renders\hoodie_crown_sleeve_taper_v1\01_HoodCrownFront.png",
"renders\hoodie_crown_sleeve_taper_v1\02_HoodCrownProfile.png",
"renders\hoodie_crown_sleeve_taper_v1\03_SleeveTaperThreeQuarter.png",
"renders\hoodie_crown_sleeve_taper_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_crown_sleeve_taper_v1\HoodieCrownSleeveTaper_report.txt",
"renders\hoodie_crown_sleeve_taper_v1\HoodieCrownSleeveTaper_status.json",
"reports\hoodie_crown_sleeve_taper_v1\Hoodie_Crown_Sleeve_Taper_v1.md",
"reports\hoodie_crown_sleeve_taper_v1\hoodie_crown_sleeve_taper_v1.json",
"renders\current_review\01_HoodCrownFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE CROWN SLEEVE TAPER PASS ==="
Write-Host "Hoodie crown expanded in feathered sections for Sackboy's large head."
Write-Host "Sleeve outer/cuff regions were tapered to reduce large sticking-out sleeve mass."
Write-Host "F2 character BODYFIT shape keys remain disabled; character baseline is preserved."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
