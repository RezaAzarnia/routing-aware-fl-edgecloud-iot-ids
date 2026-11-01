"""Apply the metric-accounting invariants to the archived Phase-6A runs."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.metric_accounting import reconcile_network_events  # noqa: E402

out = {}
for run in sorted((ROOT / "docs" / "phase6a" / "runs").iterdir()):
    net = pd.read_csv(run / "network_metrics.csv")
    rm = pd.read_csv(run / "round_metrics.csv")
    out[run.name] = reconcile_network_events(net, rm, failure_enabled=True)
(ROOT / "docs" / "phase6b" / "phase6a_metric_reconciliation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out["phase6a_unsw_no_dp"], indent=1))
print({k: v["invariants_hold"] for k, v in out.items()})
