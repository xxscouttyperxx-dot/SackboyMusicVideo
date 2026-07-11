$ErrorActionPreference="Stop"

$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Scripts=Join-Path $Root "blender\scripts"
$PatchScripts=Join-Path $Root "patch\blender\scripts"
$BackupRoot=Join-Path $Root ("Backups\CleanupReset-"+(Get-Date -Format "yyyyMMdd-HHmmss"))

$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$Blend=Join-Path $Root "blender\sackboy_scene.blend"

foreach($Item in @($BlenderExe,$Blend,$Scripts)){
    if(-not(Test-Path $Item)){throw "Required item missing: $Item"}
}

New-Item -ItemType Directory -Force -Path $BackupRoot|Out-Null
Copy-Item $Blend (Join-Path $BackupRoot "sackboy_scene_before_CleanupReset.blend") -Force

$Name="cleanup_reset_scene.py"
$Src=Join-Path $PatchScripts $Name
$Dst=Join-Path $Scripts $Name
Copy-Item $Src $Dst -Force

Write-Host "[CleanupReset] Cleaning Blender scene and rebuilding minimal diagnostics..."
& $BlenderExe --background $Blend --python-exit-code 1 --python $Dst
if($LASTEXITCODE -ne 0){throw "Blender cleanup/reset failed."}

# Root package-file cleanup.
Write-Host "[CleanupReset] Removing obsolete root-level package scripts/readmes..."
$KeepNames=@(
    "Apply-ProjectCleanupReset.ps1",
    "Validate-ProjectCleanupReset.ps1",
    "README-ProjectCleanupReset.txt",
    "README_FIRST.txt",
    "Run-BuildAll.ps1",
    "Run-DiagnosticRenders.ps1"
)

$Patterns=@(
    "Apply-Step*.ps1",
    "Validate-Step*.ps1",
    "README-Step*.txt",
    "Apply-ProductionPreview.ps1",
    "Validate-ProductionPreview.ps1",
    "README-ProductionPreview.txt",
    "Archive-ProjectPackageClutter.ps1"
)

foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object {$KeepNames -notcontains $_.Name} |
        Remove-Item -Force
}

# Remove accumulated patch staging area after scripts have been installed.
$PatchDir=Join-Path $Root "patch"
if(Test-Path $PatchDir){
    Remove-Item $PatchDir -Recurse -Force
}

# Keep only newest 3 backup directories; delete older backup directories.
$BackupsDir=Join-Path $Root "Backups"
if(Test-Path $BackupsDir){
    $Dirs=Get-ChildItem $BackupsDir -Directory | Sort-Object LastWriteTime -Descending
    $Old=$Dirs | Select-Object -Skip 3
    foreach($Dir in $Old){
        Remove-Item $Dir.FullName -Recurse -Force
    }
}

$Expected=@(
"renders\cleanup_reset_validation\01_Clean_Hero.png",
"renders\cleanup_reset_validation\02_Clean_Low.png",
"renders\cleanup_reset_validation\03_Clean_Orbit.png",
"renders\cleanup_reset_validation\CleanupReset_inventory.txt"
)

foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}

Write-Host ""
Write-Host "=== PROJECT CLEANUP RESET PASS ==="
Write-Host "Removed integrated preview and diagnostic clutter from Blender scene."
Write-Host "Kept F2 baseline, J2B best hand branch, and original source collection."
Write-Host "Reduced lights to exactly two amber area lights."
Write-Host "Reduced cameras to exactly three final cameras plus one orbit helper."
Write-Host "Applied warm brown yarn material to retained character branches."
Write-Host "Deleted obsolete root package scripts/readmes."
Write-Host "Deleted older backups, keeping the newest three."
Write-Host "Backups: $BackupRoot"
