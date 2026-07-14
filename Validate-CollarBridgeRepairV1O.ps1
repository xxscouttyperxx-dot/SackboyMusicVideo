param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\collar_bridge_repair_v1O\CollarBridgeRepairV1O_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if(-not $status.saved_blend){throw "Validation failed: saved_blend was false."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
if($status.v1N_shape_key.value_after -ne 0){throw "Validation failed: v1N shape key was not disabled."}
if(-not $status.bridge.created){throw "Validation failed: collar bridge object was not created."}
if($status.hoodie_topology.boundary_edges_after -ne $status.hoodie_topology.boundary_edges_before){throw "Validation failed: hoodie topology boundary count changed."}
if($status.bridge.vertex_count -lt 100){throw "Validation failed: collar bridge mesh is too small."}
Write-Host "=== COLLAR BRIDGE REPAIR V1O VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "v1N shape key disabled: before=$($status.v1N_shape_key.value_before); after=$($status.v1N_shape_key.value_after)"
Write-Host "Bridge object: $($status.bridge.name)"
Write-Host "Bridge vertices/faces: $($status.bridge.vertex_count)/$($status.bridge.face_count)"
Write-Host "Bridge radii x/y: $($status.bridge.x_radius_outer)/$($status.bridge.y_radius_outer)"
Write-Host "Bridge vertical height: $($status.bridge.vertical_height)"
Write-Host "Hoodie boundary edges unchanged: $($status.hoodie_topology.boundary_edges_before)"
Write-Host "Hoodie boundary loops unchanged: $($status.hoodie_topology.boundary_loops_before)"
Write-Host "No backup creation confirmed."
