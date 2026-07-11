$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Expected=@(
"renders\character_wardrobe_prep_v1\01_CharacterWardrobeFront.png",
"renders\character_wardrobe_prep_v1\02_ShoeCloseup.png",
"renders\character_wardrobe_prep_v1\03_WardrobeSceneContext.png",
"renders\character_wardrobe_prep_v1\CharacterWardrobePrep_status.json",
"renders\character_wardrobe_prep_v1\CharacterWardrobePrep_report.txt",
"renders\current_review\01_CharacterWardrobeFront.png"
)
foreach($Rel in $Expected){
    if(-not(Test-Path (Join-Path $Root $Rel))){throw "Missing expected output: $Rel"}
}
Write-Host "=== CHARACTER WARDROBE PREP VALIDATION PASS ==="
