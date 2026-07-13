$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"
$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$BackupRoot=Join-Path $Root ("Backups\CollectionVisibilityFixRetryPush-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

foreach($Item in @($Scripts,$PatchScripts,$Blend,$BlenderExe)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CollectionVisibilityFixRetryPush.blend") -Force
Copy-Item (Join-Path $PatchScripts "collection_visibility_fix_retry_push_v1.py") (Join-Path $Scripts "collection_visibility_fix_retry_push_v1.py") -Force

Write-Host "[CollectionVisibilityFixRetryPush] Fixing hidden-review collection visibility..."
& $BlenderExe --background $Blend --python-exit-code 1 --python (Join-Path $Scripts "collection_visibility_fix_retry_push_v1.py")
if($LASTEXITCODE -ne 0){throw "Collection visibility fix failed."}

$Expected=@(
"reports\collection_visibility_fix_retry_push_v1\Collection_Visibility_Fix_Retry_Push_v1.md",
"reports\collection_visibility_fix_retry_push_v1\CollectionVisibilityFixRetryPush_report.txt",
"reports\collection_visibility_fix_retry_push_v1\CollectionVisibilityFixRetryPush_status.json",
"reports\collection_visibility_fix_retry_push_v1\collection_visibility_fix_retry_push_v1.json"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){Remove-Item $PatchDir -Recurse -Force}

Write-Host ""
Write-Host "=== COLLECTION VISIBILITY FIX PASS ==="
Write-Host "No objects were deleted."
Write-Host "Hidden review collection was made hidden/render-disabled again."
Write-Host "Backup: $BackupRoot"
