"""Cross-platform reproducibility check: compare a re-run (cloud) with a verified local run of the same config/seed.

usage: python scripts/cloud/compare_runs.py LOCAL_RUN_DIR CLOUD_RUN_DIR [--tol 1e-9]
Exit 0 = numerically identical (max abs diff <= tol over all numeric round-metric columns and final metrics);
exit 1 = differences (reported with their size, not hidden).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("local")
parser.add_argument("cloud")
parser.add_argument("--tol", type=float, default=1e-9)
args = parser.parse_args()
a, b = Path(args.local), Path(args.cloud)

ra, rb = pd.read_csv(a / "round_metrics.csv"), pd.read_csv(b / "round_metrics.csv")
skip = {"round_seconds", "mean_local_train_seconds"}
cols = [c for c in ra.columns if c in rb.columns and c not in skip and pd.api.types.is_numeric_dtype(ra[c])]
diffs = {c: float(np.nanmax(np.abs(ra[c].to_numpy(float) - rb[c].to_numpy(float)))) for c in cols}
bad = {c: d for c, d in diffs.items() if d > args.tol}
fa = json.loads((a / "final_validation_metrics.json").read_text())
fb = json.loads((b / "final_validation_metrics.json").read_text())
keys = ("roc_auc", "pr_auc", "f1", "fpr", "recall_adr", "precision")
final = {k: [fa["report_partition_at_selected_threshold"].get(k), fb["report_partition_at_selected_threshold"].get(k)] for k in keys}
final_diff = {k: abs(v[0] - v[1]) for k, v in final.items() if v[0] is not None and v[1] is not None}
na, nb = pd.read_csv(a / "network_metrics.csv"), pd.read_csv(b / "network_metrics.csv")
trace_cols = [c for c in ("client_id", "pdr", "update_delivered", "end_to_end_delay_ms", "explicit_failure_draw") if c in na and c in nb]
trace_equal = len(na) == len(nb) and all(((na[c] == nb[c]) | (na[c].isna() & nb[c].isna())).all() for c in trace_cols)
out = {
    "columns_compared": len(cols), "columns_with_difference_above_tol": len(bad),
    "max_abs_diff_round_metrics": max(diffs.values()) if diffs else None,
    "worst_columns": dict(sorted(bad.items(), key=lambda kv: -kv[1])[:8]),
    "best_round_local_cloud": [fa["best_round"], fb["best_round"]],
    "report_partition_metrics_local_vs_cloud": final, "final_metric_abs_diff": final_diff,
    "exogenous_network_and_failure_traces_identical": bool(trace_equal),
    "verdict": "IDENTICAL" if not bad and trace_equal else ("TRACES_IDENTICAL_BUT_NUMERICS_DIFFER" if trace_equal else "TRACES_DIFFER"),
}
print(json.dumps(out, indent=2))
sys.exit(0 if out["verdict"] == "IDENTICAL" else 1)
