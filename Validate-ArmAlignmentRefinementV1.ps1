param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\arm_alignment_refinement_v1\ArmAlignmentRefinementV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}
$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.armature_count_after -ne 1){throw "Validation failed: expected one armature"}
if($status.bone_count_after -ne 22){throw "Validation failed: bone count changed"}
if($status.changed_bone_count -ne 8){throw "Validation failed: expected 8 adjusted arm bones"}
if($status.mesh_change_count -ne 0){throw "Validation failed: character mesh data changed"}
if($status.armature_modifier_count_after -ne 0){throw "Validation failed: Armature modifiers exist"}
if($status.parented_target_count_after -ne 0){throw "Validation failed: character objects were parented"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected scene objects changed"}

Write-Host "=== ARM ALIGNMENT REFINEMENT VALIDATION PASS ==="
Write-Host "Adjusted bones: $($status.changed_bone_count)"
Write-Host "Bone count: $($status.bone_count_after)"
Write-Host "Mesh changes: $($status.mesh_change_count)"
Write-Host "Armature modifiers: $($status.armature_modifier_count_after)"
Write-Host "Parented character targets: $($status.parented_target_count_after)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "Review the arms visually before the binding stage."
