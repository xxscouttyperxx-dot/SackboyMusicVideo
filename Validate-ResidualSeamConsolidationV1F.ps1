param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\residual_seam_consolidation_v1F\ResidualSeamConsolidationV1F_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if(-not $status.saved_blend){throw "Validation failed: saved_blend was false."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
if($status.before.boundary_edges -lt $status.after.boundary_edges){throw "Validation failed: boundary edge count increased."}
if($status.before.boundary_loop_count -lt $status.after.boundary_loop_count){throw "Validation failed: boundary loop count increased."}
Write-Host "=== RESIDUAL SEAM CONSOLIDATION V1F VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "Boundary edges: before=$($status.before.boundary_edges); after=$($status.after.boundary_edges)"
Write-Host "Boundary loops: before=$($status.before.boundary_loop_count); after=$($status.after.boundary_loop_count)"
Write-Host "Accepted seam pairs: $($status.repair.total_pairs_accepted)"
Write-Host "Smoothed vertices: $($status.repair.total_smoothed_vertices)"
Write-Host "Max local vertex movement: $($status.repair.max_local_vertex_movement)"
Write-Host "Armpit cameras used: left=$($status.rendering.left_armpit_camera); right=$($status.rendering.right_armpit_camera)"
Write-Host "No backup creation confirmed."
