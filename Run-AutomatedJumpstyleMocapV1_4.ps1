param(
    [string]$ProjectRoot="C:\BlenderProjects\SackboyMusicVideo\Project",
    [string]$BlenderExe="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)
$ErrorActionPreference="Stop"
Set-Location $ProjectRoot

$EnvDir=".\Tools\jumpstyle-mocap-env"
$EnvPython=Join-Path $EnvDir "Scripts\python.exe"
$VideoPath=".\motion\reference\dance_reference.mp4"
$AnalysisPath=".\motion\reference\SourceVideoAnalysisV1.json"
$RawPath=".\motion\extracted\dance_reference_pose_raw_v1.json"
$ProcessedPath=".\motion\extracted\dance_reference_pose_processed_v1.json"
$OverlayPath=".\motion\extracted\dance_reference_tracking_overlay_v1.mp4"
$PoseReport=".\reports\jumpstyle_mocap_v1\PoseExtractionV1_report.txt"

$SelfTest=".\tools\mocap\pose_pipeline_selftest_v1.py"
$Extractor=".\tools\mocap\extract_pose_landmarks_v1.py"
$Processor=".\tools\mocap\process_pose_landmarks_v1.py"
$CacheValidator=".\tools\mocap\validate_pose_cache_v1.py"
$BlenderPreflight=".\blender\scripts\preflight_jumpstyle_retarget_v1_3.py"
$BlenderApply=".\blender\scripts\apply_jumpstyle_retarget_v1_3.py"

Write-Host "=== SACKBOY AUTOMATED JUMPSTYLE MOCAP V1.4 ==="
Write-Host "No manual posing: local MediaPipe extraction, smoothing, foot contacts, and Blender retargeting."
Write-Host "Python discovery, layered-Action, driven-constraint, and robust preflight hotfixes enabled."

if(!(Test-Path $BlenderExe)){throw "Blender not found: $BlenderExe"}
if(!(Test-Path ".\blender\sackboy_scene.blend")){throw "Missing blender\sackboy_scene.blend"}
foreach($path in @($VideoPath,$AnalysisPath,$SelfTest,$Extractor,$Processor,$CacheValidator,$BlenderPreflight,$BlenderApply)){
    if(!(Test-Path $path)){throw "Missing required package file: $path"}
}

function Invoke-NativeProbe {
    param(
        [string]$Exe,
        [string[]]$Arguments
    )

    if([string]::IsNullOrWhiteSpace($Exe)){return $null}
    if(!(Test-Path $Exe)){return $null}

    $oldPreference=$ErrorActionPreference
    try{
        # Native programs may legitimately write diagnostics to stderr.
        # Probe failures must not terminate the entire PowerShell script.
        $ErrorActionPreference="Continue"
        $output=& $Exe @Arguments 2>$null
        $exitCode=$LASTEXITCODE
    }catch{
        return $null
    }finally{
        $ErrorActionPreference=$oldPreference
    }

    if($exitCode -ne 0 -or -not $output){return $null}
    return (($output | Select-Object -Last 1).ToString().Trim())
}

function Invoke-NativeRequired {
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$FailureMessage
    )

    if(!(Test-Path $Exe)){throw "Executable not found: $Exe"}

    $oldPreference=$ErrorActionPreference
    try{
        # Prevent harmless native stderr output from becoming a terminating
        # NativeCommandError under Windows PowerShell 5.1.
        $ErrorActionPreference="Continue"
        & $Exe @Arguments
        $exitCode=$LASTEXITCODE
    }finally{
        $ErrorActionPreference=$oldPreference
    }

    if($exitCode -ne 0){
        throw "$FailureMessage (exit code $exitCode)"
    }
}

function Test-PythonCandidate {
    param([string]$Path)

    if([string]::IsNullOrWhiteSpace($Path)){return $null}
    if($Path -like "*\WindowsApps\python.exe"){return $null}

    $probe=Invoke-NativeProbe -Exe $Path -Arguments @(
        "-c",
        "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{sys.version_info.major}{sys.version_info.minor}|{sys.executable}')"
    )
    if(-not $probe){return $null}

    $parts=$probe -split "\|",3
    if($parts.Count -ne 3){return $null}
    if($parts[0] -notin @("3.10","3.11","3.12")){return $null}

    return [PSCustomObject]@{
        Path=$parts[2]
        Version=$parts[0]
        WheelTag=$parts[1]
    }
}

