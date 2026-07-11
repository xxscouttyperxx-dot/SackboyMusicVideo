$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BlenderExe = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$Script = Join-Path $Root "blender\scripts\build_all.py"

if (-not (Test-Path $BlenderExe)) { throw "Missing Blender: $BlenderExe" }
if (-not (Test-Path $Script)) { throw "Missing build script: $Script" }

& $BlenderExe --background --python-exit-code 1 --python $Script

if ($LASTEXITCODE -ne 0) {
    throw "Blender build failed with exit code $LASTEXITCODE"
}

Write-Host "Build complete. Open blender\sackboy_scene.blend"
