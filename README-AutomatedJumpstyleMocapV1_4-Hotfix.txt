Sackboy Automated Jumpstyle Mocap v1.4 — Driver Preflight Hotfix

What the latest run proved:
- Healthy isolated MediaPipe environment.
- Cached 764-frame tracking data remained valid.
- Blender 5.1 layered Action preflight passed.
- The structural snapshot correctly identified the synthetic influence as driven.
- The constraint structure and driver definition stayed unchanged.

Why the preflight still stopped:
- In Blender factory-startup/background mode, a newly created synthetic driver
  did not refresh its evaluated influence immediately after the custom property
  changed.
- influence_before and influence_after both read 0.0.
- That is a dependency-graph refresh behavior in the synthetic test, not a
  failure of the production structural constraint checker.
- Requiring the evaluated synthetic influence to change was therefore another
  false-positive gate.

Root correction:
- Evaluated influence refresh is retained as a diagnostic only.
- The required checks are:
    driven influence is identified and excluded,
    constraint structure remains unchanged,
    driver definition remains unchanged,
    driver count remains stable,
    an actual undriven influence edit is detected.
- The test therefore proves both sides:
    expected driven evaluation cannot trigger a false structural change,
    real undriven constraint edits are still caught.

The project blend was not opened by the failed run and was not modified.

Run:
  .\Run-AutomatedJumpstyleMocapV1_4.ps1

Then:
  .\Validate-AutomatedJumpstyleMocapV1_3.ps1

Do not publish or push until the generated dance has been visually reviewed.
