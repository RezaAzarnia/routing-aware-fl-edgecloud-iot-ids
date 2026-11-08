"""Read-only audit of (i) the effective weight cap / CapNormalize behaviour, (ii) whether chi_rec, sample-size weighting and surrogate down-weighting are active,
(iii) collective surrogate contribution, (iv) conformity of reused Phase 6C arms. Writes only into --out. Never modifies a run directory.
usage: python scripts/supp_v1/audit_weights.py --out DIR"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.privacy import capped_normalized_weights  # noqa: E402
from supp_common import ARMS, DATASETS, MANIFEST, OUT_ROOT, load_manifest, sha256_text_file  # noqa: E402

P6C = json.loads((ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
M = load_manifest(MANIFEST)


def rundir(ds, arm, seed):
    if arm in ARMS:
        return ROOT / OUT_ROOT / ds / arm / f"seed_{seed}"
    if arm.startswith("t4_"):
        return ROOT / "results_table4_controlled_v2" / ds / arm / f"seed_{seed}"
    return ROOT / "results_phase6c" / ds / arm / f"seed_{seed}"


def part_b():
    """Direct test of the implemented CapNormalize on adversarial raw weights, n = 1..10 (cap 0.1) and n = 11..20."""
    rng = np.random.default_rng(0)
    rows = []
    for n in range(1, 21):
        worst = 0.0
        for _ in range(2000):
            raw = rng.lognormal(0, 2.0, n) * rng.choice([1.0, 0.5, 100.0], n)          # wildly unequal sample sizes and surrogate factors
            w, mx = capped_normalized_weights(raw, 0.1)
            worst = max(worst, float(np.abs(np.array(w) - 1.0 / n).max()))
        rows.append(dict(n_retained=n, max_abs_deviation_from_uniform=worst, exactly_uniform=bool(worst < 1e-9)))
    return pd.DataFrame(rows)


def part_a(dp_runs):
    """Recorded weights of real runs: applied_weight_share of the kept updates vs 1/n and raw-weight heterogeneity."""
    rows = []
    for ds, arm, seed, kind in dp_runs:
        d = rundir(ds, arm, seed)
        f = d / "aggregation_diagnostics.csv"
        if not f.exists():
            continue
        ag = pd.read_csv(f)
        if "applied_weight_share" not in ag.columns:
            continue
        n_uniform = n_het_raw = n_rounds = 0
        maxdev = 0.0
        sur_share, sur_only, kept_n = [], 0, []
        for _, g in ag.groupby("round"):
            k = g[g.kept.astype(bool)]
            if len(k) == 0:
                continue
            n_rounds += 1
            dev = float(np.abs(k.applied_weight_share - 1.0 / len(k)).max())
            maxdev = max(maxdev, dev)
            n_uniform += dev < 1e-9
            n_het_raw += float(k.raw_weight.max() / max(k.raw_weight.min(), 1e-12)) > 1.0 + 1e-9
            s = float(k.loc[k.is_recovered_update.astype(bool), "applied_weight_share"].sum())
            sur_share.append(s)
            sur_only += int((~k.is_recovered_update.astype(bool)).sum() == 0)
            kept_n.append(len(k))
        rows.append(dict(dataset=ds, arm=arm, seed=seed, pipeline=kind, rounds=n_rounds, rounds_exactly_uniform=int(n_uniform), max_abs_dev_from_1_over_n=maxdev,
                         rounds_with_heterogeneous_raw_weights=int(n_het_raw), mean_retained=float(np.mean(kept_n)), max_retained=int(np.max(kept_n)),
                         surrogate_share_mean=float(np.mean(sur_share)), surrogate_share_median=float(np.median(sur_share)), surrogate_share_max=float(np.max(sur_share)),
                         rounds_surrogate_share_ge_half=int(np.sum(np.array(sur_share) >= 0.5)), rounds_surrogates_only=int(sur_only)))
    return pd.DataFrame(rows)


def part_d():
    """Do the reused Phase 6C arms match the required configuration / seeds / splits / definitions?"""
    runs = {(r["dataset"], r.get("arm") or r.get("variant"), r["seed"]): r for r in P6C["runs"]}
    rows = []
    flat = lambda d, p="": {k2: v2 for k, v in d.items() for k2, v2 in (flat(v, p + k + ".").items() if isinstance(v, dict) else {p + k: v}.items())}  # noqa: E731
    expected = {"ctl_imputation_none": {"failure.recovery_enabled": False}, "ctl_imputation_cap010": {"failure.surrogate_total_weight_cap": 0.1},
                "ctl_imputation_postfilter": {"aggregation.surrogate_handling": "post_filter_real_only"},
                "reference_gaussian": {"privacy.mode": "central_client", "privacy.target_epsilon": 10.0, "privacy.auto_calibrate_noise": True},
                "scenario_fedavg_topk": {"failure.recovery_enabled": False, "aggregation.method": "fedavg", "routing.selection_policy": "top_k"}}
    for ds in DATASETS:
        base = flat(yaml.safe_load((ROOT / f"configs/phase6c/{ds}_reference.yaml").read_text(encoding="utf-8")))
        for arm in ["reference"] + list(expected):
            cfgp = ROOT / f"configs/phase6c/{ds}_{arm}.yaml"
            cur = flat(yaml.safe_load(cfgp.read_text(encoding="utf-8")))
            diff = {k: (base.get(k), cur.get(k)) for k in set(base) | set(cur) if base.get(k) != cur.get(k) and not k.startswith("experiment.")}
            decl = expected.get(arm, {})
            ok_decl = set(diff) == set(decl) and all(cur.get(k) == v for k, v in decl.items())
            seeds_ok, hash_ok, split_ok, comp_ok = True, True, True, True
            ref_split = None
            for s in (12, 13, 14, 15, 16):
                r = runs.get((ds, arm, s))
                seeds_ok &= r is not None
                d = rundir(ds, arm, s)
                comp_ok &= (d / "COMPLETE.json").exists()
                if r is not None:
                    hash_ok &= sha256_text_file(cfgp) == r["config_sha256"]
                sp = json.loads((d / "validation_split_info.json").read_text(encoding="utf-8"))
                rs = json.loads((rundir(ds, "reference", s) / "validation_split_info.json").read_text(encoding="utf-8"))
                split_ok &= sp == rs
            rows.append(dict(dataset=ds, arm=arm, differs_from_reference_only_in_declared_fields=ok_decl, observed_diff=str(diff), seeds_12_16_in_locked_manifest=seeds_ok,
                             config_sha256_equals_manifest=hash_ok, validation_split_identical_to_reference_runs=split_ok, all_five_runs_complete=comp_ok))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    B = part_b()
    B.to_csv(out / "AUDIT_capnormalize_unit_test.csv", index=False)
    dp, nondp = [], []
    for ds in DATASETS:
        for s in (12, 13, 14, 15, 16):
            for arm in ("reference_gaussian", "t4_e3_dpfedavg_random_path", "t4_e4_proposed_eps20"):
                dp.append((ds, arm, s, "central-DP (cap active path)"))
            for arm in ("reference", "ctl_imputation_cap010", "ctl_imputation_postfilter", "ctl_imputation_none"):
                nondp.append((ds, arm, s, "no noise (plain weighted FedAvg path)"))
        for s in (12, 13, 14, 15, 16):
            for arm, v in ARMS.items():
                if s in v["seeds"][ds]:
                    kind = "central-DP (cap active path)" if v["parent"] == "reference_gaussian" else "no noise (plain weighted FedAvg path)"
                    (dp if kind.startswith("central") else nondp).append((ds, arm, s, kind))
    A = pd.concat([part_a(dp), part_a(nondp)], ignore_index=True)
    A.to_csv(out / "AUDIT_recorded_weights_per_run.csv", index=False)
    D = part_d()
    D.to_csv(out / "AUDIT_reused_phase6c_conformity.csv", index=False)
    g = A.groupby(["pipeline", "dataset", "arm"]).agg(runs=("seed", "size"), rounds=("rounds", "sum"), uniform=("rounds_exactly_uniform", "sum"), het_raw=("rounds_with_heterogeneous_raw_weights", "sum"),
                                                      maxdev=("max_abs_dev_from_1_over_n", "max"), sur_mean=("surrogate_share_mean", "mean"), sur_max=("surrogate_share_max", "max"),
                                                      surrogate_only_rounds=("rounds_surrogates_only", "sum"), max_retained=("max_retained", "max")).reset_index()
    g.to_csv(out / "AUDIT_recorded_weights_summary.csv", index=False)
    print("CapNormalize unit test: exactly uniform for n<=10 in all trials:", bool(B[B.n_retained <= 10].exactly_uniform.all()),
          "| n>10 non-uniform allowed:", bool((~B[B.n_retained > 10].exactly_uniform).any()))
    print(g.to_string())
    print(D[["dataset", "arm", "differs_from_reference_only_in_declared_fields", "seeds_12_16_in_locked_manifest", "config_sha256_equals_manifest",
             "validation_split_identical_to_reference_runs", "all_five_runs_complete"]].to_string())


if __name__ == "__main__":
    main()
