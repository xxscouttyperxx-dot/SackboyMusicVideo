$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\glass_reflection_visibility_v1B\01_GlassReflectionClose.png",
"renders\glass_reflection_visibility_v1B\02_GlassReflectionOblique.png",
"renders\glass_reflection_visibility_v1B\03_ReflectionFXSetup.png",
"renders\glass_reflection_visibility_v1B\04_CharacterReadyUnchanged.png",
"renders\glass_reflection_visibility_v1B\GlassReflectionVisibility_report.txt",
"renders\glass_reflection_visibility_v1B\GlassReflectionVisibility_status.json",
"reports\glass_reflection_visibility_v1B\Glass_Reflection_Visibility_v1B.md",
"reports\glass_reflection_visibility_v1B\glass_reflection_visibility_v1B.json",
"renders\current_review\01_GlassReflectionClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== GLASS REFLECTION VISIBILITY v1B VALIDATION PASS ==="
