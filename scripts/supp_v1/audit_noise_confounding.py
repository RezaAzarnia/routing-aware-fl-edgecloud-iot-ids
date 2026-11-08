"""Read-only audit: does the Table 5 'Added Gaussian' contrast change only the Gaussian noise, or also the effective weighting / clipping?
Compares configs, recorded per-round applied weights, clipping behaviour and trace identity of the locked controlled-ablation arms and the Table 4 DP arms.
usage: python scripts/supp_v1/audit_noise_confounding.py --out DIR"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
AB = ROOT / "results_ablation_controlled_v2"
ARMS = {"abl_reference_repro": "no-noise reference (privacy.mode none)", "abl_privacy_clip_only": "central_client, noise multiplier 0 (clipping + capped weights)",
        "abl_reference_gaussian_repro": "central_client + Gaussian (eps~10)", "abl_no_filter": "FedAvg, privacy none"}


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        o.update(flat(v, p + k + ".") if isinstance(v, dict) else {p + k: v})
    return o


def run_dir(ds, arm, seed):
    return AB / "runs" / ds / arm / f"seed_{seed}"


def weights_stats(d):
    ag = pd.read_csv(d / "aggregation_diagnostics.csv")
    nu = het = rounds = 0
    maxdev = 0.0
    for _, g in ag.groupby("round"):
        k = g[g.kept.astype(bool)]
        if not len(k):
            continue
        rounds += 1
        dev = float(np.abs(k.applied_weight_share - 1.0 / len(k)).max())
        maxdev = max(maxdev, dev)
        nu += dev < 1e-9
        het += float(k.raw_weight.max() / max(k.raw_weight.min(), 1e-12)) > 1 + 1e-9
    rm = pd.read_csv(d / "round_metrics.csv"); rm = rm[rm["round"] > 0]
    return dict(rounds=rounds, rounds_exactly_uniform=int(nu), rounds_heterogeneous_raw=int(het), max_dev_from_1_over_n=maxdev,
                clipped_fraction_mean=float(rm.privacy_clipped_fraction.mean()), noise_std_mean=float(rm.privacy_noise_std.mean()),
                post_clip_norm_max=float(ag.post_clip_l2_norm.max()), pre_clip_norm_median=float(ag.pre_clip_l2_norm.median()))


def sig(d):
    nm = pd.read_csv(d / "network_metrics.csv"); nm = nm[nm.selected == True]  # noqa: E712
    return hashlib.sha256(nm[["round", "client_id", "explicit_client_failure", "update_delivered", "end_to_end_delay_ms"]].round(9).to_csv(index=False).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    rows, ident = [], []
    for ds in ("unsw", "ciciot"):
        cfg = {a: flat(yaml.safe_load((ROOT / f"configs/ablation_v2/{ds}_{a}.yaml").read_text(encoding="utf-8"))) for a in ARMS}
        for a, b in (("abl_privacy_clip_only", "abl_reference_repro"), ("abl_reference_gaussian_repro", "abl_privacy_clip_only"), ("abl_reference_gaussian_repro", "abl_reference_repro")):
            diff = {k: (cfg[b].get(k), cfg[a].get(k)) for k in set(cfg[a]) | set(cfg[b]) if cfg[a].get(k) != cfg[b].get(k) and not k.startswith("experiment.")}
            ident.append(dict(dataset=ds, variant=a, reference=b, config_differences=str(diff)))
        for arm in ARMS:
            for seed in (12, 13, 14, 15, 16):
                d = run_dir(ds, arm, seed)
                if (d / "aggregation_diagnostics.csv").exists():
                    rows.append(dict(dataset=ds, arm=arm, seed=seed, **weights_stats(d)))
        same = [sig(run_dir(ds, "abl_privacy_clip_only", s)) == sig(run_dir(ds, "abl_reference_gaussian_repro", s)) == sig(run_dir(ds, "abl_reference_repro", s))
                for s in (12, 13, 14, 15, 16) if (run_dir(ds, "abl_reference_repro", s) / "network_metrics.csv").exists()]
        ident.append(dict(dataset=ds, variant="trace identity (selected clients, failures, delivery) across reference_repro / clip_only / gaussian", reference="-",
                          config_differences=f"identical in {sum(same)}/{len(same)} seeds"))
    R = pd.DataFrame(rows)
    R.to_csv(out / "AUDIT_ablation_weights_per_run.csv", index=False)
    pd.DataFrame(ident).to_csv(out / "AUDIT_ablation_config_differences.csv", index=False)
    S = R.groupby(["dataset", "arm"]).agg(runs=("seed", "size"), rounds=("rounds", "sum"), uniform=("rounds_exactly_uniform", "sum"), het_raw=("rounds_heterogeneous_raw", "sum"),
                                          maxdev=("max_dev_from_1_over_n", "max"), clipped=("clipped_fraction_mean", "mean"), noise_std=("noise_std_mean", "mean")).reset_index()
    S.to_csv(out / "AUDIT_ablation_weights_summary.csv", index=False)
    # published contrasts (locked results) and the existing weighting-only control
    P = pd.read_csv(AB / "ablation_paired_comparisons.csv")
    keep = P[(P.metric == "auc_best") & (P.variant.isin(["abl_privacy_clip_only", "abl_reference_gaussian_repro", "ctl_weighting_uniform", "abl_no_filter"]))]
    keep[["dataset", "variant", "reference", "single_factor", "mean_diff", "ci95_lo", "ci95_hi", "n_improved", "n_deteriorated"]].to_csv(out / "AUDIT_ablation_contrasts_auc_best.csv", index=False)
    print(pd.DataFrame(ident).to_string())
    print(S.to_string())
    print(keep[["dataset", "variant", "reference", "mean_diff", "ci95_lo", "ci95_hi", "n_improved", "n_deteriorated"]].round(4).to_string())


if __name__ == "__main__":
    main()
