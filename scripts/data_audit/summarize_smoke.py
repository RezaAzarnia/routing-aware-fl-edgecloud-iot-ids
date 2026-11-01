"""Summarise a smoke run from VALIDATION-side artefacts only (final-test files are ignored)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

run = Path(sys.argv[1])
rm = pd.read_csv(run / "round_metrics.csv")
net = pd.read_csv(run / "network_metrics.csv")
agg = pd.read_csv(run / "aggregation_diagnostics.csv")
rec = pd.read_csv(run / "recovery_events.csv")
cd = pd.read_csv(run / "client_distribution.csv")
plan = json.loads((run / "privacy_plan.json").read_text())
split = json.loads((run / "validation_split_info.json").read_text())
usage = json.loads((run / "resource_usage.json").read_text())
cols = ["round", "selected_clients", "received_updates", "kept_updates", "rejected_updates", "failed_clients",
        "recovered_clients", "malicious_selected", "mean_train_loss", "privacy_epsilon_estimate",
        "privacy_noise_std", "privacy_noise_to_signal_ratio", "server_applied_update_l2_norm",
        "val_f1", "val_roc_auc", "val_precision", "val_recall_adr", "val_fpr", "val_tn", "val_fp", "val_fn", "val_tp",
        "selected_threshold", "mean_pdr", "mean_end_to_end_delay_ms", "communication_bytes"]
cols = [c for c in cols if c in rm.columns]
pd.set_option("display.width", 250, "display.max_columns", 40)
print(rm[cols].round(4).to_string(index=False))
final = rm.iloc[-1]
out = {
    "run": str(run),
    "clients": {"n": int(len(cd)), "min_samples": int(cd.num_samples.min()), "max_samples": int(cd.num_samples.max())},
    "participation": {"unique_clients_selected": int(net["client_id"].nunique()),
                      "transfers": int(len(net)), "delivered": int(net["received_by_server"].sum()),
                      "failed_transfers": int((~net["received_by_server"].astype(bool)).sum())},
    "recovery": {"events": int(len(rec)), "applied": int(rec["recovery_applied"].sum()) if len(rec) else 0},
    "aggregation": {"methods": sorted(agg["actual_aggregation_method"].unique().tolist()),
                    "kept": int(agg["kept"].sum()), "rejected": int((~agg["kept"].astype(bool)).sum()),
                    "malicious_rows": int(agg["is_malicious_client"].sum())},
    "privacy": {k: plan.get(k) for k in ("privacy_mode", "effective_noise_multiplier", "accountant_sample_rate",
                                         "planned_epsilon_estimate", "subsampling_amplification_valid")},
    "epsilon_after_last_round": float(final["privacy_epsilon_estimate"]),
    "server_momentum_applied_update_norm_last": float(final["server_applied_update_l2_norm"]),
    "checkpoint_saved": (run / "best_model_state.pt").exists(),
    "validation_split": split, "resources": usage,
    "finite_validation_metrics": bool(np.isfinite(rm[[c for c in cols if c.startswith("val_")]].to_numpy(dtype=float)).all()),
    "note": "Final-test files in this directory are NOT used or reported (test slot is a stand-in).",
}
print(json.dumps(out, indent=1))
(run / "smoke_validation_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
