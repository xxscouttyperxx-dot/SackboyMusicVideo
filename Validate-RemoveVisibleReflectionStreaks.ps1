$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\remove_visible_reflection_streaks_v1\01_StorefrontNoFloatingStreaks.png",
"renders\remove_visible_reflection_streaks_v1\02_ReflectionCardsOnlyCheck.png",
"renders\remove_visible_reflection_streaks_v1\03_CharacterNoStreakIntersections.png",
"renders\remove_visible_reflection_streaks_v1\RemoveVisibleReflectionStreaks_report.txt",
"renders\remove_visible_reflection_streaks_v1\RemoveVisibleReflectionStreaks_status.json",
"reports\remove_visible_reflection_streaks_v1\Remove_Visible_Reflection_Streaks_v1.md",
"reports\remove_visible_reflection_streaks_v1\remove_visible_reflection_streaks_v1.json",
"renders\current_review\01_StorefrontNoFloatingStreaks.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== REMOVE VISIBLE REFLECTION STREAKS VALIDATION PASS ==="
