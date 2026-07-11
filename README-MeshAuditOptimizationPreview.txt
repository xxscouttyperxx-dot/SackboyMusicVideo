Sackboy Blender Mesh Audit / Optimization Preview v1
===================================================

Purpose
-------
This pass does two things:
1) audits imported clothing/prop meshes so we can identify high-poly optimization candidates before any automatic decimation pass;
2) adds preview snap modifiers so the parking paint strips sit on the asphalt more cleanly.

This pass preserves the current baseline:
- do not move or alter the locked lights;
- do not alter the current car placement;
- do not alter the user-managed sky/HDRI;
- do not decimate or rebuild meshes automatically.

Outputs
-------
- renders/mesh_audit_optimization_preview_v1/
- reports/mesh_audit_optimization_preview/
- renders/current_review/
- scene_manifest.json
- reports/project_workflow_audit/

Suggested PowerShell sequence
-----------------------------
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_Mesh_Audit_Optimization_Preview_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-MeshAuditOptimizationPreview.ps1
.\Apply-MeshAuditOptimizationPreview.ps1
.\Validate-MeshAuditOptimizationPreview.ps1
.\Publish-CurrentReview.ps1
