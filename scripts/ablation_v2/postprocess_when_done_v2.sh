#!/bin/bash
# Waits for the EXACT 40 expected completion records (4 arms x 2 datasets x seeds 12-16), then builds
# tables, figure and LaTeX. Read-only on run directories. Exits nonzero (and says FAILED) on any failed step.
cd "$(dirname "$0")/../.." || exit 90
PY=/c/Users/R_Azarnia/venv_ablation/Scripts/python.exe
R=results_ablation_controlled_v2
[ -x "$PY" ] || { echo "FAILED: venv python missing"; exit 91; }
"$PY" -c "import torch,pandas,matplotlib,scipy,yaml" || { echo "FAILED: venv lacks dependencies"; exit 92; }
missing() {
  for ds in ciciot unsw; do for arm in abl_reference_repro abl_no_filter abl_privacy_clip_only abl_reference_gaussian_repro; do
    for s in 12 13 14 15 16; do [ -f "$R/runs/$ds/$arm/seed_$s/ablation_COMPLETE.json" ] || echo "$ds/$arm/seed_$s"; done; done; done
}
while [ -n "$(missing)" ]; do sleep 30; done
sleep 5
echo "all 40 expected completion records present at $(date)"
rm -f "$R/ablation_figure.png" "$R/ablation_table.tex"   # generated outputs only; stale copies must not mask a failure
step() { echo "== $*"; "$@" || { echo "FAILED (exit $?): $*"; exit 1; }; }
step "$PY" scripts/ablation_v2/verify_historical.py
step "$PY" scripts/ablation_v2/analyse.py
step "$PY" scripts/ablation_v2/make_figure_table.py
[ -s "$R/ablation_figure.png" ] || { echo "FAILED: ablation_figure.png missing/empty"; exit 2; }
[ -s "$R/ablation_table.tex" ]  || { echo "FAILED: ablation_table.tex missing/empty"; exit 3; }
echo "SUCCESS: post-processing finished at $(date)"
