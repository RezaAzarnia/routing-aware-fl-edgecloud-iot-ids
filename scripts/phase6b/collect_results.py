"""Collect all Phase-6B one-seed results into comparison tables (read-only on results)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results_phase6b"
OUT = ROOT / "docs" / "phase6b"
rows = []
for d in ("unsw", "ciciot"):
    for cfg in sorted((ROOT / "configs" / "phase6b").glob(f"{d}_v*.yaml")):
        name = cfg.stem[len(d) + 1:]
        run = R / f"phase6b_{d}_{name}" / name / "seed_2"
        fin = json.loads((run / "final_validation_metrics.json").read_text())
        sel = fin["selected_operating_point"]
        thr = fin["threshold_diagnostics"]
        dg = json.loads((run / "phase6b_diagnostics.json").read_text())
        rm = pd.read_csv(run / "round_metrics.csv").query("round>=1")
        acc = json.loads((run / "metric_accounting.json").read_text())
        net = pd.read_csv(run / "network_metrics.csv")
        up = dg["updates"]
        rows.append({
            "dataset": d, "variant": name, "best_round": fin["best_round"],
            "roc_auc": sel["roc_auc"], "pr_auc": sel["pr_auc"],
            "f1_at_15pct_cal": sel["f1"], "precision": sel["precision"], "recall": sel["recall_adr"],
            "eval_fpr_at_15pct_cal": sel["fpr"], "cal_fpr_15pct": sel.get("calibration_fpr"),
            "eval_fpr_at_5pct_cal": thr["5pct"]["independent_evaluation"]["fpr"],
            "eval_recall_at_5pct_cal": thr["5pct"]["independent_evaluation"]["recall_adr"],
            "eval_fpr_at_1pct_cal": thr["1pct"]["independent_evaluation"]["fpr"],
            "eval_recall_at_1pct_cal": thr["1pct"]["independent_evaluation"]["recall_adr"],
            "same_obs_fpr_target_15": thr["15pct"]["same_observation_optimistic"]["fpr"],
            "same_obs_recall_15": thr["15pct"]["same_observation_optimistic"]["recall_adr"],
            "tn": sel["tn"], "fp": sel["fp"], "fn": sel["fn"], "tp": sel["tp"],
            "auc_min_after_r3": dg["round_stability"]["val_roc_auc_min_after_round3"],
            "rounds_auc_lt_0p9_after_r3": dg["round_stability"]["rounds_with_auc_below_0.9_after_round3"],
            "auc_std_last10": dg["round_stability"]["val_roc_auc_std_last10"],
            "final_train_loss": float(rm["mean_train_loss"].iloc[-1]),
            "clients_ever_selected": dg["participation"]["clients_ever_selected"],
            "selection_gini": dg["participation"]["selection_gini"],
            "longest_gap_sel": dg["participation"]["longest_exclusion_gap_rounds_selection"]["max"],
            "sample_coverage": dg["participation"]["sample_coverage_of_ever_selected"],
            "worst_client_recall": dg["fairness"]["worst_client_recall"],
            "recall_never_selected": dg["fairness"]["mean_client_recall_never_selected"],
            "recall_ever_selected": dg["fairness"]["mean_client_recall_ever_selected"],
            "received": up["received_total"], "failed": up["failed_total"], "imputed": up["imputed_total"],
            "surrogate_weight_share": dg["weights"]["mean_surrogate_weight_share"],
            "real_weight_share": up["mean_real_weight_share"],
            "benign_real_rejected": up["benign_real_rows_rejected"],
            "mal_kept": up["effective_malicious_updates_kept"], "mal_rejected": up["effective_malicious_updates_rejected"],
            "retained_mean": dg["weights"]["retained_updates_mean"],
            "max_weight_share_mean": dg["weights"]["max_applied_weight_share_mean"],
            "delivery_ratio": acc["update_delivery_ratio__delivered_over_selected"],
            "received_ratio": acc["received_ratio__received_over_selected"],
            "mean_pdr_first_tx": acc["mean_pdr__over_selected"],
            "mean_delay_ms": dg["network"]["mean_end_to_end_delay_ms"],
            "bytes_attempted": dg["network"]["communication_bytes_attempted"],
            "bytes_on_wire": int(net["bytes_on_wire"].sum()),
            "bytes_delivered": dg["network"]["communication_bytes_delivered_to_server"],
            "noise_to_signal": dg["clipping_and_noise"]["mean_noise_to_signal"],
            "wall_s": dg["resources"]["wall_seconds"], "peak_mb": dg["resources"]["peak_working_set_mb"],
        })
table = pd.DataFrame(rows)
table.to_csv(OUT / "phase6b_results_table.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 60)
print(table.round(4)[["dataset", "variant", "best_round", "roc_auc", "pr_auc", "f1_at_15pct_cal", "eval_fpr_at_15pct_cal",
                      "cal_fpr_15pct", "recall", "auc_min_after_r3", "rounds_auc_lt_0p9_after_r3"]].to_string(index=False))
