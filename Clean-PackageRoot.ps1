$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Keep=@("Apply-ProjectWorkflowAudit.ps1","Validate-ProjectWorkflowAudit.ps1","Publish-CurrentReview.ps1","Clean-PackageRoot.ps1","README-ProjectWorkflowAudit.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-Step*.ps1","Validate-Step*.ps1","README-Step*.txt","Apply-ProductionRecon*.ps1","Validate-ProductionRecon*.ps1","README-ProductionRecon*.txt","Apply-ProductionPreview.ps1","Validate-ProductionPreview.ps1","README-ProductionPreview.txt","Apply-ProjectCleanupReset.ps1","Validate-ProjectCleanupReset.ps1","README-ProjectCleanupReset.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue | Where-Object {$Keep -notcontains $_.Name} | Remove-Item -Force
}
Write-Host "=== PACKAGE ROOT CLEANED ==="
