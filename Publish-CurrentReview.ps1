$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function GitAddExistingOrDeleted {
    param([string[]]$Paths)
    foreach($Rel in $Paths){
        $Full = Join-Path $Root $Rel
        if(Test-Path $Full){
            git -C $Root add -A -- $Rel
            if($LASTEXITCODE -ne 0){throw "git add failed: $Rel"}
        } else {
            $Tracked = git -C $Root ls-files -- $Rel
            if(-not [string]::IsNullOrWhiteSpace($Tracked)){
                git -C $Root add -A -- $Rel
                if($LASTEXITCODE -ne 0){throw "git add failed deleted: $Rel"}
            }
        }
    }
}

Write-Host "[Publish] Cleaning stale package files..."
$Keep=@("Apply-ParkingHeightUnderglowRepair.ps1","Validate-ParkingHeightUnderglowRepair.ps1","Publish-CurrentReview.ps1","README-ParkingHeightUnderglowRepair.txt","README_FIRST.txt","Run-BuildAll.ps1","Run-DiagnosticRenders.ps1")
$Patterns=@("Apply-*.ps1","Validate-*.ps1","README-*.txt")
foreach($Pattern in $Patterns){
    Get-ChildItem -Path $Root -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { ($Keep -notcontains $_.Name) -and ($_.Name -notin @('Publish-CurrentReview.ps1','Clean-PackageRoot.ps1')) } |
        Remove-Item -Force
}

GitAddExistingOrDeleted @(
    ".gitignore",
    ".gitattributes",
    "blender\sackboy_scene.blend",
    "blender\sackboy_scene.blend1",
    "blender\scripts",
    "blender\assets",
    "NightSkyHDRI003_1K",
    "scene_manifest.json",
    "reports\project_workflow_audit",
    "reports\parking_height_underglow_repair_v1",
    "reports\parking_texture_decal_fit_prep_v1",
    "renders\current_review",
    "Apply-ParkingHeightUnderglowRepair.ps1",
    "Validate-ParkingHeightUnderglowRepair.ps1",
    "Publish-CurrentReview.ps1",
    "README-ParkingHeightUnderglowRepair.txt",
    "Apply-ParkingTextureDecalFitPrep.ps1",
    "Validate-ParkingTextureDecalFitPrep.ps1",
    "README-ParkingTextureDecalFitPrep.txt"
)

git -C $Root status --short
$Status = git -C $Root status --porcelain
if([string]::IsNullOrWhiteSpace($Status)){
    Write-Host "[Publish] Nothing to commit."
} else {
    git -C $Root commit -m "Repair parking height and restore underglow"
    if($LASTEXITCODE -ne 0){throw "git commit failed"}
}
git -C $Root push origin main
if($LASTEXITCODE -ne 0){throw "git push failed"}
Write-Host "[Publish] Done."
