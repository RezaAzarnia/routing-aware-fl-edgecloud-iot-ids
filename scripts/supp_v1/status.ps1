# Read-only status of the supplementary-experiment runner. Changes nothing; safe to run at any time.
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$out  = Join-Path $root 'results_supplementary_v1'
$lock = Join-Path $out '_state\runner.lock'
$done = (Get-ChildItem $out -Recurse -Filter COMPLETE.json -ErrorAction SilentlyContinue | Measure-Object).Count
$fail = (Get-ChildItem $out -Recurse -Filter FAILED.json   -ErrorAction SilentlyContinue | Measure-Object).Count
"Verified-complete runs : $done / 278   (failed: $fail)"
if (Test-Path $lock) {
  $pid_ = (Get-Content $lock | ConvertFrom-Json).pid
  $alive = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
  "Runner lock owner PID  : $pid_  ->  " + $(if ($alive) { 'RUNNING' } else { 'NOT RUNNING (stale lock)' })
} else { 'Runner lock           : none (runner not active)' }
"Last runner log lines  :"; Get-Content (Join-Path $out '_runner_main.out.log') -Tail 3
$ev = Join-Path $out '_state\events.jsonl'
if (Test-Path $ev) { "Last events            :"; Get-Content $ev -Tail 3 }
