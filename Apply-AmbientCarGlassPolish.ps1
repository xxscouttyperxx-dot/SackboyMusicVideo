$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\AmbientCarGlassPolish-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_AmbientCarGlassPolish.blend") -Force
Copy-Item (Join-Path $PatchScripts "ambient_car_glass_polish_v1.py") (Join-Path $Scripts "ambient_car_glass_polish_v1.py") -Force

Write-Host "[AmbientCarGlassPolish] Cleaning old package root files..."
$Keep=@(
    "Apply-AmbientCarGlassPolish.ps1",
    "Validate-AmbientCarGlassPolish.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-AmbientCarGlassPolish.txt",
    "README_FIRST.txt",
    "Run-BuildAll.ps1",
    "Run-DiagnosticRenders.ps1"
)
$Patterns=@(
    "Apply-Step*.ps1",
    "Validate-Step*.ps1",
    "README-Step*.txt",
    "Apply-Production*.ps1",
    "Validate-Production*.ps1",
    "README-Production*.txt",
    "Apply-Project*.ps1",
    "Validate-Project*.ps1",
    "README-Project*.txt",
    "Apply-HeroCar*.ps1",
    "Validate-HeroCar*.ps1",
    "README-HeroCar*.txt",
    "Apply-LampSidewalkSkyCleanup.ps1",
    "Validate-LampSidewalkSkyCleanup.ps1",
    "README-LampSidewalkSkyCleanup.txt",
    "Apply-StorefrontParking*.ps1",
    "Validate-StorefrontParking*.ps1",
    "README-StorefrontParking*.txt",
    "Apply-PublishFix.ps1",
    "README-PublishFix.txt"
)
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$Keep -notcontains $_.Name} |
        Remove-Item -Force
}

Write-Host "[AmbientCarGlassPolish] Preserving current layout; polishing car amber read and storefront glass..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "ambient_car_glass_polish_v1.py")
if($LASTEXITCODE -ne 0){throw "Ambient car/glass polish failed."}

$Expected=@(
"renders\ambient_car_glass_polish_v1\01_CarAmberRead.png",
"renders\ambient_car_glass_polish_v1\02_WindowReflectionPolish.png",
"renders\ambient_car_glass_polish_v1\03_StableSceneMood.png",
"renders\ambient_car_glass_polish_v1\AmbientCarGlassPolish_status.json",
"renders\ambient_car_glass_polish_v1\AmbientCarGlassPolish_report.txt",
"renders\current_review\01_CarAmberRead.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== AMBIENT CAR / GLASS POLISH PASS ==="
Write-Host "Manual lamp/sidewalk/storefront placement preserved."
Write-Host "User-managed HDRI/world preserved; scripted sky backdrop removed."
Write-Host "Subtle amber helper lights added to make overhead amber read on the hero car."
Write-Host "Storefront glass made darker/glossier with night traffic reflection streaks."
Write-Host "Current review renders updated."
Write-Host "Backup: $BackupRoot"
