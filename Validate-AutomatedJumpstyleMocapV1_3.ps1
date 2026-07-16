param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\jumpstyle_mocap_v1\JumpstyleMocapV1_status.json"
$processedPath=".\motion\extracted\dance_reference_pose_processed_v1.json"
$overlayPath=".\motion\extracted\dance_reference_tracking_overlay_v1.mp4"
if(!(Test-Path $statusPath)){throw "Missing status: $statusPath"}
if(!(Test-Path $processedPath)){throw "Missing processed landmarks: $processedPath"}
if(!(Test-Path $overlayPath)){throw "Missing tracking overlay: $overlayPath"}

$status=Get-Content $statusPath -Raw | ConvertFrom-Json
$processed=Get-Content $processedPath -Raw | ConvertFrom-Json

if($status.script_version -ne "1.3"){throw "Validation failed: wrong script version"}
if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.target_action -ne "SACKBOY_JUMPSTYLE_RETARGET_V1"){throw "Validation failed: wrong target action"}
if($status.source_frame_count -ne 764){throw "Validation failed: expected 764 source frames"}
if([math]::Abs($status.source_fps-30.0) -gt 0.001){throw "Validation failed: expected 30 FPS source"}
if(-not $processed.quality.passed){throw "Validation failed: pose extraction quality failed"}
if($processed.quality.detection_rate -lt 0.90){throw "Validation failed: pose detection rate below 90%"}
if($processed.quality.median_key_visibility -lt 0.50){throw "Validation failed: landmark visibility too low"}
if($processed.quality.longest_missing_gap_frames -gt 15){throw "Validation failed: missing tracking gap too long"}
if($status.keyed_control_count -ne 13){throw "Validation failed: expected 13 keyed controls"}
if($status.keyed_switch_count -ne 4){throw "Validation failed: expected four keyed IK switches"}
if($status.action_storage_api -ne "LAYERED_ACTION_CHANNELBAGS" -and $status.action_storage_api -ne "LEGACY_ACTION_FCURVES"){
    throw "Validation failed: unknown Blender Action storage API"
}
if($status.fcurve_count -lt 79){throw "Validation failed: expected at least 79 generated F-Curves"}
if($status.action_layer_count -lt 1){throw "Validation failed: generated action has no layer"}
if($status.action_slot_count -lt 1){throw "Validation failed: generated action has no slot"}
if($status.action_channelbag_count -lt 1 -and $status.action_storage_api -eq "LAYERED_ACTION_CHANNELBAGS"){
    throw "Validation failed: layered action has no channelbag"
}
if(-not $status.geometry_checks_passed){throw "Validation failed: geometry checks failed"}
if($status.left_contact_max_target_slide -gt 0.00001){throw "Validation failed: left locked-foot target slides"}
if($status.right_contact_max_target_slide -gt 0.00001){throw "Validation failed: right locked-foot target slides"}
if($status.rest_bone_change_count -ne 0){throw "Validation failed: rest bones changed"}
if($status.constraint_snapshot_mode -ne "STRUCTURAL_CONSTRAINTS_WITH_DRIVEN_INFLUENCE_EXCLUDED"){
    throw "Validation failed: wrong constraint snapshot mode"
}
if($status.constraint_driver_policy -ne "COMPARE_DRIVER_DEFINITION_NOT_EVALUATED_VALUE"){
    throw "Validation failed: wrong constraint driver policy"
}
if($status.constraint_change_count -ne 0){throw "Validation failed: constraints changed"}
if($status.constraint_structure_change_count -ne 0){throw "Validation failed: constraint structure changed"}
if($status.constraint_driver_change_count -ne 0){throw "Validation failed: constraint drivers changed"}
if($status.constraint_driver_count_before -ne 8){throw "Validation failed: expected eight rig drivers before retarget"}
if($status.constraint_driver_count_after -ne 8){throw "Validation failed: expected eight rig drivers after retarget"}
if($status.mesh_binding_change_count -ne 0){throw "Validation failed: bindings or weights changed"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected objects changed"}
if(-not $status.existing_actions_preserved){throw "Validation failed: existing actions were not preserved"}
if($status.active_action -ne "SACKBOY_JUMPSTYLE_RETARGET_V1"){throw "Validation failed: generated action is not active"}

Write-Host "=== AUTOMATED JUMPSTYLE MOCAP V1.3 VALIDATION PASS ==="
Write-Host "Source frames: $($status.source_frame_count)"
Write-Host "Source duration: $($status.source_duration_seconds) seconds"
Write-Host "Pose detection rate: $($processed.quality.detection_rate)"
Write-Host "Median key visibility: $($processed.quality.median_key_visibility)"
Write-Host "Longest missing gap: $($processed.quality.longest_missing_gap_frames) frames"
Write-Host "Calibration frame: $($status.calibration_frame)"
Write-Host "Target action: $($status.target_action)"
Write-Host "Target frame range: $($status.target_start_frame) to $($status.target_end_frame)"
Write-Host "Keyed controls: $($status.keyed_control_count)"
Write-Host "Keyed IK switches: $($status.keyed_switch_count)"
Write-Host "Action storage API: $($status.action_storage_api)"
Write-Host "Action layers: $($status.action_layer_count)"
Write-Host "Action slots: $($status.action_slot_count)"
Write-Host "Action channelbags: $($status.action_channelbag_count)"
Write-Host "F-curves: $($status.fcurve_count)"
Write-Host "Keyframe points: $($status.keyframe_point_count)"
Write-Host "Left contact segments: $($status.left_contact_segment_count)"
Write-Host "Right contact segments: $($status.right_contact_segment_count)"
Write-Host "Left locked-foot slide: $($status.left_contact_max_target_slide)"
Write-Host "Right locked-foot slide: $($status.right_contact_max_target_slide)"
Write-Host "Geometry checks: $($status.geometry_checks_passed)"
Write-Host "Rest-bone changes: $($status.rest_bone_change_count)"
Write-Host "Constraint snapshot mode: $($status.constraint_snapshot_mode)"
Write-Host "Constraint driver policy: $($status.constraint_driver_policy)"
Write-Host "Constraint changes: $($status.constraint_change_count)"
Write-Host "Constraint structure changes: $($status.constraint_structure_change_count)"
Write-Host "Constraint driver changes: $($status.constraint_driver_change_count)"
Write-Host "Constraint drivers before/after: $($status.constraint_driver_count_before) / $($status.constraint_driver_count_after)"
Write-Host "Binding changes: $($status.mesh_binding_change_count)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "Open Blender and play from frame $([math]::Floor($status.target_start_frame)) to $([math]::Ceiling($status.target_end_frame))."
Write-Host "Review the tracking overlay at motion\extracted\dance_reference_tracking_overlay_v1.mp4."
