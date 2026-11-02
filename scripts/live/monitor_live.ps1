<#
.SYNOPSIS
  READ-ONLY live monitor: queue progress, the active run's per-round loss/F1/AUC, and ETA. Starts/stops nothing.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\live\monitor_live.ps1 -Watch
#>
[CmdletBinding()]
param(
    [switch]$Watch,
    [int]$Interval = 15,
    [int]$Last = 8,
    [string]$PythonPath = "",
    [string]$Results = "results_phase6c",
    [string]$Manifest = "",
    [string]$Root = ""
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $here "..\phase6c\_common.ps1")
$repo = Resolve-RepoRoot -ScriptDir (Join-Path $here "..\phase6c") -Root $Root
if (-not $Manifest) { $Manifest = Join-Path $repo "docs\phase6c\EXPERIMENT_MANIFEST.json" }
$py = Find-Python -Explicit $PythonPath -Repo $repo
if (-not $py) { Write-Host "CRITICAL: no suitable Python found (use -PythonPath)." -ForegroundColor Red; exit 2 }
$argv = @((Join-Path $here "live_monitor.py"), "--root", $repo, "--results", $Results, "--manifest", $Manifest, "--interval", "$Interval", "--last", "$Last")
if ($Watch) { $argv += "--watch" }
& $py @argv
exit $LASTEXITCODE
