param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\clothing_accessory_bind_v1\ClothingAccessoryBindV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if($status.script_version -ne "1.0"){throw "Validation failed: wrong script version"}
if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.clothing_armature_modifier_count -ne 2){throw "Validation failed: expected two clothing Armature modifiers"}
if($status.clothing_unweighted_vertex_count -ne 0){throw "Validation failed: clothing has unweighted vertices"}
if($status.clothing_invalid_weight_sum_count -ne 0){throw "Validation failed: clothing contains invalid weight sums"}
if($status.rest_visual_max_error -gt 0.00001){throw "Validation failed: rest appearance changed"}
if(-not $status.attachment_parent_checks_passed){throw "Validation failed: rigid accessory parent checks failed"}
if(-not $status.motion_response_checks_passed){throw "Validation failed: bound targets did not respond to test poses"}
if($status.f2_change_count -ne 0){throw "Validation failed: F2 binding changed"}
if($status.armature_rest_change_count -ne 0){throw "Validation failed: armature rest bones changed"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected scene objects changed"}
if($status.scene_frame_range_changed){throw "Validation failed: scene frame range changed"}

Write-Host "=== CLOTHING / ACCESSORY BIND VALIDATION PASS ==="
Write-Host "Hoodie vertices: $($status.clothing_metrics.'Lowerpoly hoodie'.vertex_count)"
Write-Host "Pants vertices: $($status.clothing_metrics.'Cargo pants'.vertex_count)"
Write-Host "Clothing unweighted vertices: $($status.clothing_unweighted_vertex_count)"
Write-Host "Invalid clothing weight sums: $($status.clothing_invalid_weight_sum_count)"
Write-Host "Rest visual max error: $($status.rest_visual_max_error)"
Write-Host "Accessory parents valid: $($status.attachment_parent_checks_passed)"
Write-Host "Test-pose motion response: $($status.motion_response_checks_passed)"
Write-Host "F2 changes: $($status.f2_change_count)"
Write-Host "Protected changes: $($status.protected_change_count)"
