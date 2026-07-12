$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\character_silhouette_refine_v1\01_SilhouetteFront.png",
"renders\character_silhouette_refine_v1\02_ProfileGutLegHand.png",
"renders\character_silhouette_refine_v1\03_FaceHandCheck.png",
"renders\character_silhouette_refine_v1\04_StorefrontReflectionCamera.png",
"renders\character_silhouette_refine_v1\CharacterSilhouetteRefine_report.txt",
"renders\character_silhouette_refine_v1\CharacterSilhouetteRefine_status.json",
"reports\character_silhouette_refine_v1\Character_Silhouette_Refine_v1.md",
"reports\character_silhouette_refine_v1\character_silhouette_refine_v1.json",
"renders\current_review\01_SilhouetteFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CHARACTER SILHOUETTE REFINE VALIDATION PASS ==="
