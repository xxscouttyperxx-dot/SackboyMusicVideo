param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
function Unstage-IfTracked([string]$PathSpec){$tracked=git ls-files -- "$PathSpec"; if($tracked){git reset -q HEAD -- "$PathSpec" 2>$null}}
Write-Host "[PublishReportsOnly] Staging v1K reports/renders/scripts only. Never staging .blend, .blend1, or Backups."
git restore --staged . 2>$null
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
$paths=@("Apply-HoodSweaterIntersectionSeatV1K.ps1","Validate-HoodSweaterIntersectionSeatV1K.ps1","Publish-HoodSweaterIntersectionSeatReports.ps1","Try-PushBlendOnly.ps1","README-HoodSweaterIntersectionSeatV1K.txt","blender/scripts/hood_sweater_intersection_seat_v1K.py","reports/hood_sweater_intersection_seat_v1K","renders/current_review")
foreach($p in $paths){if(Test-Path $p){git add -- "$p"}}
Unstage-IfTracked "blender/sackboy_scene.blend"; Unstage-IfTracked "blender/sackboy_scene.blend1"
git status --short
git diff --cached --quiet; $code=$LASTEXITCODE
if($code -eq 0){Write-Host "[PublishReportsOnly] No staged changes to commit."}else{git commit -m "Add hood sweater intersection seat v1K reports and renders"}
git push origin main
Write-Host "[PublishReportsOnly] Done."
