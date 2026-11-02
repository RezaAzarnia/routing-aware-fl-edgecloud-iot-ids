<#
.SYNOPSIS
  Runs the (unchanged, locked) Phase 6C runner with LIVE per-round logging switched on.
.DESCRIPTION
  Sets IOTFL_LIVE=1 and prepends scripts\live to PYTHONPATH for this process tree only, then calls
  scripts\phase6c\run_five_seeds.ps1 with exactly the arguments you give. The logging wrapper never changes any
  computation (verified by a test: identical results with and without it). The locked manifest is unaffected.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\live\run_with_live.ps1            # dry run
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\live\run_with_live.ps1 -Execute
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\live\run_with_live.ps1 -Execute -Resume
#>
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:IOTFL_LIVE = "1"
$env:PYTHONPATH = $here + $(if ($env:PYTHONPATH) { ";" + $env:PYTHONPATH } else { "" })
$runner = Join-Path $here "..\phase6c\run_five_seeds.ps1"
& $runner @args
exit $LASTEXITCODE
