param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project")
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$statusPath=".\reports\rigging_readiness_audit_v1\RiggingReadinessAuditV1_status.json"
if(!(Test-Path $statusPath)){throw "Missing status JSON: $statusPath"}

$status = Get-Content $statusPath -Raw | ConvertFrom-Json
if($status.saved_blend){throw "Validation failed: saved_blend=true"}
if($status.created_backup_blend_files -ne 0){throw "Validation failed: backup blend files created"}
if(-not $status.summary){throw "Validation failed: summary missing"}
if(-not $status.rigging_candidates){throw "Validation failed: rigging candidates missing"}

Write-Host "=== RIGGING READINESS AUDIT VALIDATION PASS ==="
Write-Host "Blend: $($status.blend_file)"
Write-Host "Objects: $($status.summary.object_count)"
Write-Host "Meshes: $($status.summary.mesh_count)"
Write-Host "Armatures: $($status.summary.armature_count)"
Write-Host "Character candidates: $($status.summary.character_candidate_count)"
Write-Host "Clothing candidates: $($status.summary.clothing_candidate_count)"
Write-Host "Rig-ready candidates: $($status.summary.rig_ready_candidate_count)"
Write-Host "Shape keys: $($status.summary.shape_key_count)"
Write-Host "Actions: $($status.summary.action_count)"
Write-Host "Missing external files: $($status.summary.missing_external_file_count)"
Write-Host "No .blend save and no backup creation confirmed."
