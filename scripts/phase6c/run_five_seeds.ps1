<#
.SYNOPSIS
  Phase 6C five-seed experiment runner. DRY-RUN BY DEFAULT.

.DESCRIPTION
  Without -Execute this script only performs the preflight and prints the experiment queue.
  Training starts ONLY with -Execute. Runs are sequential (never concurrent), each in its own
  immutable result directory; verified results are never overwritten. -Resume re-runs only the
  missing, failed or incomplete runs (previous attempts are preserved, not deleted).
  The final test set is never touched by this script (it is a separate, authorised operation).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\run_five_seeds.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\run_five_seeds.ps1 -Execute
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\run_five_seeds.ps1 -Execute -Resume
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [switch]$Resume,
    [switch]$Detached,
    [string]$PythonPath = "",
    [string]$Manifest = "",
    [string]$Root = "",
    [int]$MaxConsecutiveFailures = 3,
    [switch]$SkipDataHash,
    [double]$MinFreeGB = 20
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $here "_common.ps1")

$repo = Resolve-RepoRoot -ScriptDir $here -Root $Root
if (-not $Manifest) { $Manifest = Join-Path $repo "docs\phase6c\EXPERIMENT_MANIFEST.json" }
if (-not (Test-Path -LiteralPath $Manifest)) { Write-Host "CRITICAL: manifest not found: $Manifest" -ForegroundColor Red; exit 2 }

$py = Find-Python -Explicit $PythonPath -Repo $repo
if (-not $py) {
    Write-Host "CRITICAL: no Python with torch/numpy/pandas/scikit-learn/PyYAML found." -ForegroundColor Red
    Write-Host "Pass -PythonPath <path\to\python.exe> or set `$env:IOTFL_PYTHON." -ForegroundColor Red
    exit 2
}
$orch = Join-Path $here "orchestrator.py"
Write-Host "Repository : $repo"
Write-Host "Python     : $py"
Write-Host "Manifest   : $Manifest"

$common = @("--manifest", $Manifest, "--root", $repo)
$extra = @("--min-free-gb", "$MinFreeGB")
if ($SkipDataHash) { $extra += "--skip-data-hash" }

Push-Location $repo
try {
    if (-not $Execute) {
        Write-Host ""
        Write-Host "=== DRY RUN (no training will start) ===" -ForegroundColor Yellow
        & $py $orch preflight @common @extra
        $pre = $LASTEXITCODE
        & $py $orch plan @common
        if ($pre -ne 0) {
            Write-Host "PREFLIGHT FAILED. Fix the problems above before executing." -ForegroundColor Red
            exit 2
        }
        Write-Host ""
        Write-Host "Preflight passed. To start the experiments add -Execute (and -Resume after an interruption)." -ForegroundColor Green
        exit 0
    }

    $runArgs = @("run") + $common + $extra + @("--max-consecutive-failures", "$MaxConsecutiveFailures")
    if ($Resume) { $runArgs += "--resume" }

    if ($Detached) {
        $logDir = Join-Path $repo "results_phase6c\_logs"
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $outLog = Join-Path $logDir "runner_$stamp.out.log"
        $errLog = Join-Path $logDir "runner_$stamp.err.log"
        $quoted = @($orch) + $runArgs | ForEach-Object { '"' + $_ + '"' }
        $p = Start-Process -FilePath $py -ArgumentList ($quoted -join " ") -WorkingDirectory $repo `
             -WindowStyle Minimized -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
        Write-Host "Started detached runner, PID $($p.Id). It keeps running if you close this window."
        Write-Host "Progress: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\monitor_five_seeds.ps1"
        exit 0
    }

    & $py $orch @runArgs
    $code = $LASTEXITCODE
    Write-Host ""
    switch ($code) {
        0   { Write-Host "Runner finished (exit 0)." -ForegroundColor Green }
        130 { Write-Host "Interrupted. Resume with: ... run_five_seeds.ps1 -Execute -Resume" -ForegroundColor Yellow }
        default { Write-Host "Runner stopped with exit code $code. See the messages above and the logs in results_phase6c\_logs." -ForegroundColor Red }
    }
    exit $code
}
finally {
    Pop-Location
}
