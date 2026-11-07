#!/bin/bash
# Waits until all 40 new runs have completion records, then builds tables, figure and LaTeX. Read-only on runs.
cd "$(dirname "$0")/../.."
PY=/c/Users/R_Azarnia/venv_ablation/Scripts/python.exe
while [ "$(find results_ablation_controlled_v2/runs -name ablation_COMPLETE.json | wc -l)" -lt 40 ]; do sleep 30; done
sleep 5
$PY scripts/ablation_v2/verify_historical.py && $PY scripts/ablation_v2/analyse.py && $PY scripts/ablation_v2/make_figure_table.py
echo "postprocess exit=$? at $(date)"
