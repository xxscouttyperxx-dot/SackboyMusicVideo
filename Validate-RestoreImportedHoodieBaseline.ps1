$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\current_review\01_RestoredHoodieFront.png",
"renders\current_review\02_RestoredHoodieLeftSideGray.png",
"renders\current_review\03_RestoredHoodieRightSideGray.png",
"renders\current_review\04_RestoredHoodieTopGray.png",
"renders\current_review\05_ScenePreserved.png",
"reports\restore_imported_hoodie_baseline_v1\RestoreImportedHoodieBaseline_report.txt",
"reports\restore_imported_hoodie_baseline_v1\RestoreImportedHoodieBaseline_status.json",
"reports\restore_imported_hoodie_baseline_v1\Restore_Imported_Hoodie_Baseline_v1.md",
"reports\restore_imported_hoodie_baseline_v1\restore_imported_hoodie_baseline_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
$BadFiles = Get-ChildItem (Join-Path $Root "renders\current_review") -File |
    Where-Object { $_.Extension -in @(".txt",".json",".md") }
if($BadFiles.Count -gt 0){
    throw "current_review contains text/json/md files; expected images only: $($BadFiles.Name -join ', ')"
}
Write-Host "=== RESTORE IMPORTED HOODIE BASELINE VALIDATION PASS ==="
