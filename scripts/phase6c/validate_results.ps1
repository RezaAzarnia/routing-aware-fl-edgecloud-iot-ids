<#
.SYNOPSIS
  Verifies every completed run against the locked manifest and writes the aggregated summary
  (per-arm statistics, paired contrasts with exact tests). Read-only with respect to the runs.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\validate_results.ps1
#>
[CmdletBinding()]
param(
    [ValidateSet("validation", "test")][string]$Source = "validation",
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
    & $py $orch validate --manifest $Manifest --root $repo
    $v = $LASTEXITCODE
    & $py $orch aggregate --manifest $Manifest --root $repo --source $Source
    $a = $LASTEXITCODE
    if ($v -eq 0 -and $a -eq 0) {
        Write-Host "VALIDATION PASSED. Summary files: results_phase6c\_summary" -ForegroundColor Green
        exit 0
    }
    Write-Host "Validation incomplete or aggregation failed (validate exit $v, aggregate exit $a)." -ForegroundColor Yellow
    exit 1
}
finally { Pop-Location }
