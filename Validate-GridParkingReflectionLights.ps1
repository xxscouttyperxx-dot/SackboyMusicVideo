$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\grid_parking_reflection_lights_v1\01_GridAsphaltPaintRestored.png",
"renders\grid_parking_reflection_lights_v1\02_ReflectionLightsFarEnd.png",
"renders\grid_parking_reflection_lights_v1\03_CharacterFitNextCheck.png",
"renders\grid_parking_reflection_lights_v1\GridParkingReflectionLights_report.txt",
"renders\grid_parking_reflection_lights_v1\GridParkingReflectionLights_status.json",
"reports\grid_parking_reflection_lights_v1\Grid_Parking_Reflection_Lights_v1.md",
"reports\grid_parking_reflection_lights_v1\grid_parking_reflection_lights_v1.json",
"renders\current_review\01_GridAsphaltPaintRestored.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== GRID PARKING / REFLECTION LIGHTS VALIDATION PASS ==="
