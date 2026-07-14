param([string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",[string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
$ErrorActionPreference="Stop"; Set-Location $ProjectRoot
Write-Host "=== HOOD SWEATER INTERSECTION SEAT V1K ==="
Write-Host "Purpose: target the hood-to-sweater intersection plus remaining armpit seam irregularities."
Write-Host "Rules: hoodie only; no Backups blend writes; no .blend1 staging; no colored tube overlays."
if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing .\blender\sackboy_scene.blend"}
if(!(Test-Path ".\blender\scripts\hood_sweater_intersection_seat_v1K.py")){throw "Missing hood_sweater_intersection_seat_v1K.py"}
$beforeBlendSize=(Get-Item ".\blender\sackboy_scene.blend").Length
$beforeBlendTime=(Get-Item ".\blender\sackboy_scene.blend").LastWriteTimeUtc
$beforeBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
& $BlenderExe --background ".\blender\sackboy_scene.blend" --python-exit-code 1 --python ".\blender\scripts\hood_sweater_intersection_seat_v1K.py"
if($LASTEXITCODE -ne 0){throw "Blender hood/sweater intersection seat v1K failed with exit code $LASTEXITCODE"}
$afterBlend=Get-Item ".\blender\sackboy_scene.blend"
$afterBackups=@(Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue).Count
if($afterBlend.LastWriteTimeUtc -eq $beforeBlendTime){throw "Safety stop: blend timestamp did not change; v1K did not save."}
if($afterBackups -ne $beforeBackups){throw "Safety stop: Backups folder blend-file count changed."}
$deltaKB=[math]::Round(($afterBlend.Length-$beforeBlendSize)/1KB,0)
Write-Host "=== HOOD SWEATER INTERSECTION SEAT V1K COMPLETE ==="
Write-Host "Reports: reports\hood_sweater_intersection_seat_v1K"
Write-Host "Renders: renders\current_review"
Write-Host "Blend saved successfully. Size delta (KB): $deltaKB"
Write-Host "No new Backups .blend files detected."
