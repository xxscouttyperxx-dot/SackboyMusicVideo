$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\GlassReflectionVisibility-v1B-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_GlassReflectionVisibility_v1B.blend") -Force
Copy-Item (Join-Path $PatchScripts "glass_reflection_visibility_v1B.py") (Join-Path $Scripts "glass_reflection_visibility_v1B.py") -Force

Write-Host "[GlassReflectionVisibility v1B] Cleaning old package root files..."
$Keep=@("Apply-GlassReflectionVisibility.ps1","Validate-GlassReflectionVisibility.ps1","Publish-CurrentReview.ps1","README-GlassReflectionVisibility.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[GlassReflectionVisibility v1B] Rebuilding storefront reflection system..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "glass_reflection_visibility_v1B.py")
if($LASTEXITCODE -ne 0){throw "Glass reflection visibility v1B failed."}

$Expected=@(
"renders\glass_reflection_visibility_v1B\01_GlassReflectionClose.png",
"renders\glass_reflection_visibility_v1B\02_GlassReflectionOblique.png",
"renders\glass_reflection_visibility_v1B\03_ReflectionFXSetup.png",
"renders\glass_reflection_visibility_v1B\04_CharacterReadyUnchanged.png",
"renders\glass_reflection_visibility_v1B\GlassReflectionVisibility_report.txt",
"renders\glass_reflection_visibility_v1B\GlassReflectionVisibility_status.json",
"reports\glass_reflection_visibility_v1B\Glass_Reflection_Visibility_v1B.md",
"reports\glass_reflection_visibility_v1B\glass_reflection_visibility_v1B.json",
"renders\current_review\01_GlassReflectionClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== GLASS REFLECTION VISIBILITY v1B PASS ==="
Write-Host "Red/yellow/green reflection system was rebuilt close to the storefront glass."
Write-Host "Camera-invisible reflection cards plus subtle on-glass streak overlays were created."
Write-Host "Glass/window materials were tuned for sharper reflection visibility."
Write-Host "Car, asphalt, white parking strips, sky/HDRI, approved amber lights, character, and clothing were preserved."
Write-Host "Character deformation was not applied yet."
Write-Host "Backup: $BackupRoot"
