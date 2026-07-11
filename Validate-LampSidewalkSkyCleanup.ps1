$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\lamp_sidewalk_sky_cleanup\01_LampSidewalk_Hero.png",
"renders\lamp_sidewalk_sky_cleanup\02_LampVisibility.png",
"renders\lamp_sidewalk_sky_cleanup\03_HighLayout.png",
"renders\lamp_sidewalk_sky_cleanup\LampSidewalkSkyCleanup_status.json",
"renders\lamp_sidewalk_sky_cleanup\LampSidewalkSkyCleanup_report.txt",
"renders\current_review\01_LampSidewalk_Hero.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== LAMP / SIDEWALK / SKY CLEANUP VALIDATION PASS ==="
Write-Host "Cleanup renders, status, report, and current_review outputs are present."
