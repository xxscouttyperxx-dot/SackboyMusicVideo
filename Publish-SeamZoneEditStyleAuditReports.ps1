param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
function Unstage-IfTracked([string]$PathSpec){$tracked=git ls-files -- "$PathSpec"; if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}}
Write-Host "[PublishReportsOnly] Staging v1J audit reports/renders/scripts only. Never staging .blend, .blend1, or Backups."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
$paths=@("Apply-SeamZoneEditStyleAuditV1J.ps1","Validate-SeamZoneEditStyleAuditV1J.ps1","Publish-SeamZoneEditStyleAuditReports.ps1","README-SeamZoneEditStyleAuditV1J.txt","blender/scripts/seam_zone_edit_style_audit_v1J.py","reports/seam_zone_edit_style_audit_v1J","renders/current_review")
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
git status --short
git diff --cached --quiet; $code=$LASTEXITCODE
if($code -eq 0){Write-Host "[PublishReportsOnly] No staged changes to commit."}else{git commit -m "Add seam zone edit-style audit v1J reports and renders"}
git push origin main
Write-Host "[PublishReportsOnly] Done."
