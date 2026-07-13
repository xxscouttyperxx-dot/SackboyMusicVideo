$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"reports\temp_safe_duplicate_visibility_cleanup_v1\Temp_Safe_Duplicate_Visibility_Cleanup_v1.md",
"reports\temp_safe_duplicate_visibility_cleanup_v1\TempSafeDuplicateVisibilityCleanup_report.txt",
"reports\temp_safe_duplicate_visibility_cleanup_v1\TempSafeDuplicateVisibilityCleanup_status.json",
"reports\temp_safe_duplicate_visibility_cleanup_v1\temp_safe_duplicate_visibility_cleanup_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== TEMP SAFE DUPLICATE VISIBILITY CLEANUP VALIDATION PASS ==="
