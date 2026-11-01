"""Extra measured analyses for Phase 6B (read-only)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results_phase6b"
variants = sorted({p.stem.split("_", 1)[1] for p in (ROOT / "configs" / "phase6b").glob("*_v*.yaml")})
out = {"threshold": {}, "malicious_exposure": {}, "surrogate_dominance": {}, "feasibility": {}}
for d in ("unsw", "ciciot"):
    thr_rows = []
    for v in variants:
        run = R / f"phase6b_{d}_{v}" / v / "seed_2"
        td = json.loads((run / "threshold_diagnostics.json").read_text())
        for key in ("1pct", "5pct", "15pct"):
            e = td[key]
            thr_rows.append({
                "variant": v, "target": key, "cal_fpr": e["calibration_partition"]["fpr"],
                "eval_fpr": e["independent_evaluation"]["fpr"], "eval_recall": e["independent_evaluation"]["recall_adr"],
                "same_obs_fpr": e["same_observation_optimistic"]["fpr"], "same_obs_recall": e["same_observation_optimistic"]["recall_adr"],
                "cal_feasible": e["calibration_partition"]["constraint_feasible"],
            })
        rm = pd.read_csv(run / "round_metrics.csv").query("round>=1")
        out["feasibility"].setdefault(d, {})[v] = {
            "rounds_constraint_infeasible": int((~rm["val_constraint_feasible"].astype(bool)).sum()),
            "calibration_rows": int(rm["val_calibration_rows"].iloc[0]),
        }
        # malicious exposure
        mal = set(json.loads((run / "malicious_clients.json").read_text())["malicious_clients"])
        net = pd.read_csv(run / "network_metrics.csv")
        agg = pd.read_csv(run / "aggregation_diagnostics.csv")
        per_round_kept = agg[agg["effective_malicious_update"].astype(bool) & agg["kept"].astype(bool)].groupby("round").size()
        rm = rm.set_index("round")
        kept_mal = per_round_kept.reindex(rm.index, fill_value=0)
        sel_mal = net[net["client_id"].isin(mal)].groupby("round").size().reindex(rm.index, fill_value=0)
        out["malicious_exposure"].setdefault(d, {})[v] = {
            "malicious_share_of_selections": float(net["client_id"].isin(mal).mean()),
            "rounds_with_ge5_malicious_selected": int((sel_mal >= 5).sum()),
            "rounds_with_ge1_malicious_kept": int((kept_mal >= 1).sum()),
            "mean_auc_rounds_no_malicious_kept": float(rm.loc[kept_mal == 0, "val_roc_auc"].mean()) if (kept_mal == 0).any() else None,
            "mean_auc_rounds_malicious_kept": float(rm.loc[kept_mal >= 1, "val_roc_auc"].mean()) if (kept_mal >= 1).any() else None,
            "corr_auc_vs_malicious_selected": float(np.corrcoef(rm["val_roc_auc"], sel_mal)[0, 1]),
        }
        rows_real = agg[~agg["is_recovered_update"].astype(bool)]
        kept_real_per_round = rows_real[rows_real["kept"].astype(bool)].groupby("round").size().reindex(rm.index, fill_value=0)
        out["surrogate_dominance"].setdefault(d, {})[v] = {
            "rounds_with_zero_real_updates_retained": int((kept_real_per_round == 0).sum()),
            "rounds_surrogate_share_ge_0.5": int((rm["surrogate_weight_share"] >= 0.5).sum()),
            "max_surrogate_share": float(rm["surrogate_weight_share"].max()),
        }
    thr = pd.DataFrame(thr_rows)
    thr["abs_shift"] = (thr["eval_fpr"] - thr["cal_fpr"]).abs()
    thr["rel_excess"] = (thr["eval_fpr"] - thr["cal_fpr"]) / thr["cal_fpr"].clip(lower=1e-6)
    summary = {}
    for key, g in thr.groupby("target"):
        summary[key] = {"mean_cal_fpr": float(g.cal_fpr.mean()), "mean_eval_fpr": float(g.eval_fpr.mean()),
                        "mean_abs_shift": float(g.abs_shift.mean()), "max_abs_shift": float(g.abs_shift.max()),
                        "median_relative_excess": float(g.rel_excess.median()),
                        "mean_same_obs_recall_minus_eval_recall": float((g.same_obs_recall - g.eval_recall).mean()),
                        "mean_same_obs_fpr": float(g.same_obs_fpr.mean())}
    out["threshold"][d] = summary
    thr.to_csv(ROOT / "docs" / "phase6b" / f"threshold_table_{d}.csv", index=False)
(ROOT / "docs" / "phase6b" / "extra_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out["threshold"], indent=1))
for d in ("unsw", "ciciot"):
    print("==", d)
    for v in variants:
        m = out["malicious_exposure"][d][v]; s = out["surrogate_dominance"][d][v]; f = out["feasibility"][d][v]
        print(f"{v:36s} mal_sel={m['malicious_share_of_selections']:.2f} r>=5mal={m['rounds_with_ge5_malicious_selected']:2d} r_malkept={m['rounds_with_ge1_malicious_kept']:2d} "
              f"auc|nomal={m['mean_auc_rounds_no_malicious_kept']} auc|mal={m['mean_auc_rounds_malicious_kept']} zeroReal={s['rounds_with_zero_real_updates_retained']} sur>=.5={s['rounds_surrogate_share_ge_0.5']} infeas={f['rounds_constraint_infeasible']}")
