$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\ambient_car_glass_polish_v1\01_CarAmberRead.png",
"renders\ambient_car_glass_polish_v1\02_WindowReflectionPolish.png",
"renders\ambient_car_glass_polish_v1\03_StableSceneMood.png",
"renders\ambient_car_glass_polish_v1\AmbientCarGlassPolish_status.json",
"renders\ambient_car_glass_polish_v1\AmbientCarGlassPolish_report.txt",
"renders\current_review\01_CarAmberRead.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== AMBIENT CAR / GLASS POLISH VALIDATION PASS ==="
