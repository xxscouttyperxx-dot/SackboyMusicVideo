param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

Write-Host "=== SACKBOY ARM ALIGNMENT FINALIZATION V2 ==="
Write-Host "Replaces the failed M/V arm placement with straight centerline arm chains."
Write-Host "No parenting, weighting, IK, posing, animation, or mesh edits."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\arm_alignment_finalization_v2.py")){throw "Missing Blender script"}

$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\arm_alignment_finalization_v2.py"
if($LASTEXITCODE -ne 0){throw "Blender arm-alignment finalization failed with exit code $LASTEXITCODE"}

$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Straight arm chains finalized and blend saved."
Write-Host "No meshes were bound or weighted."
