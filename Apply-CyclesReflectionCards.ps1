$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CyclesReflectionCards-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CyclesReflectionCards.blend") -Force
Copy-Item (Join-Path $PatchScripts "cycles_reflection_cards_v1.py") (Join-Path $Scripts "cycles_reflection_cards_v1.py") -Force

Write-Host "[CyclesReflectionCards] Cleaning old package root files..."
$Keep=@("Apply-CyclesReflectionCards.ps1","Validate-CyclesReflectionCards.ps1","Publish-CurrentReview.ps1","README-CyclesReflectionCards.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[CyclesReflectionCards] Building clean Cycles reflection-card setup..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "cycles_reflection_cards_v1.py")
if($LASTEXITCODE -ne 0){throw "Cycles reflection cards failed."}

$Expected=@(
"renders\cycles_reflection_cards_v1\01_CyclesGlassReflectionClose.png",
"renders\cycles_reflection_cards_v1\02_CyclesGlassReflectionOblique.png",
"renders\cycles_reflection_cards_v1\03_ReflectionCardsNotCameraVisible.png",
"renders\cycles_reflection_cards_v1\04_CharacterReadyUnchanged.png",
"renders\cycles_reflection_cards_v1\CyclesReflectionCards_report.txt",
"renders\cycles_reflection_cards_v1\CyclesReflectionCards_status.json",
"reports\cycles_reflection_cards_v1\Cycles_Reflection_Cards_v1.md",
"reports\cycles_reflection_cards_v1\cycles_reflection_cards_v1.json",
"renders\current_review\01_CyclesGlassReflectionClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CYCLES REFLECTION CARDS PASS ==="
Write-Host "No visible streak overlays were created."
Write-Host "FX_ReflectCard objects were rebuilt as camera-invisible / glossy-visible Cycles reflection sources."
Write-Host "Glass/window materials were tuned for sharper reflections."
Write-Host "Scene render engine was set to Cycles for reflection-proof renders."
Write-Host "Car, asphalt, white parking strips, approved amber lights, sky/HDRI, character, and clothing were preserved."
Write-Host "Backup: $BackupRoot"
