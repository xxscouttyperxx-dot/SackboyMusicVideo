$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\HoodTopArtifactFix-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_HoodTopArtifactFix.blend") -Force
Copy-Item (Join-Path $PatchScripts "hood_top_artifact_fix_v1.py") (Join-Path $Scripts "hood_top_artifact_fix_v1.py") -Force

Write-Host "[HoodTopArtifactFix] Cleaning old package root files..."
$Keep=@("Apply-HoodTopArtifactFix.ps1","Validate-HoodTopArtifactFix.ps1","Publish-CurrentReview.ps1","README-HoodTopArtifactFix.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[HoodTopArtifactFix] Running focused hood-top artifact correction..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "hood_top_artifact_fix_v1.py")
if($LASTEXITCODE -ne 0){throw "Hood top artifact fix failed."}

$Expected=@(
"renders\hood_top_artifact_fix_v1\01_HoodArtifactClose.png",
"renders\hood_top_artifact_fix_v1\02_HoodTopOverhead.png",
"renders\hood_top_artifact_fix_v1\03_HoodRimProfileClose.png",
"renders\hood_top_artifact_fix_v1\04_CharacterScenePreserved.png",
"renders\hood_top_artifact_fix_v1\HoodTopArtifactFix_report.txt",
"renders\hood_top_artifact_fix_v1\HoodTopArtifactFix_status.json",
"reports\hood_top_artifact_fix_v1\Hood_Top_Artifact_Fix_v1.md",
"reports\hood_top_artifact_fix_v1\hood_top_artifact_fix_v1.json",
"renders\current_review\01_HoodArtifactClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== HOOD TOP ARTIFACT FIX PASS ==="
Write-Host "Focused correction applied only to hood-top/rim clearance."
Write-Host "Hood top was lifted over F2 head using head top and head footprint clearance."
Write-Host "Three cameras focus on the hood artifact; one camera checks scene preservation."
Write-Host "F2 character BODYFIT shape keys remain disabled; character baseline is preserved."
Write-Host "Reflection setup, traffic lights, car, asphalt, sky/HDRI, and approved lights were preserved."
Write-Host "Backup: $BackupRoot"
