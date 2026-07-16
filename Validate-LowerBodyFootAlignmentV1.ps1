param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\lower_body_foot_alignment_v1\LowerBodyFootAlignmentV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.armature_count_after -ne 1){throw "Validation failed: expected one armature"}
if($status.bone_count_after -ne 22){throw "Validation failed: bone count changed"}
if($status.changed_bone_count -ne 8){throw "Validation failed: expected 8 adjusted bones"}
if(-not $status.lower_body_geometry_checks_passed){throw "Validation failed: lower-body geometry checks failed"}
if($status.mesh_change_count -ne 0){throw "Validation failed: character meshes changed"}
if($status.armature_modifier_count_after -ne 0){throw "Validation failed: Armature modifiers exist"}
if($status.parented_target_count_after -ne 0){throw "Validation failed: character objects were parented"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected scene objects changed"}

Write-Host "=== LOWER-BODY / FOOT ALIGNMENT VALIDATION PASS ==="
Write-Host "Adjusted bones: $($status.changed_bone_count)"
Write-Host "Bone count: $($status.bone_count_after)"
Write-Host "Geometry checks: $($status.lower_body_geometry_checks_passed)"
Write-Host "Left foot center Z: $($status.world_landmarks.L.ankle.z)"
Write-Host "Right foot center Z: $($status.world_landmarks.R.ankle.z)"
Write-Host "Mesh changes: $($status.mesh_change_count)"
Write-Host "Armature modifiers: $($status.armature_modifier_count_after)"
Write-Host "Parented targets: $($status.parented_target_count_after)"
Write-Host "Protected changes: $($status.protected_change_count)"
