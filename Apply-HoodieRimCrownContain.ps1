$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodieRimCrownContain-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodieRimCrownContain.blend") -Force
Copy-Item (Join-Path $PatchScripts "hoodie_rim_crown_contain_v1.py") (Join-Path $Scripts "hoodie_rim_crown_contain_v1.py") -Force

Write-Host "[HoodieRimCrownContain] Cleaning old package root files..."
$Keep=@("Apply-HoodieRimCrownContain.ps1","Validate-HoodieRimCrownContain.ps1","Publish-CurrentReview.ps1","README-HoodieRimCrownContain.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodieRimCrownContain] Stretching hood rim and lifting crown over head..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hoodie_rim_crown_contain_v1.py")
if($LASTEXITCODE -ne 0){throw "Hoodie rim crown contain failed."}

$Expected=@(
"renders\hoodie_rim_crown_contain_v1\01_HoodRimFront.png",
"renders\hoodie_rim_crown_contain_v1\02_HoodRimProfile.png",
"renders\hoodie_rim_crown_contain_v1\03_HoodTopArtifactCheck.png",
"renders\hoodie_rim_crown_contain_v1\04_StorefrontReflectionPreserved.png",
"renders\hoodie_rim_crown_contain_v1\HoodieRimCrownContain_report.txt",
"renders\hoodie_rim_crown_contain_v1\HoodieRimCrownContain_status.json",
"reports\hoodie_rim_crown_contain_v1\Hoodie_Rim_Crown_Contain_v1.md",
"reports\hoodie_rim_crown_contain_v1\hoodie_rim_crown_contain_v1.json",
"renders\current_review\01_HoodRimFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOODIE RIM CROWN CONTAIN PASS ==="
Write-Host "Hood rim was stretched vertically/proportionally."
Write-Host "Crown cap was lifted using F2 head-top clearance to reduce top show-through."
Write-Host "F2 character BODYFIT shape keys remain disabled; character baseline is preserved."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
