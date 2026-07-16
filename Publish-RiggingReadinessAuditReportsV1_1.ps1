param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

function Unstage-IfTracked([string]$PathSpec){
    $tracked = git ls-files -- "$PathSpec"
    if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}
}

Write-Host "[ReportsOnly] Staging only v1 audit scripts and reports. Never staging .blend or .blend1."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

$paths = @(
    "Apply-RiggingReadinessAuditV1_1.ps1",
    "Validate-RiggingReadinessAuditV1_1.ps1",
    "Publish-RiggingReadinessAuditReportsV1_1.ps1",
    "Optional-PushCurrentBaselineBlendOnly.ps1",
    "README-RiggingReadinessAuditV1_1.txt",
    "blender/scripts/rigging_readiness_audit_v1.py",
    "reports/rigging_readiness_audit_v1"
)

foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}

Unstage-IfTracked "blender/sackboy_scene.blend"
Unstage-IfTracked "blender/sackboy_scene.blend1"

git status --short
git diff --cached --quiet
if($LASTEXITCODE -eq 0){
    Write-Host "[ReportsOnly] No staged report changes."
}else{
    git commit -m "Add rigging readiness audit v1"
}
git push origin main
Write-Host "[ReportsOnly] Done."
