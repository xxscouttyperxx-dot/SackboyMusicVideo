$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\cycles_reflection_cards_v1\01_CyclesGlassReflectionClose.png",
"renders\cycles_reflection_cards_v1\02_CyclesGlassReflectionOblique.png",
"renders\cycles_reflection_cards_v1\03_ReflectionCardsNotCameraVisible.png",
"renders\cycles_reflection_cards_v1\04_CharacterReadyUnchanged.png",
"renders\cycles_reflection_cards_v1\CyclesReflectionCards_report.txt",
"renders\cycles_reflection_cards_v1\CyclesReflectionCards_status.json",
"reports\cycles_reflection_cards_v1\Cycles_Reflection_Cards_v1.md",
"reports\cycles_reflection_cards_v1\cycles_reflection_cards_v1.json",
"renders\current_review\01_CyclesGlassReflectionClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CYCLES REFLECTION CARDS VALIDATION PASS ==="
