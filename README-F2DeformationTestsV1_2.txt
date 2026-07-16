Sackboy F2 Deformation Tests v1.2

Why v1.1 failed:
- The corrected Python file was present in the ZIP.
- The v1.1 PowerShell launcher still referenced f2_deformation_tests_v1.py.
- The traceback therefore showed and executed the old v1 script.

v1.2 safeguards:
- Runs only blender/scripts/f2_deformation_tests_v1_2.py.
- Verifies SCRIPT_VERSION="1.2" before Blender starts.
- Verifies the same-frame protected-object comparison fix exists.
- Uses a distinct action and report directory.
- Contains no stale Python bytecode.

Action:
- F2_DEFORMATION_TEST_V1_2

Inspection frames:
- 205 shoulders
- 215 elbows
- 225 wrists
- 235 squat
- 245 left jumpstyle kick
- 255 right jumpstyle kick
- 265 torso lean/twist
- 270 rest

Production frames 1-120 remain at rest.
Only F2 is bound; temporarily hide clothing, eyes, and shoes to inspect it.
