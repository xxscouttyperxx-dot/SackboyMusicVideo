param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\collar_parallel_snap_v1N\CollarParallelSnapV1N_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if(-not $status.saved_blend){throw "Validation failed: saved_blend was false."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
if($status.shape_key.name -ne "SEAMSEAT_CollarParallelSnap_v1N"){throw "Validation failed: expected shape key not active."}
if($status.shape_key.value -ne 1){throw "Validation failed: shape key value is not 1."}
if($status.metrics.boundary_edges_after -ne $status.metrics.boundary_edges_before){throw "Validation failed: topology boundary edge count changed."}
if($status.metrics.boundary_loops_after -ne $status.metrics.boundary_loops_before){throw "Validation failed: topology boundary loop count changed."}
if($status.snap.total_vertices_moved -lt 10){throw "Validation failed: too few collar vertices moved for an aggressive pass."}
if($status.snap.average_gap_reduction_ratio -lt 0.55){throw "Validation failed: average gap reduction was not significant enough."}
Write-Host "=== COLLAR PARALLEL SNAP V1N VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "Shape key: $($status.shape_key.name); value=$($status.shape_key.value)"
Write-Host "Boundary edges unchanged: $($status.metrics.boundary_edges_before)"
Write-Host "Boundary loops unchanged: $($status.metrics.boundary_loops_before)"
Write-Host "Moved collar vertices: $($status.snap.total_vertices_moved)"
Write-Host "Average gap before: $($status.snap.average_gap_before)"
Write-Host "Average gap after: $($status.snap.average_gap_after)"
Write-Host "Average gap reduction ratio: $($status.snap.average_gap_reduction_ratio)"
Write-Host "Max local vertex movement: $($status.snap.max_local_vertex_movement)"
Write-Host "Left side moved: $($status.snap.zones.collar_side_left.vertices_moved)"
Write-Host "Right side moved: $($status.snap.zones.collar_side_right.vertices_moved)"
Write-Host "Back/wide moved: $($status.snap.zones.collar_back_wide.vertices_moved)"
Write-Host "Front/wide moved: $($status.snap.zones.collar_front_wide.vertices_moved)"
Write-Host "No backup creation confirmed."
