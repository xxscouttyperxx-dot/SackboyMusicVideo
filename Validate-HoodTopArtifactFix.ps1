$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
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
Write-Host "=== HOOD TOP ARTIFACT FIX VALIDATION PASS ==="
