#!/usr/bin/env bash
# Start (or resume) the locked 240-run experiment on the cloud VM, detached, with automatic result synchronisation.
# Refuses to start if a runner is already active. Safe to call again after any interruption/reboot (it resumes).
# usage: bash scripts/cloud/cloud_run.sh        # optional: SYNC_TARGET=user@backup:/path or /mnt/volume/path or rclone:remote:bucket/path
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
LOG=results_phase6c/_logs
mkdir -p "$LOG"

# never run next to another runner (the orchestrator lock also enforces this)
if [ -f results_phase6c/_state/runner.lock ]; then
  PID=$($PY -c "import json;print(json.load(open('results_phase6c/_state/runner.lock'))['pid'])")
  if kill -0 "$PID" 2>/dev/null; then echo "A runner is already active (PID $PID). Nothing started."; exit 0; fi
fi
$PY scripts/phase6c/orchestrator.py preflight --cloud-mode || { echo "Preflight failed; nothing started."; exit 2; }

STAMP=$(date +%Y%m%d-%H%M%S)
RESUME=""; ls -d results_phase6c/*/*/seed_* >/dev/null 2>&1 && RESUME="--resume"
nohup env PYTHONUNBUFFERED=1 $PY scripts/phase6c/orchestrator.py run --cloud-mode $RESUME \
      > "$LOG/runner_$STAMP.out.log" 2> "$LOG/runner_$STAMP.err.log" &
echo "runner started: PID $! ($LOG/runner_$STAMP.out.log)"

if [ -n "${SYNC_TARGET:-}" ]; then
  nohup bash scripts/cloud/cloud_sync.sh > "$LOG/sync_$STAMP.log" 2>&1 &
  echo "sync loop started (target: $SYNC_TARGET)"
fi
echo "progress: $PY scripts/phase6c/orchestrator.py status --cloud-mode   |   after reboot: bash scripts/cloud/cloud_run.sh"
