$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BlenderExe = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$Blend = Join-Path $Root "blender\sackboy_scene.blend"
$Script = Join-Path $Root "blender\scripts\render_shots.py"

if (-not (Test-Path $BlenderExe)) { throw "Missing Blender: $BlenderExe" }
if (-not (Test-Path $Blend)) { throw "Run Run-BuildAll.ps1 first. Missing: $Blend" }
if (-not (Test-Path $Script)) { throw "Missing render script: $Script" }

& $BlenderExe --background $Blend --python-exit-code 1 --python $Script

if ($LASTEXITCODE -ne 0) {
    throw "Diagnostic render run failed with exit code $LASTEXITCODE"
}

Write-Host "Diagnostics written to renders\diagnostics"
