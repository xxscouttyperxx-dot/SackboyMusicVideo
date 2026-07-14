param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
$statusPath=".\reports\seam_zone_edit_style_audit_v1J\SeamZoneEditStyleAuditV1J_status.json"
if(!(Test-Path $statusPath)){throw "Missing status file: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json
if($status.saved_blend){throw "Validation failed: saved_blend was true."}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files were created."}
if($status.hoodie_target -ne "SACKBOY_Hoodie_EditProxy"){throw "Validation failed: unexpected hoodie target '$($status.hoodie_target)'"}
if($status.body_target -ne "F2"){throw "Validation failed: unexpected body target '$($status.body_target)'"}
Write-Host "=== SEAM ZONE EDIT-STYLE AUDIT V1J VALIDATION PASS ==="
Write-Host "Targets: hoodie=$($status.hoodie_target); body=$($status.body_target)"
Write-Host "Boundary edges: $($status.current.boundary_edges)"
Write-Host "Boundary loops: $($status.current.boundary_loop_count)"
Write-Host "Left armpit zone edges: $($status.zones.left_armpit.edges_within_radius); components=$($status.zones.left_armpit.components_within_radius)"
Write-Host "Right armpit zone edges: $($status.zones.right_armpit.edges_within_radius); components=$($status.zones.right_armpit.components_within_radius)"
Write-Host "Collar front zone edges: $($status.zones.hood_collar_front.edges_within_radius); components=$($status.zones.hood_collar_front.components_within_radius)"
Write-Host "Collar back zone edges: $($status.zones.hood_collar_back.edges_within_radius); components=$($status.zones.hood_collar_back.components_within_radius)"
Write-Host "Hood top zone edges: $($status.zones.hood_top.edges_within_radius); components=$($status.zones.hood_top.components_within_radius)"
Write-Host "Closeups hide Sackboy: $($status.rendering.closeups_hide_sackboy)"
Write-Host "No .blend save and no backup creation confirmed."
