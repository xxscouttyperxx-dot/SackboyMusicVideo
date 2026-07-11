$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\cleanup_reset_validation\01_Clean_Hero.png",
"renders\cleanup_reset_validation\02_Clean_Low.png",
"renders\cleanup_reset_validation\03_Clean_Orbit.png",
"renders\cleanup_reset_validation\CleanupReset_inventory.txt"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== PROJECT CLEANUP RESET VALIDATION PASS ==="
Write-Host "Clean scene validation renders and inventory are present."
