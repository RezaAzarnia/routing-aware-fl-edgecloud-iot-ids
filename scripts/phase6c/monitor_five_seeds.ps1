<#
.SYNOPSIS
  READ-ONLY progress monitor for the Phase 6C runs. Never starts, stops or modifies anything.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\monitor_five_seeds.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\monitor_five_seeds.ps1 -Watch
#>
[CmdletBinding()]
param(
    [switch]$Watch,
    [int]$IntervalSeconds = 30,
    [string]$PythonPath = "",
    [string]$Manifest = "",
    [string]$Root = ""
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $here "_common.ps1")
$repo = Resolve-RepoRoot -ScriptDir $here -Root $Root
if (-not $Manifest) { $Manifest = Join-Path $repo "docs\phase6c\EXPERIMENT_MANIFEST.json" }
$py = Find-Python -Explicit $PythonPath -Repo $repo
if (-not $py) { Write-Host "CRITICAL: no suitable Python found (use -PythonPath)." -ForegroundColor Red; exit 2 }
$orch = Join-Path $here "orchestrator.py"
Push-Location $repo
try {
    do {
        & $py $orch status --manifest $Manifest --root $repo
        if ($Watch) { Start-Sleep -Seconds $IntervalSeconds; Write-Host "" }
    } while ($Watch)
}
finally { Pop-Location }
