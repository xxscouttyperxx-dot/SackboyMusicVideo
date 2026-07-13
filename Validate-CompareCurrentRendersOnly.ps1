$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\current_review\COMPARE_NOW_01_SceneWide_SOLID.png",
"renders\current_review\COMPARE_NOW_02_SceneWide_RENDERED.png",
"renders\current_review\COMPARE_NOW_03_HoodCharacterFront_SOLID.png",
"renders\current_review\COMPARE_NOW_04_HoodCharacterFront_RENDERED.png",
"renders\current_review\COMPARE_NOW_05_CharacterThreeQuarter_SOLID.png",
"renders\current_review\COMPARE_NOW_06_CharacterThreeQuarter_RENDERED.png",
"reports\compare_current_renders_only_v1\CompareCurrentRendersOnly_report.txt",
"reports\compare_current_renders_only_v1\CompareCurrentRendersOnly_status.json",
"reports\compare_current_renders_only_v1\Compare_Current_Renders_Only_v1.md",
"reports\compare_current_renders_only_v1\compare_current_renders_only_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== COMPARE CURRENT RENDERS ONLY VALIDATION PASS ==="
