param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$PreflightPath=".\blender\scripts\preflight_dressed_rig_controls_v1_8.py"
$ScriptPath=".\blender\scripts\dressed_rig_controls_v1_8.py"

Write-Host "=== SACKBOY DRESSED RIG REVIEW + CONTROLS V1.8 ==="
Write-Host "Uses semantic Python AST validation instead of brittle whole-file text matching."
Write-Host "The project blend opens only after all three Blender preflight checks pass."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path $PreflightPath)){throw "Missing Blender preflight: $PreflightPath"}
if(!(Test-Path $ScriptPath)){throw "Missing production Blender script: $ScriptPath"}

$preflightText=Get-Content $PreflightPath -Raw
$scriptText=Get-Content $ScriptPath -Raw

if($preflightText -notmatch 'SCRIPT_VERSION="1\.8"'){
    throw "Safety stop: v1.8 preflight identity marker was not found."
}
if($scriptText -notmatch 'SCRIPT_VERSION="1\.8"'){
    throw "Safety stop: v1.8 production identity marker was not found."
}
if($preflightText -notmatch 'static_binding_ast_check'){
    throw "Safety stop: semantic binding AST check marker was not found."
}
if($preflightText -notmatch 'action_switch_regression'){
    throw "Safety stop: action-switch regression marker was not found."
}
if($scriptText -notmatch 'MeshBindingDiagnosticV1_8\.json'){
    throw "Safety stop: final binding diagnostic marker was not found."
}

Write-Host "Verified v1.8 file identities and required regression markers."
Write-Host "Running Blender semantic/static and runtime preflight tests..."

& $BlenderExe --background --factory-startup --python-exit-code 1 --python $PreflightPath
if($LASTEXITCODE -ne 0){throw "Blender regression preflight failed with exit code $LASTEXITCODE"}

Write-Host "All Blender preflight tests passed."
Write-Host "Opening the project and applying Stage 9-11 work..."

$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count

& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python $ScriptPath
if($LASTEXITCODE -ne 0){throw "Blender dressed-rig/control build failed with exit code $LASTEXITCODE"}

$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups .blend count changed."}

Write-Host "=== APPLY COMPLETE ==="
Write-Host "Stage 9 dressed review completed."
Write-Host "Stage 10 control rig created."
Write-Host "Stage 11 action: SACKBOY_CONTROL_RIG_VALIDATION_V1"
