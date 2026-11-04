"""Five-seed aggregate + exact paired statistics from tables/all_runs.csv (no access to raw experiment folders).

usage: python statistical_analysis.py --handoff <handoff dir>
Exact two-sided Wilcoxon signed-rank (n=5 => smallest attainable p = 0.0625), exact sign-flip permutation test on the
mean difference (smallest p = 0.0625), paired Cohen d_z and t-based 95% CI (exploratory; small n). No multiplicity
correction is applied: every p-value is exploratory.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

METRICS = ["best_auc", "best_f1", "best_precision", "best_recall_adr", "best_fpr", "last_auc", "last_f1",
           "auc_drop_best_minus_last", "train_loss_max", "malicious_accepted_total", "surrogate_weight_share_mean",
           "real_kept_per_round_mean", "mean_pdr", "mean_delay_ms", "update_delivery_ratio", "selection_gini_recomputed",
           "communication_bytes_on_wire_total"]


def exact_signflip_p(d):
    d = np.asarray(d, float)
    obs = abs(d.mean())
    n = len(d)
    cnt = 0
    for signs in itertools.product([1, -1], repeat=n):
        cnt += abs((np.asarray(signs) * d).mean()) >= obs - 1e-15
    return cnt / 2 ** n


def paired(df, ds, a, b, m):
    A = df[(df.dataset == ds) & (df.arm == a)].set_index("seed")[m]
    B = df[(df.dataset == ds) & (df.arm == b)].set_index("seed")[m]
    s = sorted(set(A.index) & set(B.index))
    d = (B[s] - A[s]).to_numpy(float)
    n = len(d)
    sd = d.std(ddof=1) if n > 1 else np.nan
    se = sd / np.sqrt(n) if n > 1 else np.nan
    tcrit = stats.t.ppf(0.975, n - 1) if n > 1 else np.nan
    try:
        pw = stats.wilcoxon(d, method="exact").pvalue if np.any(d != 0) else 1.0
    except ValueError:
        pw = np.nan
    return {"dataset": ds, "metric": m, "arm_a(baseline)": a, "arm_b": b, "n_pairs": n,
            "mean_a": A[s].mean(), "mean_b": B[s].mean(), "mean_diff_b_minus_a": d.mean(), "sd_diff": sd,
            "ci95_low_t": d.mean() - tcrit * se, "ci95_high_t": d.mean() + tcrit * se,
            "cohen_dz": d.mean() / sd if sd and sd > 0 else np.nan,
            "b_better_seeds": int((d > 0).sum()), "a_better_seeds": int((d < 0).sum()), "ties": int((d == 0).sum()),
            "p_wilcoxon_exact": pw, "p_signflip_exact": exact_signflip_p(d), "per_seed_diff": json.dumps(dict(zip(s, np.round(d, 6).tolist())))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True)
    h = Path(ap.parse_args().handoff)
    df = pd.read_csv(h / "tables" / "all_runs.csv")
    arms = pd.read_csv(h / "tables" / "arm_definitions.csv")
    man = json.loads((h / "provenance" / "experiment_manifest.json").read_text(encoding="utf-8"))
    # ---- aggregate (per dataset x arm) ----
    recs = []
    for (ds, arm), g in df.groupby(["dataset", "arm"]):
        r = {"dataset": ds, "arm": arm, "n_seeds": len(g)}
        for m in METRICS:
            v = g[m].astype(float)
            r[f"{m}_mean"], r[f"{m}_sd"] = v.mean(), v.std(ddof=1)
            r[f"{m}_min"], r[f"{m}_max"] = v.min(), v.max()
            r[f"{m}_per_seed"] = json.dumps(dict(zip(g.seed.tolist(), np.round(v.to_numpy(), 6).tolist())))
        r["n_diverged_runs_loss_gt100"] = int(g.diverged_loss_gt100.sum())
        recs.append(r)
    agg = pd.DataFrame(recs).merge(arms[["arm", "group", "description", "algorithm_version"]], on="arm", how="left")
    agg.to_csv(h / "tables" / "aggregate_metrics.csv", index=False)
    # ---- paired comparisons ----
    pairs = {(c["arm"], c["compare_with"]) for c in man["arms"] if c.get("compare_with")}
    explicit = [("reference", "corrected"), ("reference", "clean_fedavg"), ("reference", "scenario_fedavg_random"),
                ("reference", "scenario_fedavg_topk"), ("scenario_fedavg_random", "robust_random_no_imputation"),
                ("scenario_fedavg_topk", "reference"), ("clean_fedavg", "clean_centralized"), ("nat_reference", "reference"),
                ("nat_corrected", "corrected"), ("fail0p3_reference", "reference"), ("fail0p3_corrected", "corrected"),
                ("ctl_delivery_coupled", "corrected"), ("ctl_imputation_postfilter", "corrected"),
                ("ctl_selection_coverage", "corrected"), ("reference_gaussian", "corrected_gaussian")]
    todo = [(b, a) for (a, b) in sorted(pairs)] + explicit            # (baseline, other)
    seen, out = set(), []
    for base, other in todo:
        if (base, other) in seen:
            continue
        seen.add((base, other))
        for ds in ("unsw", "ciciot"):
            for m in ("best_auc", "last_auc", "best_f1", "best_recall_adr", "best_fpr", "train_loss_max", "mean_pdr", "mean_delay_ms",
                      "malicious_accepted_total", "surrogate_weight_share_mean", "real_kept_per_round_mean"):
                out.append(paired(df, ds, base, other, m))
    pc = pd.DataFrame(out)
    pc.insert(0, "contrast_type", pc.apply(lambda r: "manifest_primary_or_declared" if (r["arm_b"], r["arm_a(baseline)"]) in pairs else "exploratory_extra", axis=1))
    pc.to_csv(h / "tables" / "paired_comparisons.csv", index=False)
    # ---- ablation table: every ctl_* arm vs reference and vs corrected ----
    ab = pc[(pc["arm_b"].str.startswith("ctl_") | pc["arm_b"].isin(["corrected", "nat_selection_uniform"])) & pc.metric.isin(["best_auc", "last_auc", "train_loss_max"])]
    ab.to_csv(h / "tables" / "ablation_results.csv", index=False)
    print("aggregate rows", len(agg), "paired rows", len(pc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
