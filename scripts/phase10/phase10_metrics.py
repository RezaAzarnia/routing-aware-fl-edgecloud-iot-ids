"""Phase 10 outcome metrics (read-only on run folders; training/validation data only) and the frozen analysis.

Per run:
  pdr (first-transmission), update_delivery_ratio (updates RECEIVED by the server / selected), delay_ms (mean over received updates), gini, never_selected,
  max_selection_gap (longest run of rounds a client was not selected, max over clients), malicious_share_of_selected, best/last AUC and F1 (report partition),
  and client-level HELD-OUT recall (worst, p10, mean) - valid only because each client's holdout (fl.client_holdout_fraction) was never used for training,
  selection or thresholds; a client's recall is reported only if its holdout holds >= MIN_POS attack samples (else NaN, excluded and counted).
NOT measurable validly: client-level recall for runs without a holdout (the Phase 6C client_level_recall.csv scores each client's own TRAINING data, which the
model was fit on for selected clients, so it is optimistic for them and cannot support a starvation comparison).
usage:  python scripts/phase10/phase10_metrics.py analyze --results results_phase10 --out results_phase10/ledgers
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
MIN_POS = 10


def gini(v) -> float:
    v = np.sort(np.asarray(v, dtype=float))
    n = len(v)
    return 0.0 if v.sum() == 0 else float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum()))


def holdout_client_eval(run_dir: Path, cfg) -> pd.DataFrame:
    """Recall/FPR of the best global model at its recorded calibration threshold on each client's HELD-OUT samples. Reads train data only."""
    import torch

    from src.data import load_dataset
    from src.experiment import _model_factory
    from src.partitioning import make_partitions, split_client_holdout

    bundle = load_dataset(cfg.data, seed=cfg.experiment.seed, load_test=False)
    parts = make_partitions(bundle.y_train, num_clients=cfg.fl.num_clients, strategy=cfg.fl.partition, seed=cfg.experiment.seed,
                            dirichlet_alpha=cfg.fl.dirichlet_alpha, min_client_samples=cfg.fl.min_client_samples)
    _, hold = split_client_holdout(parts, cfg.fl.client_holdout_fraction, cfg.experiment.seed)
    model = _model_factory(cfg, bundle.X_train.shape[1])()
    model.load_state_dict(torch.load(run_dir / "best_model_state.pt", map_location="cpu", weights_only=True))
    model.eval()
    thr = float(json.loads((run_dir / "final_validation_metrics.json").read_text(encoding="utf-8"))["selected_operating_point"]["threshold"])
    nm = pd.read_csv(run_dir / "network_metrics.csv")
    times = nm.groupby("client_id").size().reindex(range(cfg.fl.num_clients), fill_value=0)
    rows = []
    with torch.no_grad():
        for cid, idx in enumerate(hold):
            if len(idx) == 0:
                rows.append({"client_id": cid, "holdout_samples": 0, "holdout_attack": 0, "recall": np.nan, "fpr": np.nan, "times_selected": int(times[cid])})
                continue
            p = torch.softmax(model(torch.from_numpy(bundle.X_train[idx]).float()), 1)[:, 1].numpy()
            y = bundle.y_train[idx]
            pred = p >= thr
            rows.append({"client_id": cid, "holdout_samples": int(len(idx)), "holdout_attack": int((y == 1).sum()),
                         "recall": float(pred[y == 1].mean()) if (y == 1).sum() >= MIN_POS else np.nan,
                         "fpr": float(pred[y == 0].mean()) if (y == 0).sum() >= MIN_POS else np.nan, "times_selected": int(times[cid])})
    return pd.DataFrame(rows)


def run_metrics(run_dir: Path, with_holdout: bool = True) -> dict:
    from src.config import Config

    cfg = Config.from_yaml(run_dir / "resolved_config.yaml")
    nm = pd.read_csv(run_dir / "network_metrics.csv")
    rm = pd.read_csv(run_dir / "round_metrics.csv")
    rm = rm[rm["round"] > 0]
    fin = json.loads((run_dir / "final_validation_metrics.json").read_text(encoding="utf-8"))
    counts = nm.groupby("client_id").size().reindex(range(cfg.fl.num_clients), fill_value=0).to_numpy()
    sel = nm.groupby("round")["client_id"].apply(set)
    gap = 0
    for cid in range(cfg.fl.num_clients):
        cur = best = 0
        for r in range(1, cfg.fl.rounds + 1):
            cur = 0 if cid in sel.get(r, set()) else cur + 1
            best = max(best, cur)
        gap = max(gap, best)
    rec = nm["received_by_server"].astype(bool)
    out = {"pdr": float(rm["mean_pdr"].mean()), "update_delivery_ratio": float(rec.mean()), "delay_ms": float(nm.loc[rec, "end_to_end_delay_ms"].mean()),
           "gini": gini(counts), "never_selected": int((counts == 0).sum()), "max_selection_gap": int(gap),
           "malicious_share_of_selected": float(nm["malicious"].astype(bool).mean()),
           "best_auc": fin["report_partition_at_selected_threshold"]["roc_auc"], "best_f1": fin["report_partition_at_selected_threshold"]["f1"],
           "last_auc": fin["last_round_report_partition"]["roc_auc"], "last_f1": fin["last_round_report_partition"]["f1"]}
    if with_holdout and cfg.fl.client_holdout_fraction > 0:
        h = holdout_client_eval(run_dir, cfg)
        valid = h["recall"].dropna()
        never = h[(h.times_selected == 0) & h.recall.notna()]
        out.update(worst_client_recall=float(valid.min()) if len(valid) else np.nan, p10_client_recall=float(valid.quantile(0.10)) if len(valid) else np.nan,
                   mean_client_recall=float(valid.mean()) if len(valid) else np.nan, mean_recall_never_selected=float(never.recall.mean()) if len(never) else np.nan,
                   clients_with_valid_recall=int(len(valid)), clients_without_valid_recall=int(len(h) - len(valid)))
        h.to_csv(run_dir / "client_holdout_recall.csv", index=False)
    return out


