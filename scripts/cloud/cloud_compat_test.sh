#!/usr/bin/env bash
# One controlled compatibility test on the cloud VM. Uses ONLY train/validation data. Writes to results_cloud_compat/
# (NOT results_phase6c) and never touches the locked test files (they are absent on the VM).
# Re-runs one real arm (UNSW reference, seed 12, ~1-2 min) and compares it with the verified LOCAL run of the same job.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
WORK="${WORK:-$HOME/iotfl}"
LOCAL_REF="$WORK/cloud_transfer/reference_local_partial/results_phase6c/unsw/reference/seed_12"

echo "== 1. unit/regression tests that do not need test data"
$PY -m pytest -q -p no:cacheprovider tests/test_phase6c_lock.py tests/test_phase6c_runner.py tests/test_phase6c_science.py tests/test_phase6c_final_test.py tests/test_phase6c_run_one.py

echo "== 2. real job re-run: unsw / reference / seed 12 (train+validation data only)"
rm -rf results_cloud_compat; mkdir -p results_cloud_compat
OUT=results_cloud_compat/unsw_reference_seed12
PYTHONHASHSEED=0 $PY scripts/phase6c/run_one.py --config configs/phase6c/unsw_reference.yaml --seed 12 --out "$OUT"

echo "== 3. compare with the verified local run (same config, seed, code)"
if [ -d "$LOCAL_REF" ]; then
  $PY scripts/cloud/compare_runs.py "$LOCAL_REF" "$OUT" || echo "NOTE: numeric differences between platforms (reported above). Decide per README_CLOUD.md section 'Platform decision'."
else
  echo "local reference run not in the bundle; skipped comparison"
fi
echo "COMPAT TEST DONE (no experiment in results_phase6c was started)."
