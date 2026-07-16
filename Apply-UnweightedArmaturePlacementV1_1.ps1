param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

Write-Host "=== UNWEIGHTED ARMATURE PLACEMENT V1.1 ==="
Write-Host "Creates an unweighted custom Sackboy armature only."
Write-Host "No parenting, no skin weights, no Armature modifiers, and no character mesh edits."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\unweighted_armature_placement_v1.py")){throw "Missing Blender script"}

$beforeBackups = @(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\unweighted_armature_placement_v1.py"
if($LASTEXITCODE -ne 0){throw "Blender armature placement failed with exit code $LASTEXITCODE"}

$afterBackups = @(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Blend saved: blender\sackboy_scene.blend"
Write-Host "Armature: SACKBOY_RIG_PLACEMENT_V1"
Write-Host "Collection: RIGGING_PREVIEW"
Write-Host "No meshes were bound or weighted."
