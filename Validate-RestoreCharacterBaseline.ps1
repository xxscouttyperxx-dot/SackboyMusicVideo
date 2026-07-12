$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\restore_character_baseline_v1\01_RestoredCharacterFront.png",
"renders\restore_character_baseline_v1\02_RestoredCharacterProfile.png",
"renders\restore_character_baseline_v1\03_RestoredFaceHands.png",
"renders\restore_character_baseline_v1\04_StorefrontReflectionPreserved.png",
"renders\restore_character_baseline_v1\RestoreCharacterBaseline_report.txt",
"renders\restore_character_baseline_v1\RestoreCharacterBaseline_status.json",
"reports\restore_character_baseline_v1\Restore_Character_Baseline_v1.md",
"reports\restore_character_baseline_v1\restore_character_baseline_v1.json",
"renders\current_review\01_RestoredCharacterFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== RESTORE CHARACTER BASELINE VALIDATION PASS ==="
