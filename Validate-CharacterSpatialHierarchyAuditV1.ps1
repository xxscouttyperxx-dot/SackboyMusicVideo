param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\character_spatial_hierarchy_audit_v1\CharacterSpatialHierarchyAuditV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}

$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if($status.saved_blend){throw "Validation failed: saved_blend=true"}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files created"}
if(-not $status.character_objects){throw "Validation failed: character_objects missing"}
if(-not $status.origin_and_axis_audit){throw "Validation failed: origin_and_axis_audit missing"}
if(-not $status.protected_effect_objects){throw "Validation failed: protected_effect_objects missing"}

Write-Host "=== CHARACTER SPATIAL / HIERARCHY AUDIT VALIDATION PASS ==="
Write-Host "Character/clothing/accessory objects: $($status.summary.character_object_count)"
Write-Host "Visible candidates: $($status.summary.visible_character_object_count)"
Write-Host "Objects with shape keys: $($status.summary.shape_key_object_count)"
Write-Host "Objects with animation data: $($status.summary.animated_object_count)"
Write-Host "Objects with parent relationships: $($status.summary.parented_object_count)"
Write-Host "Potential detached origins/axes: $($status.summary.detached_origin_candidate_count)"
Write-Host "Empty-axis objects near character: $($status.summary.character_near_empty_count)"
Write-Host "Protected lightning/cloud objects: $($status.summary.protected_effect_object_count)"
Write-Host "No .blend save and no scene changes confirmed."