function Add-PythonCandidate {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Path
    )
    if([string]::IsNullOrWhiteSpace($Path)){return}
    if(-not $List.Contains($Path)){
        $List.Add($Path)
    }
}

function Resolve-BasePython {
    $candidates=New-Object "System.Collections.Generic.List[string]"

    # Prefer the user's known working ScoutAI environment before consulting
    # Windows' py launcher, which may contain stale registrations.
    Add-PythonCandidate -List $candidates -Path "C:\LLM\llm-env\Scripts\python.exe"

    foreach($candidate in @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python312\python.exe"
    )){
        Add-PythonCandidate -List $candidates -Path $candidate
    }

    # Read registered Python install paths directly. A stale py.exe mapping is
    # therefore not required for discovery.
    foreach($registryRoot in @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )){
        if(!(Test-Path $registryRoot)){continue}

        foreach($versionKey in Get-ChildItem $registryRoot -ErrorAction SilentlyContinue){
            $installKey=Join-Path $versionKey.PSPath "InstallPath"
            if(!(Test-Path $installKey)){continue}

            try{
                $key=Get-Item $installKey -ErrorAction Stop
                $registeredExe=$key.GetValue("ExecutablePath")
                $installDirectory=$key.GetValue("")

                if($registeredExe){
                    Add-PythonCandidate -List $candidates -Path ([string]$registeredExe)
                }elseif($installDirectory){
                    Add-PythonCandidate -List $candidates -Path (
                        Join-Path ([string]$installDirectory) "python.exe"
                    )
                }
            }catch{
                # An unreadable registry entry is skipped.
            }
        }
    }

    # Add directly resolvable python commands, excluding Microsoft Store aliases.
    foreach($command in Get-Command python.exe -All -ErrorAction SilentlyContinue){
        Add-PythonCandidate -List $candidates -Path $command.Source
    }

    foreach($candidate in $candidates){
        $info=Test-PythonCandidate -Path $candidate
        if($info){
            Write-Host "Selected Python $($info.Version): $($info.Path)"
            return $info
        }
        if(Test-Path $candidate){
            Write-Host "Skipping unusable Python candidate: $candidate"
        }
    }

    # py.exe is deliberately the final fallback. Its failures are contained by
    # Invoke-NativeProbe and cannot terminate the script.
    $pyCommand=Get-Command py.exe -ErrorAction SilentlyContinue
    if($pyCommand){
        foreach($selector in @("-3.11","-3.10","-3.12")){
            $resolved=Invoke-NativeProbe -Exe $pyCommand.Source -Arguments @(
                $selector,
                "-c",
                "import sys; print(sys.executable)"
            )
            if(-not $resolved){continue}

            $info=Test-PythonCandidate -Path $resolved
            if($info){
                Write-Host "Selected Python $($info.Version) through py.exe: $($info.Path)"
                return $info
            }
        }
        Write-Host "Ignoring py.exe because its registered interpreters are unavailable."
    }

    throw @"
Python 3.10, 3.11, or 3.12 was not found.
Checked the ScoutAI environment, standard install folders, Windows registry,
direct python.exe commands, and finally py.exe.
A stale py.exe registration will no longer crash this script.
"@
}

function Test-MocapEnvironment {
    param([string]$PythonPath)

    $probe=Invoke-NativeProbe -Exe $PythonPath -Arguments @(
        "-c",
        "import sys, mediapipe, cv2, scipy, numpy; assert mediapipe.__version__ == '0.10.18'; assert sys.version_info[:2] in ((3,10),(3,11),(3,12)); print('MOCAP_ENV_OK')"
    )
    return $probe -eq "MOCAP_ENV_OK"
}

if(Test-Path $EnvPython){
    if(Test-MocapEnvironment -PythonPath $EnvPython){
        Write-Host "Using healthy isolated mocap environment: $EnvPython"
    }else{
        Write-Host "Existing mocap environment is incomplete or incompatible; rebuilding it safely."
        Remove-Item $EnvDir -Recurse -Force
    }
}

