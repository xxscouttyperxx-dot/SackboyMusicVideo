$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CircularReflectionRefine-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CircularReflectionRefine.blend") -Force
Copy-Item (Join-Path $PatchScripts "circular_reflection_refine_v1.py") (Join-Path $Scripts "circular_reflection_refine_v1.py") -Force

Write-Host "[CircularReflectionRefine] Cleaning old package root files..."
$Keep=@("Apply-CircularReflectionRefine.ps1","Validate-CircularReflectionRefine.ps1","Publish-CurrentReview.ps1","README-CircularReflectionRefine.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[CircularReflectionRefine] Refining reflection cards into tighter circular sources..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "circular_reflection_refine_v1.py")
if($LASTEXITCODE -ne 0){throw "Circular reflection refine failed."}

$Expected=@(
"renders\circular_reflection_refine_v1\01_CircularReflectionClose.png",
"renders\circular_reflection_refine_v1\02_CircularReflectionOblique.png",
"renders\circular_reflection_refine_v1\03_ReflectionSourceLayout.png",
"renders\circular_reflection_refine_v1\04_CharacterReadyUnchanged.png",
"renders\circular_reflection_refine_v1\CircularReflectionRefine_report.txt",
"renders\circular_reflection_refine_v1\CircularReflectionRefine_status.json",
"reports\circular_reflection_refine_v1\Circular_Reflection_Refine_v1.md",
"reports\circular_reflection_refine_v1\circular_reflection_refine_v1.json",
"renders\current_review\01_CircularReflectionClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CIRCULAR REFLECTION REFINE PASS ==="
Write-Host "Existing successful Cycles reflection setup preserved and tightened up."
Write-Host "FX_ReflectCard objects were rebuilt as smaller circular reflection-only emissive sources."
Write-Host "Red / yellow / green traffic-light concept preserved; no white or blue added."
Write-Host "Glass materials remained reflection-friendly for Cycles."
Write-Host "No character deformation was applied in this pass."
Write-Host "Backup: $BackupRoot"
