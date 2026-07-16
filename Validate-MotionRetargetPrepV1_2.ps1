param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\motion_retarget_prep_v1_2\MotionRetargetPrepV1_2_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if($status.script_version -ne "1.2"){throw "Validation failed: wrong script version"}
if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.total_bone_count -ne 34){throw "Validation failed: expected 34 bones"}
if($status.bone_collection_count -ne 4){throw "Validation failed: expected four bone collections"}
if(-not $status.bone_collection_assignment_checks_passed){throw "Validation failed: bone collection assignments are not exact"}
if($status.main_control_count -ne 5){throw "Validation failed: expected five main controls"}
if($status.ik_control_count -ne 4){throw "Validation failed: expected four IK controls"}
if($status.pole_control_count -ne 4){throw "Validation failed: expected four pole controls"}
if($status.deform_bone_count -ne 21){throw "Validation failed: expected 21 deform bones"}
if($status.custom_shaped_control_count -ne 13){throw "Validation failed: expected 13 custom-shaped controls"}
if(-not $status.controls_only_default){throw "Validation failed: controls-only view is not the default"}
if($status.rest_visual_max_error -gt 0.00001){throw "Validation failed: rest appearance changed"}
if($status.rest_bone_change_count -ne 0){throw "Validation failed: rest bones changed"}
if($status.constraint_change_count -ne 0){throw "Validation failed: constraints changed"}
if($status.action_change_count -ne 0){throw "Validation failed: actions changed"}
if($status.mesh_binding_change_count -ne 0){throw "Validation failed: mesh bindings or weights changed"}
if($status.protected_snapshot_mode -ne "SAME_FRAME_EVALUATED_STATE"){throw "Validation failed: wrong protected snapshot mode"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected objects changed"}
if($status.scene_frame_range_changed){throw "Validation failed: scene frame range changed"}
if(-not $status.original_frame_restored){throw "Validation failed: original frame was not restored"}
if(-not $status.retarget_profile_written){throw "Validation failed: retarget profile missing"}
if(-not $status.rig_manifest_written){throw "Validation failed: rig manifest missing"}

Write-Host "=== MOTION RETARGET PREP V1.2 VALIDATION PASS ==="
Write-Host "Bone collections: $($status.bone_collection_count)"
Write-Host "Exact collection assignments: $($status.bone_collection_assignment_checks_passed)"
Write-Host "Main controls: $($status.main_control_count)"
Write-Host "IK controls: $($status.ik_control_count)"
Write-Host "Pole controls: $($status.pole_control_count)"
Write-Host "Deform bones: $($status.deform_bone_count)"
Write-Host "Custom-shaped controls: $($status.custom_shaped_control_count)"
Write-Host "Controls-only default: $($status.controls_only_default)"
Write-Host "Rest visual error: $($status.rest_visual_max_error)"
Write-Host "Rest-bone changes: $($status.rest_bone_change_count)"
Write-Host "Constraint changes: $($status.constraint_change_count)"
Write-Host "Action changes: $($status.action_change_count)"
Write-Host "Binding changes: $($status.mesh_binding_change_count)"
Write-Host "Protected snapshot mode: $($status.protected_snapshot_mode)"
Write-Host "Protected comparison frame: $($status.protected_comparison_frame)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "Retarget profile: $($status.retarget_profile_path)"
Write-Host "Rig manifest: $($status.rig_manifest_path)"
