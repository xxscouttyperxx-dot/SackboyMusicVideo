$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\RemoveVisibleReflectionStreaks-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_RemoveVisibleReflectionStreaks.blend") -Force
Copy-Item (Join-Path $PatchScripts "remove_visible_reflection_streaks_v1.py") (Join-Path $Scripts "remove_visible_reflection_streaks_v1.py") -Force

Write-Host "[RemoveVisibleReflectionStreaks] Cleaning old package root files..."
$Keep=@("Apply-RemoveVisibleReflectionStreaks.ps1","Validate-RemoveVisibleReflectionStreaks.ps1","Publish-CurrentReview.ps1","README-RemoveVisibleReflectionStreaks.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[RemoveVisibleReflectionStreaks] Removing visible floating reflection streak overlays..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "remove_visible_reflection_streaks_v1.py")
if($LASTEXITCODE -ne 0){throw "Remove visible reflection streaks failed."}

$Expected=@(
"renders\remove_visible_reflection_streaks_v1\01_StorefrontNoFloatingStreaks.png",
"renders\remove_visible_reflection_streaks_v1\02_ReflectionCardsOnlyCheck.png",
"renders\remove_visible_reflection_streaks_v1\03_CharacterNoStreakIntersections.png",
"renders\remove_visible_reflection_streaks_v1\RemoveVisibleReflectionStreaks_report.txt",
"renders\remove_visible_reflection_streaks_v1\RemoveVisibleReflectionStreaks_status.json",
"reports\remove_visible_reflection_streaks_v1\Remove_Visible_Reflection_Streaks_v1.md",
"reports\remove_visible_reflection_streaks_v1\remove_visible_reflection_streaks_v1.json",
"renders\current_review\01_StorefrontNoFloatingStreaks.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== REMOVE VISIBLE REFLECTION STREAKS PASS ==="
Write-Host "Visible FX_GlassStreak/FX_WindowGlow overlays were removed."
Write-Host "Reflection-only FX_ReflectCard objects and red/yellow/green traffic lights were preserved."
Write-Host "Car, asphalt, white parking strips, approved amber lights, sky/HDRI, character, and clothing were preserved."
Write-Host "Character deformation was not applied."
Write-Host "Backup: $BackupRoot"
