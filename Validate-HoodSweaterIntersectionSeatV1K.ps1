param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\hood_sweater_intersection_seat_v1K\HoodSweaterIntersectionSeatV1K_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if(-not $status.saved_blend){throw "Validation failed: saved_blend was false."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
if($status.after.boundary_edges -gt $status.before.boundary_edges){throw "Validation failed: boundary edge count increased."}
if($status.after.boundary_loop_count -gt $status.before.boundary_loop_count){throw "Validation failed: boundary loop count increased."}
if($status.repair.total_pairs_accepted -lt 1){throw "Validation failed: no seam seating pairs were accepted."}
Write-Host "=== HOOD SWEATER INTERSECTION SEAT V1K VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "Boundary edges: before=$($status.before.boundary_edges); after=$($status.after.boundary_edges)"
Write-Host "Boundary loops: before=$($status.before.boundary_loop_count); after=$($status.after.boundary_loop_count)"
Write-Host "Accepted seam seating pairs: $($status.repair.total_pairs_accepted)"
Write-Host "Smoothed vertices: $($status.repair.total_smoothed_vertices)"
Write-Host "Max local vertex movement: $($status.repair.max_local_vertex_movement)"
Write-Host "Collar back pairs: $($status.repair.zones.hood_collar_back.pairs_accepted)"
Write-Host "Collar front pairs: $($status.repair.zones.hood_collar_front.pairs_accepted)"
Write-Host "Left armpit pairs: $($status.repair.zones.left_armpit.pairs_accepted)"
Write-Host "Right armpit pairs: $($status.repair.zones.right_armpit.pairs_accepted)"
Write-Host "No backup creation confirmed."
