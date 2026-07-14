param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
function Unstage-IfTracked([string]$PathSpec){$tracked=git ls-files -- "$PathSpec"; if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}}
Write-Host "[PublishReportsOnly] Staging v1M reports/renders/scripts only. Never staging .blend, .blend1, or Backups."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
$paths=@("Apply-CollarSnapShapeSeatV1M.ps1","Validate-CollarSnapShapeSeatV1M.ps1","Publish-CollarSnapShapeSeatReports.ps1","Try-PushBlendOnly.ps1","README-CollarSnapShapeSeatV1M.txt","blender/scripts/collar_snap_shape_seat_v1M.py","reports/collar_snap_shape_seat_v1M","renders/current_review")
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
git status --short
git diff --cached --quiet; $code=$LASTEXITCODE
if($code -eq 0){Write-Host "[PublishReportsOnly] No staged changes to commit."}else{git commit -m "Add collar snap shape seat v1M reports and renders"}
git push origin main
Write-Host "[PublishReportsOnly] Done."
