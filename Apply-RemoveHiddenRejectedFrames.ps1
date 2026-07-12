$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\RemoveHiddenRejectedFrames-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_RemoveHiddenRejectedFrames.blend") -Force
Copy-Item (Join-Path $PatchScripts "remove_hidden_rejected_frames_v1.py") (Join-Path $Scripts "remove_hidden_rejected_frames_v1.py") -Force

Write-Host "[RemoveHiddenRejectedFrames] Cleaning old package root files..."
$Keep=@("Apply-RemoveHiddenRejectedFrames.ps1","Validate-RemoveHiddenRejectedFrames.ps1","Publish-CurrentReview.ps1","README-RemoveHiddenRejectedFrames.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

Write-Host "[RemoveHiddenRejectedFrames] Removing hidden rejected ENV_Glass/ENV_Frame leftovers..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "remove_hidden_rejected_frames_v1.py")
if($LASTEXITCODE -ne 0){throw "Remove hidden rejected frames failed."}

$Expected=@(
"renders\remove_hidden_rejected_frames_v1\01_CleanupOverview.png",
"renders\remove_hidden_rejected_frames_v1\02_ReflectionSetupIntentionalCards.png",
"renders\remove_hidden_rejected_frames_v1\03_CharacterReadyUnchanged.png",
"renders\remove_hidden_rejected_frames_v1\RemoveHiddenRejectedFrames_report.txt",
"renders\remove_hidden_rejected_frames_v1\RemoveHiddenRejectedFrames_status.json",
"reports\remove_hidden_rejected_frames_v1\Remove_Hidden_Rejected_Frames_v1.md",
"reports\remove_hidden_rejected_frames_v1\remove_hidden_rejected_frames_v1.json",
"renders\current_review\01_CleanupOverview.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== REMOVE HIDDEN REJECTED FRAMES PASS ==="
Write-Host "Hidden rejected ENV_Glass/ENV_Frame leftovers were removed from PARKING_PAINT_ORIGINALS_HIDDEN."
Write-Host "White parking paint strips were preserved."
Write-Host "FX_ReflectCard objects remain intentionally as reflection-only cards."
Write-Host "Character deformation was not applied yet."
Write-Host "Backup: $BackupRoot"
