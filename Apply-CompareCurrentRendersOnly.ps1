$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$Script=Join-Path $Root "patch\blender\scripts\compare_current_renders_only_v1.py"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

foreach($Item in @($Blend,$Script,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

Write-Host "[CompareCurrentRendersOnly] Render-only pass."
Write-Host "[CompareCurrentRendersOnly] It will NOT delete old current_review files."
Write-Host "[CompareCurrentRendersOnly] It will NOT save the blend or edit objects."
& $BlenderExe --background $Blend --python-exit-code 1 --python $Script
if($LASTEXITCODE -ne 0){throw "Compare current renders only failed."}

$Expected=@(
"renders\current_review\COMPARE_NOW_01_SceneWide_SOLID.png",
"renders\current_review\COMPARE_NOW_02_SceneWide_RENDERED.png",
"renders\current_review\COMPARE_NOW_03_HoodCharacterFront_SOLID.png",
"renders\current_review\COMPARE_NOW_04_HoodCharacterFront_RENDERED.png",
"renders\current_review\COMPARE_NOW_05_CharacterThreeQuarter_SOLID.png",
"renders\current_review\COMPARE_NOW_06_CharacterThreeQuarter_RENDERED.png",
"reports\compare_current_renders_only_v1\CompareCurrentRendersOnly_report.txt",
"reports\compare_current_renders_only_v1\CompareCurrentRendersOnly_status.json",
"reports\compare_current_renders_only_v1\Compare_Current_Renders_Only_v1.md",
"reports\compare_current_renders_only_v1\compare_current_renders_only_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== COMPARE CURRENT RENDERS ONLY PASS ==="
Write-Host "Existing current_review images were kept."
Write-Host "New compare renders were added with COMPARE_NOW_ prefix."
Write-Host "No objects were changed."
Write-Host "The blend file was not saved."
