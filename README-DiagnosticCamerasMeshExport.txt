DIAGNOSTIC CAMERAS + MESH EXPORT V1

This package:
- deletes previous DIAG_CURRENT_* diagnostic cameras
- creates fresh DIAG_CURRENT_* cameras aimed at the current character/clothing
- cleans renders/current_review
- renders current diagnostic views
- exports targeted OBJ mesh diagnostics for current hoodie/body/clothing
- writes mesh boundary/open-edge/island diagnostics
- saves the blend locally so the diagnostic cameras are retained

It does NOT:
- edit mesh geometry
- repair seams yet
- change materials
- change lights/world/car/environment
- push the blend in the main publish step

Main flow:
.\Apply-DiagnosticCamerasMeshExport.ps1
.\Validate-DiagnosticCamerasMeshExport.ps1
.\Publish-ReportsOnly.ps1

Optional blend-only push:
.\Try-PushBlendOnly.ps1
