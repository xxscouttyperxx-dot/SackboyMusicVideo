param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",[string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== ARMPIT COLLAR SHAPE SEAT V1L ==="
Write-Host "Purpose: reversible shape-key seating for armpit irregularities and hood/sweater intersection."
Write-Host "Rules: hoodie only; no Backups blend writes; no .blend1 staging; no topology changes."
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\armpit_collar_shape_seat_v1L.py")){throw "Missing armpit_collar_shape_seat_v1L.py"}
$beforeBlendSize=(Get-Item ".\blender\sackboy_scene.blend").Length
$beforeBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\armpit_collar_shape_seat_v1L.py"
if($LASTEXITCODE -ne 0){throw "Blender armpit/collar shape seat v1L failed with exit code $LASTEXITCODE"}
$afterBlend=Get-Item ".\blender\sackboy_scene.blend"
$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBlend.LastWriteTimeUtc -eq $beforeBlendTime){throw "Safety stop: blend timestamp did not change; v1L did not save."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups folder blend-file count changed."}
$deltaKB=[math]::Round(($afterBlend.Length-$beforeBlendSize)/1KB,0)
Write-Host "=== ARMPIT COLLAR SHAPE SEAT V1L COMPLETE ==="
Write-Host "Reports: reports\armpit_collar_shape_seat_v1L"
Write-Host "Renders: renders\current_review"
Write-Host "Blend saved successfully. Size delta (KB): $deltaKB"
Write-Host "No new Backups .blend files detected."
