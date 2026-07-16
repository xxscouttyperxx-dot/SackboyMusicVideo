param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\f2_bind_weights_v1\F2BindWeightsV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.armature_count_after -ne 1){throw "Validation failed: expected one armature"}
if($status.f2_armature_modifier_count_after -ne 1){throw "Validation failed: F2 needs exactly one Armature modifier"}
if($status.other_target_armature_modifier_count_after -ne 0){throw "Validation failed: non-F2 targets received Armature modifiers"}
if($status.unweighted_vertex_count -ne 0){throw "Validation failed: F2 has unweighted vertices"}
if($status.invalid_weight_sum_vertex_count -ne 0){throw "Validation failed: F2 contains invalid normalized weight sums"}
if($status.rest_visual_world_error -gt 0.00001){throw "Validation failed: F2 moved in the rest pose"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected objects changed"}
if($status.armature_rest_change_count -ne 0){throw "Validation failed: armature rest bones changed"}
if($status.rig_action_created){throw "Validation failed: this stage should not create rig animation"}

Write-Host "=== F2-ONLY BIND / WEIGHTS VALIDATION PASS ==="
Write-Host "Weighting method: $($status.weighting_method)"
Write-Host "F2 vertices: $($status.f2_vertex_count)"
Write-Host "Deform groups: $($status.deform_group_count)"
Write-Host "Unweighted vertices: $($status.unweighted_vertex_count)"
Write-Host "Invalid weight sums: $($status.invalid_weight_sum_vertex_count)"
Write-Host "Maximum influences per vertex: $($status.maximum_influences_per_vertex)"
Write-Host "Rest visual error: $($status.rest_visual_world_error)"
Write-Host "Other targets bound: $($status.other_target_armature_modifier_count_after)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "No test animation was created."
