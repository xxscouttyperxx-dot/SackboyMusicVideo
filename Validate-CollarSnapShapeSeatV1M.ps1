param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\collar_snap_shape_seat_v1M\CollarSnapShapeSeatV1M_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if(-not $status.saved_blend){throw "Validation failed: saved_blend was false."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
if($status.shape_key.name -ne "SEAMSEAT_CollarSnap_v1M"){throw "Validation failed: expected shape key not active."}
if($status.shape_key.value -ne 1){throw "Validation failed: shape key value is not 1."}
if($status.metrics.boundary_edges_after -ne $status.metrics.boundary_edges_before){throw "Validation failed: topology boundary edge count changed."}
if($status.metrics.boundary_loops_after -ne $status.metrics.boundary_loops_before){throw "Validation failed: topology boundary loop count changed."}
if($status.repair.total_pairs -lt 1){throw "Validation failed: no collar snap pairs were accepted."}
Write-Host "=== COLLAR SNAP SHAPE SEAT V1M VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "Shape key: $($status.shape_key.name); value=$($status.shape_key.value)"
Write-Host "Boundary edges unchanged: $($status.metrics.boundary_edges_before)"
Write-Host "Boundary loops unchanged: $($status.metrics.boundary_loops_before)"
Write-Host "Collar snap pairs: $($status.repair.total_pairs)"
Write-Host "Smoothed vertices: $($status.repair.total_smoothed_vertices)"
Write-Host "Max local vertex movement: $($status.repair.max_local_vertex_movement)"
Write-Host "Collar back pairs: $($status.repair.zones.hood_collar_back.pairs)"
Write-Host "Collar front pairs: $($status.repair.zones.hood_collar_front.pairs)"
Write-Host "Collar wide pairs: $($status.repair.zones.hood_collar_wide.pairs)"
Write-Host "No backup creation confirmed."
