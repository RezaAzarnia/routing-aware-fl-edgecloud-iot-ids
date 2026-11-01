# Shared helpers for the Phase 6C PowerShell scripts (dot-sourced; Windows PowerShell 5.1 compatible).

function Resolve-RepoRoot {
    param([string]$ScriptDir, [string]$Root)
    if ($Root) { return (Resolve-Path -LiteralPath $Root).Path }
    return (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..\..")).Path
}

function Test-PythonCandidate {
    param([string]$Candidate)
    if (-not $Candidate) { return $false }
    if (-not (Test-Path -LiteralPath $Candidate) -and -not (Get-Command $Candidate -ErrorAction SilentlyContinue)) { return $false }
    try {
        & $Candidate -c "import torch, numpy, pandas, sklearn, yaml" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    param([string]$Explicit, [string]$Repo)
    $candidates = @()
    if ($Explicit) { $candidates += $Explicit }
    if ($env:IOTFL_PYTHON) { $candidates += $env:IOTFL_PYTHON }
    $candidates += (Join-Path $Repo ".venv\Scripts\python.exe")
    $candidates += (Join-Path $Repo "venv\Scripts\python.exe")
    $candidates += (Join-Path $Repo "..\..\IoT-FL-Recovery\venv\Scripts\python.exe")
    $candidates += (Join-Path $Repo "..\IoT-FL-Recovery\venv\Scripts\python.exe")
    $candidates += "python"
    foreach ($c in $candidates) {
        if (Test-PythonCandidate $c) {
            if (Test-Path -LiteralPath $c) { return (Resolve-Path -LiteralPath $c).Path }
            return (Get-Command $c).Source
        }
    }
    return $null
}

function Get-PhaseArgs {
    param([string]$Manifest, [string]$Repo)
    return @("--manifest", $Manifest, "--root", $Repo)
}
