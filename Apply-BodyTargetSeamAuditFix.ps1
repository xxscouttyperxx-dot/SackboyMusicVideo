$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$Script=Join-Path $Root "patch\blender\scripts\body_target_seam_audit_fix_v1B.py"
$Scripts=Join-Path $Root "blender\scripts"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\BodyTargetSeamAuditFix-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Blend,$Script,$BlenderExe,$Scripts)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_BodyTargetSeamAuditFix.blend") -Force
Copy-Item $Script (Join-Path $Scripts "body_target_seam_audit_fix_v1B.py") -Force

Write-Host "[BodyTargetSeamAuditFix] Running corrected body-target seam audit..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "body_target_seam_audit_fix_v1B.py")
if($LASTEXITCODE -ne 0){throw "Body target seam audit fix failed."}

$Expected=@(
"renders\current_review\01_V1B_FullContext_SeamOverlay.png",
"renders\current_review\02_V1B_LeftArmpit_SeamOverlay.png",
"renders\current_review\03_V1B_RightArmpit_SeamOverlay.png",
"renders\current_review\04_V1B_HoodCollar_SeamOverlay.png",
"renders\current_review\05_V1B_HoodTop_SeamOverlay.png",
"reports\body_target_seam_audit_fix_v1B\Body_Target_Seam_Audit_Fix_v1B.md",
"reports\body_target_seam_audit_fix_v1B\BodyTargetSeamAuditFix_status.json",
"reports\body_target_seam_audit_fix_v1B\body_target_seam_audit_fix_v1B.json",
"reports\body_target_seam_audit_fix_v1B\targeted_mesh_exports\current_body_F2.obj"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}
Write-Host ""
Write-Host "=== BODY TARGET + SEAM AUDIT FIX V1B PASS ==="
Write-Host "Corrected body target export should now be F2."
Write-Host "Reports/renders/OBJ exports written under reports\body_target_seam_audit_fix_v1B."
Write-Host "Backup: $BackupRoot"
