param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
function Unstage-IfTracked([string]$PathSpec){$tracked=git ls-files -- "$PathSpec"; if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}}
Write-Host "[PublishReportsOnly] Staging v1F reports/renders/scripts only. Never staging .blend, .blend1, or Backups."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
$paths=@("Apply-ResidualSeamConsolidationV1F.ps1","Validate-ResidualSeamConsolidationV1F.ps1","Publish-ResidualSeamConsolidationV1FReports.ps1","Try-PushBlendOnly.ps1","README-ResidualSeamConsolidationV1F.txt","blender/scripts/residual_seam_consolidation_v1F.py","reports/residual_seam_consolidation_v1F","renders/current_review")
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
git status --short
git diff --cached --quiet; $code=$LASTEXITCODE
if($code -eq 0){Write-Host "[PublishReportsOnly] No staged changes to commit."}else{git commit -m "Add residual seam consolidation v1F reports and renders"}
git push origin main
Write-Host "[PublishReportsOnly] Done."
