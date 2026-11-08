"""FINAL consolidated analysis: SUPP_V1 (246 verified, frozen) + SUPP_V2 (44 verified) + reused locked evidence (Phase 6C, Table 4 v2).
One row per experimental identity (dataset, arm, seed). Rules (documented in the report):
  * V2 regression controls (4) and chi0 seeds 12/14 are bit-identical re-executions of V1 identities: counted ONCE.
  * arm sens_chi0_dp (both datasets) is taken ENTIRELY from V2 (all five seeds under one code version; seeds 12/14 identical to V1).
  * CICIoT2023 participation (part_*) exists only under the V2 client-holdout protocol; it is never compared with Phase 6C CIC runs.
Read-only on all run directories. usage: python scripts/supp_final/analyse_final.py [--out Supplementary_Experiments_Package]"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "supp_v2"))
from supp_common import MANIFEST as V2_MANIFEST, V1_MANIFEST, load_manifest, sha256_file  # noqa: E402

_spec = importlib.util.spec_from_file_location("v1common", ROOT / "scripts" / "supp_v1" / "supp_common.py")
_v1 = importlib.util.module_from_spec(_spec); sys.modules["v1common"] = _v1; _spec.loader.exec_module(_v1)   # noqa: E702
ARMS = _v1.ARMS
DATASETS = ["unsw", "ciciot"]
OUT_V1, OUT_V2 = "results_supplementary_v1", "results_supplementary_v2"
LEDGER = pd.read_csv(ROOT / "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv").set_index(["dataset", "arm", "seed"])
P6C = json.loads((ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
T4 = json.loads((ROOT / "docs/table4_v2/EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
M1, M2 = load_manifest(V1_MANIFEST), load_manifest(V2_MANIFEST)
T4_ARMS = {r["arm"] for r in T4["runs"]}
V2_ARMS = {r["arm"] for r in M2["runs"]}
REUSED_P6C = ["reference", "reference_gaussian", "scenario_fedavg_topk", "ctl_imputation_none", "ctl_imputation_cap010", "ctl_imputation_postfilter"]
S5 = [12, 13, 14, 15, 16]
V1_DONE = {(r["dataset"], r["arm"], r["seed"]): r for r in M1["runs"] if (ROOT / r["out_dir"] / "COMPLETE.json").exists()}
V2_RUNS = {(r["dataset"], r["arm"], r["seed"]): r for r in M2["runs"]}


def resolve(ds, arm, seed):
    """-> (version label, run directory, manifest run record or None)"""
    k = (ds, arm, seed)
    if arm == "sens_chi0_dp" or (k in V2_RUNS and k not in V1_DONE):
        return "SUPP_V2", ROOT / V2_RUNS[k]["out_dir"], V2_RUNS[k]
    if k in V1_DONE:
        return "SUPP_V1", ROOT / V1_DONE[k]["out_dir"], V1_DONE[k]
    if arm in T4_ARMS:
        return "Table4_v2 (reused)", ROOT / "results_table4_controlled_v2" / ds / arm / f"seed_{seed}", None
    return "Phase6C (reused, locked)", ROOT / "results_phase6c" / ds / arm / f"seed_{seed}", None


def gini(c):
    c = np.sort(np.asarray(c, float)); n = len(c)
    return float((2 * np.sum(np.arange(1, n + 1) * c) / (n * c.sum()) - (n + 1) / n)) if c.sum() else 0.0


def extract(ds, arm, seed):
    ver, d, rec_m = resolve(ds, arm, seed)
    direct = not ver.startswith("Phase6C")          # corrected evaluation is built into current code; Phase 6C detection comes from the audited ledger
    fv = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
    meta = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))
    rec = json.loads((d / "COMPLETE.json").read_text(encoding="utf-8"))
    rr = json.loads((d / "run_record.json").read_text(encoding="utf-8"))
    rm = pd.read_csv(d / "round_metrics.csv"); rmr = rm[rm["round"] > 0]
    nm_all = pd.read_csv(d / "network_metrics.csv"); nm = nm_all[nm_all.selected == True]  # noqa: E712
    ag = pd.read_csv(d / "aggregation_diagnostics.csv")
    cfg = yaml.safe_load((d / "resolved_config.yaml").read_text(encoding="utf-8"))
    ncl, kper = int(cfg["fl"]["num_clients"]), int(cfg["fl"]["clients_per_round"])
    sel, last = fv["report_partition_at_selected_threshold"], fv["last_round_report_partition"]
    row = dict(dataset=ds, arm=arm, seed=seed, run_id=rec["run_id"], source=ver, out_dir=d.relative_to(ROOT).as_posix(),
               config_sha256=rec["config_sha256"], code_fingerprint=rec["code_fingerprint"], manifest_sha256=rec["manifest_sha256"],
               test_data_loaded=meta.get("test_data_loaded"), best_round=fv["best_round"], num_clients=ncl, clients_per_round=kper)
    for tag, blk, lc in (("sel", sel, "best"), ("last", last, "last")):
        for m, key, lcol in (("f1", "f1", "f1_audited"), ("auc", "roc_auc", "auc_audited"), ("fpr", "fpr", "fpr_audited"), ("recall", "recall_adr", "recall_audited")):
            row[f"{m}_{tag}"] = float(blk[key]) if direct else float(LEDGER.loc[(ds, arm, seed)][f"{lc}_{lcol}"])
        row[f"ap_{tag}"] = float(blk["pr_auc"])
        for c in ("tn", "fp", "fn", "tp"):
            row[f"{c}_{tag}"] = int(blk[c])
    row["detection_source"] = "run output (corrected evaluation)" if direct else "audited ledger (Phase 9); AP unaudited"
    row["auc_drop_sel_minus_last"] = row["auc_sel"] - row["auc_last"]
    row["val_auc_sd_last10_rounds"] = float(rmr.val_roc_auc.tail(10).std(ddof=1))
    # network (simulated)
    dl = nm[nm.update_delivered == True]  # noqa: E712
    row.update(delay_ms_delivered=float(dl.end_to_end_delay_ms.mean()), pdr_first_transmission=float(nm.pdr.mean()), update_delivery_rate=float(nm.update_delivered.mean()),
               path_stability=float(nm.path_stability.mean()), te_mbps_delivered=float(dl.transfer_efficiency_mbps.mean()),
               update_bytes_serialized=float(nm.update_bytes.iloc[0]), bytes_attempted=float(nm.update_bytes.sum()), bytes_delivered=float(dl.update_bytes.sum()),
               bytes_on_wire=float(nm.bytes_on_wire.sum()), attacker_exposure=float(nm.malicious.mean()), explicit_failure_rate=float(nm.explicit_client_failure.mean()))
    # updates actually received / retained / surrogate accounting
    ag["real"] = ~ag.is_recovered_update.astype(bool)
    ag["mal"] = ag.is_malicious_client.astype(bool)
    ag["kept_b"] = ag.kept.astype(bool)
    real, rec_rows = ag[ag.real], ag[~ag.real]
    mal, hon = real[real.mal], real[~real.mal]
    per_round = ag.groupby("round")
    sur_w = per_round.apply(lambda g: float(g.loc[~g.real, "applied_weight_share"].sum()), include_groups=False)
    kept_n = per_round.apply(lambda g: int(g.kept_b.sum()), include_groups=False)
    realkept_n = per_round.apply(lambda g: int((g.kept_b & g.real).sum()), include_groups=False)
    maxw = per_round.applied_weight_share.max()
    nR = len(rmr)
    row.update(rounds=nR, received_updates_total=int(rmr.received_updates.sum()), received_updates_per_round=float(rmr.received_updates.mean()),
               selected_updates_total=int(len(nm)), surrogate_updates_total=int(rmr.imputed_clients.sum()), surrogate_rows_in_aggregation=int(len(rec_rows)),
               retained_total_per_round=float(kept_n.mean()), retained_genuine_per_round=float(realkept_n.mean()),
               rounds_retained_lt10=float((kept_n < 10).mean()), min_retained=int(kept_n.min()), max_weight_share_max=float(maxw.max()), max_weight_share_mean=float(maxw.mean()),
               surrogate_weight_share_mean=float(sur_w.mean()), surrogate_weight_share_median=float(sur_w.median()), surrogate_weight_share_max=float(sur_w.max()),
               rounds_with_surrogate=float((per_round.apply(lambda g: (~g.real).any(), include_groups=False)).mean()), rounds_surrogate_only=float((realkept_n == 0).mean()),
               malicious_updates_received=int(len(mal)), malicious_updates_retained=int(mal.kept_b.sum()),
               malicious_retention=float(mal.kept_b.mean()) if len(mal) else np.nan, honest_updates_received=int(len(hon)),
               honest_rejection=float(1 - hon.kept_b.mean()) if len(hon) else np.nan)
    # participation (selection-count based; valid without a holdout)
    counts = nm.groupby("client_id").size().reindex(range(ncl), fill_value=0).to_numpy()
    selr = nm.groupby("round")["client_id"].apply(set)
    gap = 0
    for cid in range(ncl):
        cur = bst = 0
        for r in range(1, int(cfg["fl"]["rounds"]) + 1):
            cur = 0 if cid in selr.get(r, set()) else cur + 1
            bst = max(bst, cur)
        gap = max(gap, bst)
    row.update(selection_gini=gini(counts), clients_never_selected=int((counts == 0).sum()), coverage=float((counts > 0).mean()), max_selection_gap=int(gap))
    # privacy / noise
    priv = json.loads((d / "privacy_plan.json").read_text(encoding="utf-8"))
    dp = bool(priv.get("privacy_enabled", False))
    row.update(dp_enabled=dp, dp_noise_multiplier=priv.get("effective_noise_multiplier") if dp else np.nan,
               dp_noise_std_mean=float(rmr.privacy_noise_std.mean()) if dp else np.nan, dp_nsr_mean=float(rmr.privacy_noise_to_signal_ratio.mean()) if dp else np.nan,
               dp_clipped_fraction_mean=float(rmr.privacy_clipped_fraction.mean()) if dp else np.nan,
               dp_epsilon_planned_estimate=priv.get("planned_epsilon_estimate") if dp else np.nan, dp_certified=priv.get("epsilon_is_certified_guarantee") if dp else np.nan)
    # resources
    row.update(wall_seconds=rr.get("wall_seconds"), cpu_seconds=rr.get("cpu_seconds"), peak_working_set_mb=rr.get("peak_working_set_mb"),
               mean_local_train_seconds_per_client=float(rmr.mean_local_train_seconds.mean()), round_seconds_mean=float(rmr.round_seconds.mean()))
    if "no_valid_contribution" in rm.columns:
        row.update(abstention_rounds=int(rmr.no_valid_contribution.sum()), noisy_release_rounds=int(rmr.noisy_release.sum()) if dp else np.nan,
                   dp_eps_release_diag=float(rmr.privacy_epsilon_estimate.iloc[-1]) if dp else np.nan,
                   dp_eps_attempted_diag=float(rmr.privacy_epsilon_attempted_rounds_conservative.iloc[-1]) if dp else np.nan)
    row["empty_rounds_no_update_received"] = int((rmr.received_updates == 0).sum())
    tb = d / "timing_breakdown.json"
    if tb.exists():
        t = json.loads(tb.read_text(encoding="utf-8"))
        for k, v in t["seconds"].items():
            row[f"timed_{k}"] = v
        row["timed_local_train_calls"] = t["calls"].get("local_training_s")
    return row




# -------------------------------------------------------------------------------------------------------------- contrasts
LOWER = {"fpr_sel", "fpr_last", "delay_ms_delivered", "selection_gini", "clients_never_selected", "max_selection_gap", "auc_drop_sel_minus_last", "honest_rejection",
         "malicious_retention", "wall_seconds", "val_auc_sd_last10_rounds", "surrogate_weight_share_mean"}
STAT_METRICS = ["f1_sel", "auc_sel", "auc_last", "fpr_sel", "recall_sel", "val_auc_sd_last10_rounds", "malicious_retention", "honest_rejection", "received_updates_per_round",
                "surrogate_updates_total", "surrogate_weight_share_mean", "retained_genuine_per_round", "delay_ms_delivered", "pdr_first_transmission", "update_delivery_rate",
                "path_stability", "selection_gini", "clients_never_selected", "coverage", "max_selection_gap", "dp_noise_std_mean", "dp_nsr_mean", "worst_client_recall", "p10_client_recall", "mean_client_recall", "mean_recall_never_selected", "abstention_rounds"]


def contrasts():
    C = []   # (family, variant arm, reference arm, description, type)
    for pipe in ("ref", "fedavg"):
        base = f"atk_{pipe}_noatk"
        sf20 = "reference" if pipe == "ref" else "scenario_fedavg_topk"
        for cond in ("sf10", "sf30", "bsf20", "lf20"):
            C.append(("A_attack", f"atk_{pipe}_{cond}", base, f"{pipe}: attack effect vs no attack ({cond})", "attack effect (matched traces)"))
        C.append(("A_attack", sf20, base, f"{pipe}: attack effect vs no attack (sf20, reused locked arm)", "attack effect (matched traces)"))
        for cond in ("sf10", "sf30", "bsf20", "lf20"):
            pass
    for cond in ("noatk", "sf10", "sf30", "bsf20", "lf20"):
        C.append(("A_attack", f"atk_ref_{cond}", f"atk_fedavg_{cond}", f"MAD+surrogate reference vs FedAvg under {cond}", "pipeline contrast (bundle)"))
    C.append(("A_attack", "reference", "scenario_fedavg_topk", "MAD+surrogate reference vs FedAvg under sf20 (reused)", "pipeline contrast (bundle)"))
    # comment 5 (reused locked arms)
    C += [("5_surrogate", "reference", "ctl_imputation_none", "surrogate imputation ON (current) vs OFF", "single-factor: imputation"),
          ("5_surrogate", "ctl_imputation_cap010", "reference", "collectively capped surrogates (cap 0.10) vs current", "single-factor: surrogate cap"),
          ("5_surrogate", "ctl_imputation_cap010", "ctl_imputation_none", "capped surrogates vs no imputation", "single-factor: imputation (capped)"),
          ("5_surrogate", "ctl_imputation_postfilter", "reference", "real-only MAD then surrogates vs surrogates then MAD", "single-factor: processing order")]
    # 2x2
    C += [("C_interaction", "ix_routeoff_surron", "reference", "routing ON -> OFF with surrogates ON", "single-factor: routing"),
          ("C_interaction", "t4_e2_robust_random_path", "ctl_imputation_none", "routing ON -> OFF with surrogates OFF", "single-factor: routing"),
          ("C_interaction", "reference", "ctl_imputation_none", "surrogates OFF -> ON with routing ON", "single-factor: surrogates"),
          ("C_interaction", "ix_routeoff_surron", "t4_e2_robust_random_path", "surrogates OFF -> ON with routing OFF", "single-factor: surrogates")]
    # sensitivity
    for k, (ch, d) in {kk[5:]: (v["ch"], v["desc"]) for kk, v in ARMS.items() if kk.startswith("sens_")}.items():
        parent = ARMS[f"sens_{k}"]["parent"]
        C.append(("B_sensitivity", f"sens_{k}", parent, d + f" vs locked {parent}", "one-factor-at-a-time (other settings may co-vary)"))
    C.append(("B_sensitivity", "sens_chi0_dp", "reference_gaussian", "chi_rec=0 under central DP vs locked reference_gaussian (expected null)", "inertness check"))
    # participation
    for pol in ("topk", "coverage", "uniform"):
        C.append(("E_participation", f"part_{pol}_coup", f"part_{pol}_indep", f"{pol}: correlated vs independent network/data", "scenario effect"))
    for scen in ("indep", "coup"):
        C.append(("E_participation", f"part_uniform_{scen}", f"part_topk_{scen}", f"uniform vs top-k selection ({scen})", "selection policy"))
        C.append(("E_participation", f"part_coverage_{scen}", f"part_topk_{scen}", f"coverage-aware vs top-k selection ({scen})", "selection policy"))
    return C


def paired(P, fam, v, r, desc, typ, ds, metrics):
    a = P[(P.dataset == ds) & (P.arm == r)].set_index("seed")
    b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")
    seeds = sorted(set(a.index) & set(b.index))
    if len(seeds) < 3:
        return []
    out = []
    for m in metrics:
        if m not in P.columns:
            continue
        x, y = a.loc[seeds, m].astype(float), b.loc[seeds, m].astype(float)
        ok = x.notna() & y.notna()
        if ok.sum() < 3:
            continue
        dlt = (y[ok] - x[ok]).to_numpy(float); n = len(dlt); mu = float(dlt.mean()); sd = float(dlt.std(ddof=1)); se = sd / math.sqrt(n)
        tc = stats.t.ppf(0.975, n - 1)
        signs = np.array(list(itertools.product([1, -1], repeat=n)))
        pex = float((np.abs((signs * np.abs(dlt)).mean(1)) >= abs(mu) - 1e-15).mean())
        up, dn = int((dlt > 1e-12).sum()), int((dlt < -1e-12).sum())
        out.append(dict(family=fam, dataset=ds, variant=v, reference=r, factor=desc, comparison_type=typ, metric=m, n_pairs=n, mean_reference=float(x[ok].mean()),
                        mean_variant=float(y[ok].mean()), mean_diff=mu, sd_diff=sd, ci95_lo=mu - tc * se, ci95_hi=mu + tc * se, n_variant_higher=up, n_variant_lower=dn,
                        n_tied=n - up - dn, n_improved=dn if m in LOWER else up, n_deteriorated=up if m in LOWER else dn, exact_signflip_p=pex, min_attainable_exact_p=2 / 2 ** n,
                        per_seed_diffs="; ".join(f"{s}:{z:.6g}" for s, z in zip(np.array(seeds)[ok.to_numpy()], dlt)),
                        note=f"exploratory; n={n} pairs: smallest attainable two-sided exact p = {2 / 2 ** n:.4f}" + ("; no difference can reach p<0.05" if 2 / 2 ** n >= 0.05 else "")))
    return out


def interaction_rows(P):
    rows = []
    for ds in DATASETS:
        g = {a: P[(P.dataset == ds) & (P.arm == a)].set_index("seed") for a in ("reference", "ctl_imputation_none", "ix_routeoff_surron", "t4_e2_robust_random_path")}
        seeds = sorted(set.intersection(*[set(v.index) for v in g.values()]))
        if len(seeds) < 5:
            continue
        for m in STAT_METRICS:
            if m not in P.columns:
                continue
            dlt = ((g["reference"].loc[seeds, m] - g["ctl_imputation_none"].loc[seeds, m]) - (g["ix_routeoff_surron"].loc[seeds, m] - g["t4_e2_robust_random_path"].loc[seeds, m])).astype(float).dropna().to_numpy()
            n = len(dlt)
            if n < 3:
                continue
            mu, sd = float(dlt.mean()), float(dlt.std(ddof=1)); tc = stats.t.ppf(0.975, n - 1); se = sd / math.sqrt(n)
            signs = np.array(list(itertools.product([1, -1], repeat=n)))
            pex = float((np.abs((signs * np.abs(dlt)).mean(1)) >= abs(mu) - 1e-15).mean())
            rows.append(dict(family="C_interaction", dataset=ds, variant="interaction", reference="(surrogate effect | routing ON) - (surrogate effect | routing OFF)",
                             factor="routing x surrogate interaction contrast", comparison_type="2x2 interaction", metric=m, n_pairs=n, mean_diff=mu, sd_diff=sd,
                             ci95_lo=mu - tc * se, ci95_hi=mu + tc * se, exact_signflip_p=pex, min_attainable_exact_p=2 / 2 ** n,
                             per_seed_diffs="; ".join(f"{s}:{z:.6g}" for s, z in zip(seeds, dlt)), note=f"exploratory; n={n}; min attainable p={2 / 2 ** n:.4f}"))
    return rows



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Supplementary_Experiments_Package")
    PKG = ROOT / ap.parse_args().out
    PKG.mkdir(parents=True, exist_ok=True)
    keys = set(V1_DONE) | set(V2_RUNS)
    for ds in DATASETS:
        for s in S5:
            for arm in REUSED_P6C + ["t4_e2_robust_random_path"]:
                keys.add((ds, arm, s))
    # keep exactly one row per identity; V2 runs that duplicate a verified V1 identity (regression controls) are recorded as twins, not rows
    P = pd.DataFrame([extract(*k) for k in sorted(keys)])
    assert not P.duplicated(["dataset", "arm", "seed"]).any(), "duplicate identity"
    H = pd.read_csv(PKG / "SUPPLEMENTARY_HOLDOUT_CLIENT_METRICS.csv")
    Hs = H[H.checkpoint == "selected"].drop(columns=["checkpoint", "version", "run_id"])
    Hl = H[H.checkpoint == "last"].drop(columns=["checkpoint", "version", "run_id"]).rename(columns={c: c + "_last" for c in H.columns if c in ("worst_client_recall", "p10_client_recall", "mean_client_recall", "mean_recall_never_selected")})
    Hl = Hl[["dataset", "arm", "seed", "worst_client_recall_last", "p10_client_recall_last", "mean_client_recall_last"]]
    P = P.merge(Hs, on=["dataset", "arm", "seed"], how="left").merge(Hl, on=["dataset", "arm", "seed"], how="left")
    twins = {(r["dataset"], r["arm"], r["seed"]): r["run_id"] for r in M2["runs"]}
    P["regression_twin_v2_run_id"] = [twins.get((a, b, c)) if (a, b, c) in V1_DONE and (a, b, c) in twins and b != "sens_chi0_dp" else None for a, b, c in zip(P.dataset, P.arm, P.seed)]
    P["superseded_v1_twin"] = [(f"v1 verified run unsw/ciciot {b} seed {c} identical" if (a, b, c) in V1_DONE and b == "sens_chi0_dp" else None) for a, b, c in zip(P.dataset, P.arm, P.seed)]
    P["provenance_manifest_sha256"] = [M2["manifest_sha256"] if v == "SUPP_V2" else (M1["manifest_sha256"] if v == "SUPP_V1" else (T4["manifest_sha256"] if v.startswith("Table4") else P6C["manifest_sha256"])) for v in P.source]
    P.to_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv", index=False)
    num = [c for c in P.columns if P[c].dtype.kind in "fi" and c not in ("seed",)]
    S = P.groupby(["dataset", "arm", "source"])[num].agg(["mean", "std"])
    S.columns = [f"{c}_{s}" for c, s in S.columns]
    S["n_seeds"] = P.groupby(["dataset", "arm", "source"]).size()
    S["seeds"] = P.groupby(["dataset", "arm", "source"]).seed.apply(lambda x: ",".join(map(str, sorted(x))))
    S["run_ids"] = P.groupby(["dataset", "arm", "source"]).run_id.apply(lambda x: ";".join(sorted(x)))
    S.reset_index().to_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_SUMMARY.csv", index=False)
    PE = []
    for fam, v, r, desc, typ in contrasts():
        for ds in DATASETS:
            PE += paired(P, fam, v, r, desc, typ, ds, STAT_METRICS)
    PE += interaction_rows(P)
    pd.DataFrame(PE).to_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv", index=False)
    print(f"{len(P)} identity rows ({P.source.value_counts().to_dict()}); {len(PE)} paired rows")


if __name__ == "__main__":
    main()
