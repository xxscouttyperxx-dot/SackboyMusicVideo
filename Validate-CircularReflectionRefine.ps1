$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\circular_reflection_refine_v1\01_CircularReflectionClose.png",
"renders\circular_reflection_refine_v1\02_CircularReflectionOblique.png",
"renders\circular_reflection_refine_v1\03_ReflectionSourceLayout.png",
"renders\circular_reflection_refine_v1\04_CharacterReadyUnchanged.png",
"renders\circular_reflection_refine_v1\CircularReflectionRefine_report.txt",
"renders\circular_reflection_refine_v1\CircularReflectionRefine_status.json",
"reports\circular_reflection_refine_v1\Circular_Reflection_Refine_v1.md",
"reports\circular_reflection_refine_v1\circular_reflection_refine_v1.json",
"renders\current_review\01_CircularReflectionClose.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CIRCULAR REFLECTION REFINE VALIDATION PASS ==="
