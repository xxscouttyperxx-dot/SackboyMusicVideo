$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@("renders\baseline_capture_scan_v1\BaselineCaptureScan_report.txt","reports\baseline_capture_scan_v1\Baseline_Capture_Scan_v1.md","reports\baseline_capture_scan_v1\baseline_capture_scan_v1.json","reports\project_workflow_audit\scene_layout_summary.md","renders\current_review\BaselineCaptureScan_report.txt")
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== BASELINE CAPTURE / SCAN VALIDATION PASS ==="
