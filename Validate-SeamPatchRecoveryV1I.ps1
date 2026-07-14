param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\seam_patch_recovery_v1I\SeamPatchRecoveryV1I_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if($status.saved_blend){throw "Validation failed: saved_blend was true."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
Write-Host "=== SEAM PATCH RECOVERY V1I VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "Current boundary edges: $($status.current.boundary_edges)"
Write-Host "Current boundary loops: $($status.current.boundary_loop_count)"
Write-Host "Current polygon islands: $($status.current.polygon_island_count)"
Write-Host "Compared to v1F after: edges delta=$($status.comparison_to_v1F_after.boundary_edges_delta); loops delta=$($status.comparison_to_v1F_after.boundary_loop_delta)"
Write-Host "Armpit cameras used: left=$($status.rendering.left_armpit_camera); right=$($status.rendering.right_armpit_camera)"
Write-Host "Closeups hide Sackboy: $($status.rendering.closeups_hide_sackboy)"
Write-Host "No .blend save and no backup creation confirmed."
