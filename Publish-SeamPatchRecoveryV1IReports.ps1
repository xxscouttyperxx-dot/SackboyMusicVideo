param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
function Unstage-IfTracked([string]$PathSpec){$tracked=git ls-files -- "$PathSpec"; if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}}
Write-Host "[PublishReportsOnly] Staging v1I recovery reports/renders/scripts only. Never staging .blend, .blend1, or Backups."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
$paths=@("Apply-SeamPatchRecoveryV1I.ps1","Validate-SeamPatchRecoveryV1I.ps1","Publish-SeamPatchRecoveryV1IReports.ps1","README-SeamPatchRecoveryV1I.txt","blender/scripts/seam_patch_recovery_v1I.py","reports/seam_patch_recovery_v1I","renders/current_review")
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
git status --short
git diff --cached --quiet; $code=$LASTEXITCODE
if($code -eq 0){Write-Host "[PublishReportsOnly] No staged changes to commit."}else{git commit -m "Add seam patch recovery v1I reports and renders"}
git push origin main
Write-Host "[PublishReportsOnly] Done."
