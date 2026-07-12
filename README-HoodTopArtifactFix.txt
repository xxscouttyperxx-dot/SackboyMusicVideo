HOOD TOP ARTIFACT FIX V1

This is a focused hoodie-only corrective pass.

It:
- only focuses on the hood-top artifact and hood rim clearance
- keeps F2 visually restored/baseline
- keeps all F2 BODYFIT shape keys disabled
- creates a new hoodie-only shape key: HOODIEFIT_TopArtifactFix_v1
- uses F2's head top and XY head footprint as a stronger clearance reference
- lifts/domes the hood top over the head to reduce red/show-through artifact
- keeps the hood rim vertically open
- feathers the slope below the lifted top to avoid banding
- updates cameras so 3 focus on the hood artifact/rim and 1 checks scene preservation
- preserves reflections, traffic lights, car, underglow, asphalt, parking strips, sky/HDRI, and approved lighting

Run:
cd "C:\BlenderProjects\SackboyMusicVideo\Project"
Remove-Item ".\patch" -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path "$env:USERPROFILE\Downloads\Sackboy_Blender_HoodTopArtifactFix_v1.zip" -DestinationPath "C:\BlenderProjects\SackboyMusicVideo\Project" -Force
Set-ExecutionPolicy -Scope Process Bypass
Unblock-File .\Apply-HoodTopArtifactFix.ps1
.\Apply-HoodTopArtifactFix.ps1
.\Validate-HoodTopArtifactFix.ps1
.\Publish-CurrentReview.ps1
