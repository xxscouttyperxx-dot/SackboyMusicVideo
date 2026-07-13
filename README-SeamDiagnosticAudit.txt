SEAM DIAGNOSTIC AUDIT V1

Purpose:
- Diagnose known seam break zones before any repair:
  1. Left armpit seam
  2. Right armpit seam
  3. Hood-to-sweater/collar attachment seam
  4. Top-center hood seam

Safety:
- No mesh repair.
- No smoothing.
- No shrinkwrap.
- No object deletion other than previous SEAMDIAG_* cameras and TMP_SEAMDIAG_* temporary objects.
- Temporary boundary overlays are rendered and removed before save.
- Blend is saved locally only so seam cameras remain available.
- Main publish pushes reports/renders/scripts only, not the blend.

Main flow:
.\Apply-SeamDiagnosticAudit.ps1
.\Validate-SeamDiagnosticAudit.ps1
.\Publish-ReportsOnly.ps1

Optional blend-only push:
.\Try-PushBlendOnly.ps1
