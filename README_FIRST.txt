SACKBOY BLENDER STARTER

Recommended working folder:
C:\BlenderProjects\SackboyMusicVideo\

Do not keep the working project under Program Files.

1. Extract this bundle into the project folder.
2. Put your references at:
   reference\master_image.png
   reference\dance_reference.mp4
3. Open PowerShell in the project root.
4. Run:
   Set-ExecutionPolicy -Scope Process Bypass
   .\Run-BuildAll.ps1

This launches Blender headlessly and creates:
- rough Sackboy-style graybox
- parking lot / plaza graybox
- amber night lighting
- descending orbit camera
- low-angle camera
- blender\sackboy_scene.blend

Then open the .blend file normally and inspect it.

For test renders:
   .\Run-DiagnosticRenders.ps1

The first character is only a proportional blockout. Rigging and dance motion
should come after the silhouette and proportions are approved.
