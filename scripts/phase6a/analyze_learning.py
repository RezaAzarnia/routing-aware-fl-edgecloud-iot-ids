"""Measured (not hypothesised) quantities that characterise Gaussian vs no-Gaussian training."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(sys.argv[1])
out = {}
for d, clip in (("unsw", 0.1), ("ciciot", 0.05)):
    runs = {t: R / f"phase6a_{d}_{t}" / f"proposed_{t}" / "seed_2" for t in ("no_dp", "dp_original")}
    rm = {t: pd.read_csv(p / "round_metrics.csv").query("round>=1").reset_index(drop=True) for t, p in runs.items()}
    ag = {t: pd.read_csv(p / "aggregation_diagnostics.csv") for t, p in runs.items()}
    plan = json.loads((runs["dp_original"] / "privacy_plan.json").read_text())
    res = {}
    for t in runs:
        a = ag[t]
        real = a[~a["is_recovered_update"].astype(bool)]
        res[t] = {
            "median_pre_clip_update_norm_real": float(real["pre_clip_l2_norm"].median()),
            "p10_p90_pre_clip_norm_real": [float(real["pre_clip_l2_norm"].quantile(.1)), float(real["pre_clip_l2_norm"].quantile(.9))],
            "fraction_real_updates_above_clip": float((real["pre_clip_l2_norm"] > clip).mean()),
            "median_pre_clip_norm_malicious_effective": float(a.loc[a["effective_malicious_update"].astype(bool), "pre_clip_l2_norm"].median()),
            "kept_updates_mean_per_round": float(rm[t]["kept_updates"].mean()),
            "kept_updates_min": int(rm[t]["kept_updates"].min()),
            "val_roc_auc_mean_over_rounds": float(rm[t]["val_roc_auc"].mean()),
            "val_f1_mean_over_rounds": float(rm[t]["val_f1"].mean()),
            "first_round_val_auc_ge_0.90": (int(rm[t].loc[rm[t]["val_roc_auc"] >= 0.90, "round"].min()) if (rm[t]["val_roc_auc"] >= 0.90).any() else None),
            "first_round_val_auc_ge_0.95": (int(rm[t].loc[rm[t]["val_roc_auc"] >= 0.95, "round"].min()) if (rm[t]["val_roc_auc"] >= 0.95).any() else None),
            "val_auc_round_to_round_std_last10": float(rm[t]["val_roc_auc"].iloc[-10:].std()),
            "final_val_auc": float(rm[t]["val_roc_auc"].iloc[-1]),
        }
    dp = rm["dp_original"]
    res["dp_original"].update({
        "clip_norm": clip, "noise_multiplier": plan["effective_noise_multiplier"],
        "requested_weight_cap": plan["max_client_weight_share"],
        "realized_max_weight_share_mean": float(dp["privacy_max_weight_share"].mean()),
        "realized_max_weight_share_max": float(dp["privacy_max_weight_share"].max()),
        "rounds_where_cap_exceeded": int((dp["privacy_max_weight_share"] > plan["max_client_weight_share"] + 1e-9).sum()),
        "released_aggregate_signal_norm_mean": float(dp["aggregate_signal_l2_norm"].mean()),
        "noise_norm_mean": float(dp["privacy_noise_l2_norm"].mean()),
        "noise_to_signal_mean_median": [float(dp["privacy_noise_to_signal_ratio"].mean()), float(dp["privacy_noise_to_signal_ratio"].median())],
        "server_applied_update_norm_mean": float(dp["server_applied_update_l2_norm"].mean()),
        "accountant_sample_rate_assumed": plan["accountant_sample_rate"],
        "realized_distinct_clients_per_round": 10,
        "epsilon_final": float(dp["privacy_epsilon_estimate"].iloc[-1]),
        "release_count": int((dp["privacy_noise_std"] > 0).sum()),
    })
    res["no_dp"]["server_applied_update_norm_mean"] = float(rm["no_dp"]["server_applied_update_l2_norm"].mean())
    res["no_dp"]["aggregate_signal_norm_mean"] = float(rm["no_dp"]["aggregate_signal_l2_norm"].mean())
    out[d] = res
Path(sys.argv[2]).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=1))
