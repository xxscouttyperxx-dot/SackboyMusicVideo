$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\scene_scrub_glass_reflection_boost_v1B\01_SceneScrub_Overview.png",
"renders\scene_scrub_glass_reflection_boost_v1B\02_GlassReflectionBoost.png",
"renders\scene_scrub_glass_reflection_boost_v1B\03_ReflectionTrafficSetup.png",
"renders\scene_scrub_glass_reflection_boost_v1B\04_CharacterFitReady.png",
"renders\scene_scrub_glass_reflection_boost_v1B\SceneScrubGlassReflectionBoost_report.txt",
"renders\scene_scrub_glass_reflection_boost_v1B\SceneScrubGlassReflectionBoost_status.json",
"reports\scene_scrub_glass_reflection_boost_v1B\Scene_Scrub_Glass_Reflection_Boost_v1B.md",
"reports\scene_scrub_glass_reflection_boost_v1B\scene_scrub_glass_reflection_boost_v1B.json",
"renders\current_review\01_SceneScrub_Overview.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== SCENE SCRUB / GLASS REFLECTION BOOST v1B VALIDATION PASS ==="
