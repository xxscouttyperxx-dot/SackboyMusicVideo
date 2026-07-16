param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\clean_animation_baseline_v1\CleanAnimationBaselineV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}

$status=Get-Content $statusPath -Raw | ConvertFrom-Json

if(-not $status.saved_blend){throw "Validation failed: saved_blend=false"}
if($status.armatures_after -ne 0){throw "Validation failed: an armature exists after baseline cleanup"}
if($status.f2_shape_keys_after -ne 0){throw "Validation failed: F2 still has shape keys"}
if(-not $status.shoes_empty_removed){throw "Validation failed: Shoes Empty was not removed"}
if($status.max_visual_world_error -gt 0.00001){throw "Validation failed: visual world error exceeds tolerance"}
if($status.protected_change_count -ne 0){throw "Validation failed: protected objects changed"}
if($status.target_animation_data_after -ne 0){throw "Validation failed: target animation data remains"}

Write-Host "=== CLEAN ANIMATION BASELINE VALIDATION PASS ==="
Write-Host "F2 shape keys before: $($status.f2_shape_keys_before)"
Write-Host "F2 shape keys after: $($status.f2_shape_keys_after)"
Write-Host "Origins normalized: $($status.origins_normalized_count)"
Write-Host "Shoes Empty removed: $($status.shoes_empty_removed)"
Write-Host "Character animation-data blocks cleared: $($status.target_animation_data_cleared)"
Write-Host "Maximum visual world error: $($status.max_visual_world_error)"
Write-Host "Protected object changes: $($status.protected_change_count)"
Write-Host "Armatures after: $($status.armatures_after)"
