param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\dressed_rig_controls_v1_8\DressedRigControlsV1_8_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if($status.script_version -ne "1.8"){throw "Validation failed: wrong script version"}
if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if(-not $status.stage9_dressed_review_passed){throw "Validation failed: Stage 9 dressed review failed"}
if($status.stage9_corrections_applied_count -ne 0){throw "Validation failed: unexpected automatic clothing corrections"}
if($status.original_bone_change_count -ne 0){throw "Validation failed: unintended original rest-bone changes"}
if($status.pelvis_edit_reparent_geometry_error -gt 0.00000001){throw "Validation failed: pelvis rest geometry changed"}
if($status.allowed_original_hierarchy_change_count -ne 1){throw "Validation failed: expected exactly one approved hierarchy change"}
if($status.pelvis_control_mode -ne "DIRECT_BONE_PARENT_ORDERED_RESTORE"){throw "Validation failed: wrong pelvis control mode"}
if(-not $status.pelvis_parent_checks_passed){throw "Validation failed: pelvis hierarchy propagation probe failed"}
if($status.pelvis_parent_probe_movement -lt 0.049){throw "Validation failed: pelvis did not follow CTRL_pelvis"}
if($status.pelvis_parent_probe_restore_error -gt 0.000001){throw "Validation failed: pelvis hierarchy probe did not restore cleanly"}
if($status.control_bone_count -ne 12){throw "Validation failed: expected 12 new control bones"}
if($status.total_bone_count_after -ne 34){throw "Validation failed: expected 34 total bones"}
if($status.control_constraint_count -ne 11){throw "Validation failed: expected 11 control constraints"}
if($status.ik_switch_property_count -ne 4){throw "Validation failed: expected four IK/FK switches"}
if($status.constraint_driver_count -ne 8){throw "Validation failed: expected eight driven constraint influences"}
if(-not $status.control_rest_visual_check_passed){throw "Validation failed: controls changed the default rest appearance"}
if($status.control_rest_visual_max_error -gt 0.00001){throw "Validation failed: rest visual error exceeded tolerance"}
if(-not $status.stage11_automatic_checks_passed){throw "Validation failed: Stage 11 automatic checks failed"}
if($status.mesh_binding_snapshot_type -ne "POSE_INDEPENDENT_BINDING_SNAPSHOT"){throw "Validation failed: wrong binding snapshot type"}
if($status.mesh_binding_change_count -ne 0){throw "Validation failed: true mesh bindings or weights changed"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected scene objects changed"}
if($status.scene_frame_range_changed){throw "Validation failed: scene frame range changed"}
if($status.preserved_deformation_action -ne "F2_DEFORMATION_TEST_V1_2"){throw "Validation failed: previous deformation action was not preserved"}
if($status.active_validation_action -ne "SACKBOY_CONTROL_RIG_VALIDATION_V1"){throw "Validation failed: validation action is not active"}

Write-Host "=== DRESSED RIG + CONTROLS V1.8 VALIDATION PASS ==="
Write-Host "Stage 9 dressed review: $($status.stage9_dressed_review_passed)"
Write-Host "Stage 9 corrections applied: $($status.stage9_corrections_applied_count)"
Write-Host "Pelvis control mode: $($status.pelvis_control_mode)"
Write-Host "Pelvis hierarchy probe: $($status.pelvis_parent_checks_passed)"
Write-Host "New control bones: $($status.control_bone_count)"
Write-Host "Control constraints: $($status.control_constraint_count)"
Write-Host "IK/FK switches: $($status.ik_switch_property_count)"
Write-Host "Constraint drivers: $($status.constraint_driver_count)"
Write-Host "Total bones: $($status.total_bone_count_after)"
Write-Host "Default rest visual error: $($status.control_rest_visual_max_error)"
Write-Host "Stage 11 automatic checks: $($status.stage11_automatic_checks_passed)"
Write-Host "Binding snapshot: $($status.mesh_binding_snapshot_type)"
Write-Host "True mesh binding changes: $($status.mesh_binding_change_count)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "Inspect frames 300, 310, 320, 330, 340, 350, 360, 370, 380, and 390."
