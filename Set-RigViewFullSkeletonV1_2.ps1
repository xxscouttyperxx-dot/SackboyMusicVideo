param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot
$ScriptPath=".\blender\scripts\rig_view_mode_v1_2.py"
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path $ScriptPath)){throw "Missing rig view script: $ScriptPath"}
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python $ScriptPath -- --mode full
if($LASTEXITCODE -ne 0){throw "Full-skeleton rig view failed"}
Write-Host "Full-skeleton rig view saved."
