$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$Script=Join-Path $Root "patch\blender\scripts\current_baseline_annotation_v1.py"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

foreach($Item in @($Blend,$Script,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

Write-Host "[CurrentBaselineAnnotation] Audit/render/report only."
Write-Host "[CurrentBaselineAnnotation] This will clean current_review images, render fresh views, and write reports."
Write-Host "[CurrentBaselineAnnotation] It will NOT save or edit the blend."
& $BlenderExe --background $Blend --python-exit-code 1 --python $Script
if($LASTEXITCODE -ne 0){throw "Current baseline annotation failed."}

$Expected=@(
"renders\current_review\01_CurrentSceneWide_SOLID.png",
"renders\current_review\02_CurrentSceneWide_RENDERED.png",
"renders\current_review\03_CurrentCharacterThreeQuarter_SOLID.png",
"renders\current_review\04_CurrentCharacterThreeQuarter_RENDERED.png",
"renders\current_review\05_CurrentHoodFront_SOLID.png",
"renders\current_review\06_CurrentHoodLeftSide_SOLID.png",
"renders\current_review\07_CurrentHoodRightSide_SOLID.png",
"reports\current_baseline_annotation_v1\Current_Baseline_Annotation_v1.md",
"reports\current_baseline_annotation_v1\CurrentBaselineAnnotation_report.txt",
"reports\current_baseline_annotation_v1\CurrentBaselineAnnotation_status.json",
"reports\current_baseline_annotation_v1\current_baseline_annotation_v1.json",
"reports\current_baseline_annotation_v1\visible_objects.csv",
"reports\current_baseline_annotation_v1\hoodie_candidates.csv",
"reports\current_baseline_annotation_v1\clothing_candidates.csv",
"reports\current_baseline_annotation_v1\character_candidates.csv"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== CURRENT BASELINE ANNOTATION PASS ==="
Write-Host "Fresh current_review renders created."
Write-Host "Reports written under reports\current_baseline_annotation_v1."
Write-Host "No objects were edited, deleted, moved, renamed, hidden/unhidden, or saved."