def paired(df: pd.DataFrame, a: str, b: str, metric: str, scenario: str | None = None) -> dict | None:
    sub = df if scenario is None else df[df.scenario == scenario]
    A, B = sub[sub.policy == a].sort_values("seed"), sub[sub.policy == b].sort_values("seed")
    if len(A) < 2 or list(A.seed) != list(B.seed) or metric not in A:
        return None
    d = A[metric].to_numpy(float) - B[metric].to_numpy(float)
    if np.isnan(d).any():
        return None
    return _stats(d, f"{a} - {b}", metric, scenario or "all")


def _stats(d: np.ndarray, label: str, metric: str, scenario: str) -> dict:
    n, s = len(d), d.std(ddof=1)
    ci = stats.t.interval(0.95, n - 1, loc=d.mean(), scale=s / math.sqrt(n)) if s > 0 else (np.nan, np.nan)
    flips = [abs((d * np.array(f)).mean()) for f in itertools.product([1, -1], repeat=n)]
    return dict(contrast=label, scenario=scenario, metric=metric, n=n, mean_diff=d.mean(), sd=s, dz=d.mean() / s if s > 0 else np.nan, ci95_lo=ci[0], ci95_hi=ci[1],
                n_first_higher=int((d > 0).sum()), n_second_higher=int((d < 0).sum()), p_exact_signflip=float(np.mean([f >= abs(d.mean()) - 1e-15 for f in flips])),
                per_seed=json.dumps(np.round(d, 5).tolist()))


def interaction(df: pd.DataFrame, a: str, b: str, metric: str) -> dict | None:
    """(a-b) in coupled minus (a-b) in independent, paired by seed."""
    out = []
    for sc in ("coupled", "independent"):
        s = df[df.scenario == sc]
        A, B = s[s.policy == a].sort_values("seed"), s[s.policy == b].sort_values("seed")
        if len(A) < 2 or list(A.seed) != list(B.seed) or metric not in A:
            return None
        out.append(A[metric].to_numpy(float) - B[metric].to_numpy(float))
    d = out[0] - out[1]
    return None if np.isnan(d).any() else _stats(d, f"({a} - {b})[coupled] - ({a} - {b})[independent]", metric, "interaction")


PRIMARY = [("history_ucb", "oracle_topk", "update_delivery_ratio", "independent"), ("history_ucb", "oracle_topk", "gini", "independent"),
           ("oracle_topk", "uniform", "p10_client_recall", "coupled"), ("history_ucb", "oracle_topk", "p10_client_recall", "coupled")]
SECONDARY_METRICS = ["pdr", "delay_ms", "never_selected", "max_selection_gap", "malicious_share_of_selected", "worst_client_recall", "mean_client_recall", "best_auc", "last_auc", "best_f1", "last_f1"]
POLICIES = ["oracle_topk", "oracle_coverage", "uniform", "history_ucb"]


def analyze(results: Path, out: Path, with_holdout: bool = True) -> None:
    rows = []
    for d in sorted(results.glob("*/*/seed_*")):
        if not (d / "COMPLETE.json").exists() and not (d / "final_validation_metrics.json").exists():
            continue
        policy_scenario = d.parent.name
        scenario = "coupled" if policy_scenario.endswith("__coupled") else "independent"
        policy = policy_scenario.rsplit("__", 1)[0]
        rows.append({"policy": policy, "scenario": scenario, "seed": int(d.name.split("_")[1]), **run_metrics(d, with_holdout)})
    df = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "ledger_phase10_per_run.csv", index=False)
    g = df.groupby(["scenario", "policy"])
    num = [c for c in df.columns if c not in ("policy", "scenario", "seed")]
    summ = g[num].mean().add_suffix("_mean").join(g[num].std(ddof=1).add_suffix("_sd")).join(g.size().rename("n_seeds"))
    summ.round(5).to_csv(out / "ledger_phase10_arm_summary.csv")
    prim = [paired(df, a, b, m, sc) for a, b, m, sc in PRIMARY]
    pd.DataFrame([r for r in prim if r]).round(5).to_csv(out / "ledger_phase10_primary_contrasts.csv", index=False)
    sec = []
    for sc in ("independent", "coupled"):
        for a, b in itertools.combinations(POLICIES, 2):
            for m in ["update_delivery_ratio", "gini", "p10_client_recall"] + SECONDARY_METRICS:
                sec.append(paired(df, a, b, m, sc))
    for a, b in itertools.combinations(POLICIES, 2):
        for m in ["update_delivery_ratio", "gini", "p10_client_recall", "worst_client_recall", "best_auc"]:
            sec.append(interaction(df, a, b, m))
    pd.DataFrame([r for r in sec if r]).round(5).to_csv(out / "ledger_phase10_secondary_contrasts.csv", index=False)
    print(f"analysed {len(df)} runs -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["analyze"])
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    analyze(Path(a.results), Path(a.out))
