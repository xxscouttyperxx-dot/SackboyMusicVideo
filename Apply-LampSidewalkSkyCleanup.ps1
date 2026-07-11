$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\LampSidewalkSkyCleanup-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_LampSidewalkSkyCleanup.blend") -Force

Copy-Item (Join-Path $PatchScripts "lamp_sidewalk_sky_cleanup.py") (Join-Path $Scripts "lamp_sidewalk_sky_cleanup.py") -Force

Write-Host "[LampSidewalkSkyCleanup] Cleaning old package root files..."
$Keep=@(
    "Apply-LampSidewalkSkyCleanup.ps1",
    "Validate-LampSidewalkSkyCleanup.ps1",
    "Publish-CurrentReview.ps1",
    "Clean-PackageRoot.ps1",
    "README-LampSidewalkSkyCleanup.txt",
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
    "Apply-HeroCarHDRIIntegration.ps1",
    "Validate-HeroCarHDRIIntegration.ps1",
    "README-HeroCarHDRIIntegration.txt"
)
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$Keep -notcontains $_.Name} |
        Remove-Item -Force
}

Write-Host "[LampSidewalkSkyCleanup] Moving lamp posts, widening sidewalk, removing duplicate sky objects..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "lamp_sidewalk_sky_cleanup.py")
if($LASTEXITCODE -ne 0){throw "Lamp/sidewalk/sky cleanup failed."}

$Expected=@(
"renders\lamp_sidewalk_sky_cleanup\01_LampSidewalk_Hero.png",
"renders\lamp_sidewalk_sky_cleanup\02_LampVisibility.png",
"renders\lamp_sidewalk_sky_cleanup\03_HighLayout.png",
"renders\lamp_sidewalk_sky_cleanup\LampSidewalkSkyCleanup_status.json",
"renders\lamp_sidewalk_sky_cleanup\LampSidewalkSkyCleanup_report.txt",
"renders\current_review\01_LampSidewalk_Hero.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== LAMP / SIDEWALK / SKY CLEANUP PASS ==="
Write-Host "Old duplicate moon/cloud/star objects removed."
Write-Host "Lamp posts and fixtures rebuilt where the overhead lights are."
Write-Host "Sidewalk widened."
Write-Host "Parking lines rebuilt as flatter double-thick painted strips."
Write-Host "Current review renders updated."
Write-Host "Old package files cleaned from root."
Write-Host "Backup: $BackupRoot"
