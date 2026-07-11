$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\BaselineCaptureScan-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_BaselineCaptureScan.blend") -Force
Copy-Item (Join-Path $PatchScripts "baseline_capture_scan_v1.py") (Join-Path $Scripts "baseline_capture_scan_v1.py") -Force

Write-Host "[BaselineCaptureScan] Cleaning old package root files..."
$Keep=@("Apply-BaselineCaptureScan.ps1","Validate-BaselineCaptureScan.ps1","Publish-CurrentReview.ps1","Clean-PackageRoot.ps1","README-BaselineCaptureScan.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-Step*.ps1","Validate-Step*.ps1","README-Step*.txt","Apply-Production*.ps1","Validate-Production*.ps1","README-Production*.txt","Apply-Project*.ps1","Validate-Project*.ps1","README-Project*.txt","Apply-HeroCar*.ps1","Validate-HeroCar*.ps1","README-HeroCar*.txt","Apply-LampSidewalkSkyCleanup.ps1","Validate-LampSidewalkSkyCleanup.ps1","README-LampSidewalkSkyCleanup.txt","Apply-StorefrontParking*.ps1","Validate-StorefrontParking*.ps1","README-StorefrontParking*.txt","Apply-AmbientCarGlassPolish.ps1","Validate-AmbientCarGlassPolish.ps1","README-AmbientCarGlassPolish.txt","Apply-CharacterWardrobePrep.ps1","Validate-CharacterWardrobePrep.ps1","README-CharacterWardrobePrep.txt","Apply-WardrobeCleanupAssetIntake.ps1","Validate-WardrobeCleanupAssetIntake.ps1","README-WardrobeCleanupAssetIntake.txt","Apply-PublishFix.ps1","README-PublishFix.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$Keep -notcontains $_.Name} |
        Remove-Item -Force
}

Write-Host "[BaselineCaptureScan] Running read-only scene scan and review render capture..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "baseline_capture_scan_v1.py")
if($LASTEXITCODE -ne 0){throw "Baseline capture scan failed."}

$Expected=@("renders\baseline_capture_scan_v1\BaselineCaptureScan_report.txt","reports\baseline_capture_scan_v1\Baseline_Capture_Scan_v1.md","reports\baseline_capture_scan_v1\baseline_capture_scan_v1.json","reports\project_workflow_audit\scene_layout_summary.md","renders\current_review\BaselineCaptureScan_report.txt")
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== BASELINE CAPTURE / SCAN PASS ==="
Write-Host "Read-only scan complete."
Write-Host "No scene objects, lights, materials, world/HDRI, car, clothing, or geometry were modified."
Write-Host "Current scene reports and review renders captured."
Write-Host "Backup: $BackupRoot"
