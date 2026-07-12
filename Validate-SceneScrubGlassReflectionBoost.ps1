$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\scene_scrub_glass_reflection_boost_v1\01_ParkingEdgeScrubCheck.png",
"renders\scene_scrub_glass_reflection_boost_v1\02_GlassReflectionBoostCheck.png",
"renders\scene_scrub_glass_reflection_boost_v1\03_CharacterFitReadyCheck.png",
"renders\scene_scrub_glass_reflection_boost_v1\SceneScrubGlassReflectionBoost_report.txt",
"renders\scene_scrub_glass_reflection_boost_v1\SceneScrubGlassReflectionBoost_status.json",
"reports\scene_scrub_glass_reflection_boost_v1\Scene_Scrub_Glass_Reflection_Boost_v1.md",
"reports\scene_scrub_glass_reflection_boost_v1\scene_scrub_glass_reflection_boost_v1.json",
"renders\current_review\01_ParkingEdgeScrubCheck.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== SCENE SCRUB / GLASS REFLECTION BOOST VALIDATION PASS ==="
