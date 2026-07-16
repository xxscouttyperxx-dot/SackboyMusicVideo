param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\arm_alignment_finalization_v2\ArmAlignmentFinalizationV2_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.armature_count_after -ne 1){throw "Validation failed: expected one armature"}
if($status.bone_count_after -ne 22){throw "Validation failed: bone count changed"}
if($status.changed_bone_count -ne 8){throw "Validation failed: expected 8 adjusted bones"}
if(-not $status.arm_chain_geometry_checks_passed){throw "Validation failed: arm-chain geometry checks failed"}
if($status.mesh_change_count -ne 0){throw "Validation failed: character meshes changed"}
if($status.armature_modifier_count_after -ne 0){throw "Validation failed: Armature modifiers exist"}
if($status.parented_target_count_after -ne 0){throw "Validation failed: character objects were parented"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected scene objects changed"}

Write-Host "=== ARM ALIGNMENT FINALIZATION V2 PASS ==="
Write-Host "Adjusted bones: $($status.changed_bone_count)"
Write-Host "Bone count: $($status.bone_count_after)"
Write-Host "Arm center height: $($status.arm_center_world.z)"
Write-Host "Arm center depth: $($status.arm_center_world.y)"
Write-Host "Straight-chain checks: $($status.arm_chain_geometry_checks_passed)"
Write-Host "Mesh changes: $($status.mesh_change_count)"
Write-Host "Armature modifiers: $($status.armature_modifier_count_after)"
Write-Host "Parented targets: $($status.parented_target_count_after)"
Write-Host "Protected changes: $($status.protected_change_count)"
