$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CharacterSilhouetteRefine-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CharacterSilhouetteRefine.blend") -Force
Copy-Item (Join-Path $PatchScripts "character_silhouette_refine_v1.py") (Join-Path $Scripts "character_silhouette_refine_v1.py") -Force

Write-Host "[CharacterSilhouetteRefine] Cleaning old package root files..."
$Keep=@("Apply-CharacterSilhouetteRefine.ps1","Validate-CharacterSilhouetteRefine.ps1","Publish-CurrentReview.ps1","README-CharacterSilhouetteRefine.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[CharacterSilhouetteRefine] Refining silhouette: thinner legs, flatter gut/face, smaller hands..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "character_silhouette_refine_v1.py")
if($LASTEXITCODE -ne 0){throw "Character silhouette refine failed."}

$Expected=@(
"renders\character_silhouette_refine_v1\01_SilhouetteFront.png",
"renders\character_silhouette_refine_v1\02_ProfileGutLegHand.png",
"renders\character_silhouette_refine_v1\03_FaceHandCheck.png",
"renders\character_silhouette_refine_v1\04_StorefrontReflectionCamera.png",
"renders\character_silhouette_refine_v1\CharacterSilhouetteRefine_report.txt",
"renders\character_silhouette_refine_v1\CharacterSilhouetteRefine_status.json",
"reports\character_silhouette_refine_v1\Character_Silhouette_Refine_v1.md",
"reports\character_silhouette_refine_v1\character_silhouette_refine_v1.json",
"renders\current_review\01_SilhouetteFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CHARACTER SILHOUETTE REFINE PASS ==="
Write-Host "F2 received a stronger active non-destructive silhouette/face/hand fit shape key."
Write-Host "Legs were thinned, torso/gut was flattened more, face/snout area was reduced, and hands were reduced."
Write-Host "Clothing deformation was not applied yet."
Write-Host "Persistent review cameras were refreshed, including CAM_REVIEW_StorefrontReflection."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
