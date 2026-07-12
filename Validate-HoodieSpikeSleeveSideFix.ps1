$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\hoodie_spike_sleeve_side_fix_v1\01_HoodieMaterialPreviewShape.png",
"renders\hoodie_spike_sleeve_side_fix_v1\02_HoodieLeftGraySide.png",
"renders\hoodie_spike_sleeve_side_fix_v1\03_HoodieRightGraySide.png",
"renders\hoodie_spike_sleeve_side_fix_v1\04_HoodieWireSpikeCheck.png",
"renders\hoodie_spike_sleeve_side_fix_v1\05_HoodieScenePreserved.png",
"renders\hoodie_spike_sleeve_side_fix_v1\HoodieSpikeSleeveSideFix_report.txt",
"renders\hoodie_spike_sleeve_side_fix_v1\HoodieSpikeSleeveSideFix_status.json",
"reports\hoodie_spike_sleeve_side_fix_v1\Hoodie_Spike_Sleeve_Side_Fix_v1.md",
"reports\hoodie_spike_sleeve_side_fix_v1\hoodie_spike_sleeve_side_fix_v1.json",
"renders\current_review\01_HoodieMaterialPreviewShape.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== HOODIE SPIKE / SLEEVE / SIDE FIX VALIDATION PASS ==="
