$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"reports\collection_visibility_fix_retry_push_v1\Collection_Visibility_Fix_Retry_Push_v1.md",
"reports\collection_visibility_fix_retry_push_v1\CollectionVisibilityFixRetryPush_report.txt",
"reports\collection_visibility_fix_retry_push_v1\CollectionVisibilityFixRetryPush_status.json",
"reports\collection_visibility_fix_retry_push_v1\collection_visibility_fix_retry_push_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== COLLECTION VISIBILITY FIX VALIDATION PASS ==="
