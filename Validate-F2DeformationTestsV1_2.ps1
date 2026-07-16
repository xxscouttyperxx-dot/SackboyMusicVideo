param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\f2_deformation_tests_v1_2\F2DeformationTestsV1_2_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if($status.script_version -ne "1.2"){throw "Validation failed: wrong script version"}
if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.action_name -ne "F2_DEFORMATION_TEST_V1_2"){throw "Validation failed: wrong action"}
if(-not $status.production_frames_rest_verified){throw "Validation failed: production frames are not rest"}
if(-not $status.all_pose_geometry_checks_passed){throw "Validation failed: a deformation pose failed geometry checks"}
if($status.armature_rest_change_count -ne 0){throw "Validation failed: armature rest bones changed"}
if($status.other_target_armature_modifier_count -ne 0){throw "Validation failed: non-F2 targets were bound"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected objects changed"}
if($status.scene_frame_start_changed -or $status.scene_frame_end_changed){throw "Validation failed: scene frame range changed"}

Write-Host "=== F2 DEFORMATION TESTS V1.2 VALIDATION PASS ==="
Write-Host "Script version: $($status.script_version)"
Write-Host "Action: $($status.action_name)"
Write-Host "Production frames rest: $($status.production_frames_rest_verified)"
Write-Host "Pose checks: $($status.all_pose_geometry_checks_passed)"
Write-Host "Test poses: $($status.test_pose_count)"
Write-Host "Rest-bone changes: $($status.armature_rest_change_count)"
Write-Host "Other targets bound: $($status.other_target_armature_modifier_count)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "Inspect frames 205, 215, 225, 235, 245, 255, 265, and 270."
