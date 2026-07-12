$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
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
Write-Host "=== REMOVE HIDDEN REJECTED FRAMES VALIDATION PASS ==="