if(!(Test-Path $EnvPython)){
    $baseInfo=Resolve-BasePython
    $BasePython=$baseInfo.Path
    $BaseVersion=$baseInfo.WheelTag

    Write-Host "Creating isolated mocap environment with $BasePython (cp$BaseVersion)..."
    Invoke-NativeRequired -Exe $BasePython -Arguments @(
        "-m","venv",$EnvDir
    ) -FailureMessage "Could not create $EnvDir"

    $Wheel=".\tools\wheels\mediapipe-0.10.18-cp$BaseVersion-cp$BaseVersion-win_amd64.whl"
    if(!(Test-Path $Wheel)){throw "No packaged MediaPipe wheel for cp$BaseVersion"}

    Invoke-NativeRequired -Exe $EnvPython -Arguments @(
        "-m","pip","install","--upgrade","pip","setuptools","wheel"
    ) -FailureMessage "Failed to update pip in the mocap environment"

    Invoke-NativeRequired -Exe $EnvPython -Arguments @(
        "-m","pip","install",
        "numpy==1.26.4",
        "scipy==1.13.1",
        $Wheel
    ) -FailureMessage "Failed to install the local pose environment"

    if(!(Test-MocapEnvironment -PythonPath $EnvPython)){
        throw "The newly created mocap environment failed its import/version health check."
    }
    Write-Host "Isolated mocap environment created and verified."
}

$env:PYTHONPATH=(Resolve-Path ".\tools\mocap").Path

Write-Host "Running local pose-pipeline self-test..."
Invoke-NativeRequired -Exe $EnvPython -Arguments @(
    $SelfTest,
    "--reference-video",$VideoPath
) -FailureMessage "Pose-pipeline self-test failed"

$cacheProbe=Invoke-NativeProbe -Exe $EnvPython -Arguments @(
    $CacheValidator,
    "--video",$VideoPath,
    "--analysis",$AnalysisPath,
    "--raw",$RawPath,
    "--processed",$ProcessedPath,
    "--overlay",$OverlayPath,
    "--report",$PoseReport
)

if($cacheProbe -eq "POSE_CACHE_OK"){
    Write-Host "Reusing the verified 764-frame pose extraction from the successful previous run."
}else{
    Write-Host "Pose cache is incomplete or invalid; extracting all 33 landmarks again..."
    Invoke-NativeRequired -Exe $EnvPython -Arguments @(
        $Extractor,
        "--video",$VideoPath,
        "--analysis",$AnalysisPath,
        "--output",$RawPath,
        "--overlay",$OverlayPath
    ) -FailureMessage "Automatic pose extraction failed"

    Write-Host "Smoothing landmarks and detecting floor/foot contacts..."
    Invoke-NativeRequired -Exe $EnvPython -Arguments @(
        $Processor,
        "--raw",$RawPath,
        "--output",$ProcessedPath,
        "--report",$PoseReport
    ) -FailureMessage "Pose cleanup/contact detection failed"
}

Write-Host "Running Blender retarget API/data preflight..."
Invoke-NativeRequired -Exe $BlenderExe -Arguments @(
    "--background",
    "--factory-startup",
    "--python-exit-code","1",
    "--python",$BlenderPreflight,
    "--",
    "--processed",$ProcessedPath
) -FailureMessage "Blender jumpstyle retarget preflight failed"

Write-Host "Creating the full automatic Sackboy jumpstyle action..."
$beforeBackups=@(
    Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue
).Count

Invoke-NativeRequired -Exe $BlenderExe -Arguments @(
    "--background",
    ".\blender\sackboy_scene.blend",
    "--python-exit-code","1",
    "--python",$BlenderApply,
    "--",
    "--processed",$ProcessedPath,
    "--analysis",$AnalysisPath
) -FailureMessage "Blender jumpstyle retarget failed"

$afterBackups=@(
    Get-ChildItem ".\Backups" -Recurse -File -Include *.blend,*.blend1 -ErrorAction SilentlyContinue
).Count
if($afterBackups -ne $beforeBackups){
    throw "Safety stop: Backups .blend count changed"
}

Write-Host "=== AUTOMATED JUMPSTYLE MOCAP COMPLETE ==="
Write-Host "Action: SACKBOY_JUMPSTYLE_RETARGET_V1"
Write-Host "Tracking overlay: $OverlayPath"
Write-Host "Pose report: $PoseReport"
Write-Host "Run Validate-AutomatedJumpstyleMocapV1_3.ps1 next."
