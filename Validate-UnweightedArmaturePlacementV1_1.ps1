param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\unweighted_armature_placement_v1\UnweightedArmaturePlacementV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}

$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.armature_count_after -ne 1){throw "Validation failed: expected exactly one armature"}
if($status.armature_name -ne "SACKBOY_RIG_PLACEMENT_V1"){throw "Validation failed: wrong armature name"}
if($status.bone_count -ne 22){throw "Validation failed: expected 22 placement bones"}
if($status.character_mesh_change_count -ne 0){throw "Validation failed: character meshes changed"}
if($status.armature_modifier_count_after -ne 0){throw "Validation failed: Armature modifiers were added"}
if($status.parented_target_count_after -ne 0){throw "Validation failed: character targets were parented"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected scene objects changed"}

Write-Host "=== UNWEIGHTED ARMATURE PLACEMENT VALIDATION PASS ==="
Write-Host "Armature: $($status.armature_name)"
Write-Host "Bones: $($status.bone_count)"
Write-Host "Character mesh changes: $($status.character_mesh_change_count)"
Write-Host "Armature modifiers after: $($status.armature_modifier_count_after)"
Write-Host "Parented character targets after: $($status.parented_target_count_after)"
Write-Host "Protected changes: $($status.protected_change_count)"
Write-Host "This is placement-only; no weighting has occurred."
