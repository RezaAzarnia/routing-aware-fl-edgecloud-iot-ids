"""Frozen analysis of the final-test results (plan final-test-eval-v2). Reads ONLY result JSONs produced by final_test_v2.py evaluate;
never reads test data. Statistics are the same as the validation ledgers: mean +- SD, per-seed values, paired differences with a t-based 95% CI,
exact sign-flip p (n=5 => minimum p = 0.0625; exploratory), no multiplicity correction.

usage: python scripts/final_test/analyze_final_test.py --results results_final_test --out results_final_test/ledgers
Outputs (CSV): ledger_final_test_per_run, ledger_final_test_arm_summary, ledger_final_test_paired_contrasts, ledger_fpr_shift, ledger_overlap_controlled.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PRIMARY_CONTRASTS = [("reference", "clean_fedavg"), ("reference", "scenario_fedavg_topk"), ("corrected", "reference"), ("reference_gaussian", "reference")]
FPR_FLAG = 0.25
METRICS = ("roc_auc", "pr_auc", "f1", "recall_adr", "precision", "fpr")


def load_results(results: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(results.glob("*/*/seed_*/final_test_result.json"))]


def per_run_table(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows:
        for ck, cr in (("best", r["best"]["primary"]), ("last", r["last"]["primary"])):
            rec = dict(dataset=r["dataset"], arm=r["arm"], seed=r["seed"], checkpoint=ck, test_rows=r["test_rows"], test_benign=r["test_benign"],
                       threshold=cr["threshold"], tp=cr["tp"], fp=cr["fp"], fn=cr["fn"], tn=cr["tn"], **{m: cr[m] for m in METRICS})
            ref = r.get("calibration_reference") or {}
            rec["calibration_fpr"] = ref.get("fpr")
            rec["fpr_shift_test_minus_calibration"] = cr["fpr"] - ref["fpr"] if ref.get("fpr") is not None and ck == "best" else np.nan
            rec["operational_flag_fpr_gt_0.25"] = bool(cr["fpr"] > FPR_FLAG)
            out.append(rec)
    return pd.DataFrame(out)


def arm_summary(per: pd.DataFrame) -> pd.DataFrame:
    g = per.groupby(["dataset", "arm", "checkpoint"])
    mean, sd = g[list(METRICS)].mean().add_suffix("_mean"), g[list(METRICS)].std(ddof=1).add_suffix("_sd")
    return mean.join(sd).join(g.size().rename("n_seeds")).reset_index()


def paired(per: pd.DataFrame, a: str, b: str, dataset: str, checkpoint: str, metric: str) -> dict | None:
    A = per[(per.dataset == dataset) & (per.arm == a) & (per.checkpoint == checkpoint)].sort_values("seed")
    B = per[(per.dataset == dataset) & (per.arm == b) & (per.checkpoint == checkpoint)].sort_values("seed")
    if len(A) < 2 or len(A) != len(B) or list(A.seed) != list(B.seed):
        return None
    d = A[metric].to_numpy() - B[metric].to_numpy()
    n, s = len(d), d.std(ddof=1)
    ci = stats.t.interval(0.95, n - 1, loc=d.mean(), scale=s / math.sqrt(n)) if s > 0 else (np.nan, np.nan)
    flips = [abs((d * np.array(f)).mean()) for f in itertools.product([1, -1], repeat=n)]
    return dict(dataset=dataset, contrast=f"{a} - {b}", checkpoint=checkpoint, metric=metric, n=n, mean_diff=d.mean(), sd=s, ci95_lo=ci[0], ci95_hi=ci[1],
                dz=d.mean() / s if s > 0 else np.nan, n_first_better=int((d > 0).sum()), n_second_better=int((d < 0).sum()),
                p_exact_signflip=float(np.mean([f >= abs(d.mean()) - 1e-15 for f in flips])), per_seed=json.dumps(np.round(d, 5).tolist()))


def contrasts_table(per: pd.DataFrame, pairs=PRIMARY_CONTRASTS) -> pd.DataFrame:
    rows = [paired(per, a, b, ds, ck, m) for a, b in pairs for ds in sorted(per.dataset.unique()) for ck in ("best", "last") for m in ("roc_auc", "f1", "recall_adr", "fpr")]
    return pd.DataFrame([r for r in rows if r])


def overlap_table(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows:
        for name, v in r.get("overlap_controlled", {}).items():
            for ck in ("best", "last"):
                m = v[f"{ck}_primary"]
                out.append(dict(dataset=r["dataset"], arm=r["arm"], seed=r["seed"], subset=name, checkpoint=ck, rows=v["rows"], **{k: m[k] for k in METRICS}))
    return pd.DataFrame(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    results, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = load_results(results)
    if not rows:
        raise SystemExit("no final_test_result.json files found")
    per = per_run_table(rows)
    per.to_csv(out / "ledger_final_test_per_run.csv", index=False)
    arm_summary(per).round(5).to_csv(out / "ledger_final_test_arm_summary.csv", index=False)
    contrasts_table(per).round(5).to_csv(out / "ledger_final_test_paired_contrasts.csv", index=False)
    per[per.checkpoint == "best"][["dataset", "arm", "seed", "calibration_fpr", "fpr", "fpr_shift_test_minus_calibration", "operational_flag_fpr_gt_0.25"]].to_csv(out / "ledger_fpr_shift.csv", index=False)
    overlap_table(rows).round(5).to_csv(out / "ledger_overlap_controlled.csv", index=False)
    print(f"analysed {len(rows)} runs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
