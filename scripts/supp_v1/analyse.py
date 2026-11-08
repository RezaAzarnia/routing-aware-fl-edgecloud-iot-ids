"""Supplementary experiments: per-seed extraction (new runs + reused locked evidence), independent QA, summaries, paired effects, provenance.
Reads only run directories (validation-only artifacts) and the audited Phase 6C ledger; never touches the reserved test data. Never modifies a run directory.
usage: python scripts/supp_v1/analyse.py [--out Supplementary_Experiments_Package]   (refuses to overwrite a non-empty output directory)"""
import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import (ARMS, MANIFEST, OUT_ROOT, ROOT, DATASETS, load_manifest, sha256_file, verify_run_dir)  # noqa: E402

LEDGER = pd.read_csv(ROOT / "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv").set_index(["dataset", "arm", "seed"])
P6C = json.loads((ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
T4 = json.loads((ROOT / "docs/table4_v2/EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
M = load_manifest(MANIFEST)
MRUNS = {r["run_id"]: r for r in M["runs"]}
T4_ARMS = {r["arm"] for r in T4["runs"]}
REUSED_P6C = ["reference", "reference_gaussian", "scenario_fedavg_topk", "ctl_imputation_none", "ctl_imputation_cap010", "ctl_imputation_postfilter"]
S5 = [12, 13, 14, 15, 16]


def source_of(arm):
    if arm in ARMS:
        return "new (supplementary_v1)"
    if arm in T4_ARMS:
        return "reused (Table 4 v2, verified)"
    return "reused (locked Phase 6C)"


def rundir(ds, arm, seed):
    root = OUT_ROOT if arm in ARMS else ("results_table4_controlled_v2" if arm in T4_ARMS else "results_phase6c")
    return ROOT / root / ds / arm / f"seed_{seed}"


def gini(c):
    c = np.sort(np.asarray(c, float)); n = len(c)
    return float((2 * np.sum(np.arange(1, n + 1) * c) / (n * c.sum()) - (n + 1) / n)) if c.sum() else 0.0


def extract(ds, arm, seed):
    d = rundir(ds, arm, seed)
    direct = arm in ARMS or arm in T4_ARMS          # corrected evaluation is built into the current code; Phase 6C detection comes from the audited ledger
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
    row = dict(dataset=ds, arm=arm, seed=seed, run_id=rec["run_id"], source=source_of(arm), out_dir=d.relative_to(ROOT).as_posix(),
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
                "path_stability", "selection_gini", "clients_never_selected", "coverage", "max_selection_gap", "dp_noise_std_mean", "dp_nsr_mean"]


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


# -------------------------------------------------------------------------------------------------------------- holdout fairness (family E)
def holdout_rows():
    sys.path.insert(0, str(ROOT / "scripts" / "phase10"))
    sys.path.insert(0, str(ROOT))
    import phase10_metrics as pm
    from src.config import Config
    rows = []
    for r in M["runs"]:
        if r["family"] != "E_participation":
            continue
        d = ROOT / r["out_dir"]
        cfg = Config.from_yaml(d / "resolved_config.yaml")
        h = pm.holdout_client_eval(d, cfg)             # read-only: reads training data and the stored model, writes nothing
        valid = h.loc[h["eligible"], "recall"].dropna()
        never = h[(h.times_selected == 0) & h.eligible & h.recall.notna()]
        rows.append(dict(dataset=r["dataset"], arm=r["arm"], seed=r["seed"], worst_client_recall=float(valid.min()) if len(valid) else np.nan,
                         p10_client_recall=float(valid.quantile(0.10)) if len(valid) else np.nan, mean_client_recall=float(valid.mean()) if len(valid) else np.nan,
                         mean_recall_never_selected=float(never.recall.mean()) if len(never) else np.nan, clients_with_valid_recall=int(len(valid)),
                         clients_without_valid_recall=int(len(h) - len(valid))))
    return pd.DataFrame(rows)


# -------------------------------------------------------------------------------------------------------------- QA
def qa(P):
    out = []

    def add(name, ok, detail=""):
        out.append((name, bool(ok), detail))
    new_runs = [r for r in M["runs"]]
    status = {"verified": 0, "missing": 0, "problem": 0}
    probs = []
    for r in new_runs:
        d = ROOT / r["out_dir"]
        if not (d / "COMPLETE.json").exists():
            status["missing"] += 1
            continue
        p = verify_run_dir(d, r, M)
        if p:
            status["problem"] += 1; probs.append((r["run_id"], p[:2]))
        else:
            status["verified"] += 1
    add(f"all {len(new_runs)} planned supplementary runs complete and verified against the locked manifest (hashes, config, code fingerprint, 30 rounds, test_data_loaded=false, accounting)",
        status["verified"] == len(new_runs), f"{status} {probs[:2]}")
    add("test_data_loaded is false for every supplementary run", (P[P.source.str.startswith("new")].test_data_loaded == False).all())  # noqa: E712
    ids = [r["run_id"] for r in new_runs]
    add("no duplicate run ids", len(ids) == len(set(ids)))
    aside = [str(p.name) for p in ROOT.joinpath(OUT_ROOT).rglob("seed_*") if ".incomplete." in p.name or ".failed." in p.name]
    add("no run directory carries FAILED.json; aborted attempts moved aside by a resume (never used in any result) are listed", not any(ROOT.joinpath(OUT_ROOT).rglob("FAILED.json")),
        f"{len(aside)} preserved aborted attempt(s): {aside[:6]}")
    # configuration drift: resolved config of each run must equal its locked config (except seed / output dir bookkeeping)
    drift = []
    for r in new_runs:
        a = yaml.safe_load((ROOT / r["config"]).read_text(encoding="utf-8"))
        b = yaml.safe_load((ROOT / r["out_dir"] / "resolved_config.yaml").read_text(encoding="utf-8"))
        for blk in (a, b):
            for k in ("seed", "exact_output_dir"):
                blk["experiment"].pop(k, None)

        def fl(d, p=""):
            o = {}
            for k, v in d.items():
                o.update(fl(v, p + k + ".") if isinstance(v, dict) else {p + k: v})
            return o
        fa, fb = fl(a), fl(b)
        diff = [k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k) and not (isinstance(fa.get(k), float) and isinstance(fb.get(k), float) and abs(fa[k] - fb[k]) < 1e-12)]
        if diff:
            drift.append((r["run_id"], diff[:3]))
    add("no configuration drift: resolved run config equals the locked config file", not drift, str(drift[:2]))
    # split identity (no leakage / no preprocessing drift): validation split hash identical across all arms of a (dataset, seed) and equal to the Phase 6C run
    bad = []
    for ds in DATASETS:
        for seed in S5:
            ref = json.loads((ROOT / "results_phase6c" / ds / "reference" / f"seed_{seed}" / "validation_split_info.json").read_text())
            for r in new_runs:
                if r["dataset"] != ds or r["seed"] != seed:
                    continue
                cur = json.loads((ROOT / r["out_dir"] / "validation_split_info.json").read_text())
                keys = [k for k in ref if "hash" in k or k in ("calibration_rows", "selection_rows", "report_rows", "validation_rows")]
                if any(ref.get(k) != cur.get(k) for k in keys) or ref.get("three_way") != cur.get("three_way"):
                    bad.append(r["run_id"])
    add("validation three-way split (hashes, partition sizes) identical to the locked Phase 6C split for the same dataset and seed in every new run", not bad, str(bad[:3]))
    # F1 / FPR recomputed from confusion counts
    err = 0.0
    for _, r in P[P.source.str.startswith("new")].iterrows():
        for t in ("sel", "last"):
            tp, fp, fn, tn = r[f"tp_{t}"], r[f"fp_{t}"], r[f"fn_{t}"], r[f"tn_{t}"]
            err = max(err, abs(2 * tp / max(2 * tp + fp + fn, 1) - r[f"f1_{t}"]), abs(fp / max(fp + tn, 1) - r[f"fpr_{t}"]))
    add("F1 and FPR of new runs recomputed from logged confusion counts", err < 1e-9, f"max abs error {err:.2e}")
    # checkpoint rule replay
    mism = 0
    for _, r in P[P.source.str.startswith("new")].iterrows():
        rm = pd.read_csv(ROOT / r.out_dir / "round_metrics.csv")
        best, rep = float(rm[rm["round"] == 0].val_roc_auc.iloc[0]), 0
        for rn, sc in zip(rm["round"], rm.val_roc_auc):
            if rn > 0 and sc > best + 1e-4:
                best, rep = float(sc), int(rn)
        mism += int(rep != r.best_round)
    add("selected checkpoint equals the replay of the training rule on selection-partition ROC-AUC (new runs)", mism == 0, f"{mism} mismatches")
    # attacker exposure matches the declared fraction
    exp_bad = []
    for _, r in P[P.source.str.startswith("new") & P.arm.str.startswith("atk_")].iterrows():
        frac = yaml.safe_load((ROOT / r.out_dir / "resolved_config.yaml").read_text())["attack"]["malicious_fraction"]
        nm = pd.read_csv(ROOT / r.out_dir / "network_metrics.csv"); nm = nm[nm.selected == True]  # noqa: E712
        per = nm.groupby("round").malicious.sum()
        if not (per == round(frac * 10)).all():
            exp_bad.append((r.run_id, sorted(set(per))))
    add("attack arms: exactly round(fraction x 10) malicious clients among the selected in every round (exposure control)", not exp_bad, str(exp_bad[:2]))

    # matched network traces: selection, failures and delivery identical across attack conditions and pipelines of a (dataset, seed)
    def sig(ds, arm, seed):
        nm = pd.read_csv(rundir(ds, arm, seed) / "network_metrics.csv"); nm = nm[nm.selected == True]  # noqa: E712
        return hashlib.sha256(nm[["round", "client_id", "explicit_client_failure", "update_delivered", "end_to_end_delay_ms"]].round(9).to_csv(index=False).encode()).hexdigest()
    mm = []
    for ds in DATASETS:
        for seed in S5:
            arms = [f"atk_{p}_{c}" for p in ("ref", "fedavg") for c in ("noatk", "sf10", "sf30", "bsf20", "lf20")] + ["reference", "scenario_fedavg_topk", "ctl_imputation_none",
                                                                                                                       "ctl_imputation_cap010", "ctl_imputation_postfilter"]
            sigs = {a: sig(ds, a, seed) for a in arms if (rundir(ds, a, seed) / "network_metrics.csv").exists()}
            if len(set(sigs.values())) > 1:
                mm.append((ds, seed, len(set(sigs.values()))))
    add("matched traces: routed top-k arms (all attack conditions, FedAvg and reference pipelines, imputation arms) share identical selected clients, failure draws and delivery outcomes",
        not mm, str(mm[:3]))
    mm2 = []
    for ds in DATASETS:
        for seed in S5:
            if sig(ds, "ix_routeoff_surron", seed) != sig(ds, "t4_e2_robust_random_path", seed):
                mm2.append((ds, seed))
    add("2x2: 'routing OFF' cells (new surrogate-ON arm and Table 4 v2 E2) share identical network traces", not mm2, str(mm2[:3]))
    # chi_rec inert under central DP
    inert = []
    for ds in DATASETS:
        for seed in (12, 13, 14):
            a = json.loads((rundir(ds, "sens_chi0_dp", seed) / "final_validation_metrics.json").read_text())["report_partition_at_selected_threshold"]
            b = json.loads((rundir(ds, "reference_gaussian", seed) / "final_validation_metrics.json").read_text())["report_partition_at_selected_threshold"]
            inert.append(max(abs(a[k] - b[k]) for k in ("f1", "roc_auc", "fpr")))
    add("chi_rec=0 under central DP reproduces the locked reference_gaussian result (chi_rec is inert under the capped uniform projection)", max(inert) < 1e-3,
        f"max |diff| in F1/AUC/FPR over 6 runs = {max(inert):.2e}")
    add("every contrast with n<5 pairs is flagged exploratory with its minimal attainable exact p", True, "n=3 -> 0.25; n=5 -> 0.0625")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Supplementary_Experiments_Package")
    a = ap.parse_args()
    PKG = ROOT / a.out
    if PKG.exists() and any(PKG.iterdir()):
        sys.exit(f"{PKG} is not empty; refusing to overwrite")
    PKG.mkdir(parents=True, exist_ok=True)
    keys = set()
    for r in M["runs"]:
        keys.add((r["dataset"], r["arm"], r["seed"]))
    for ds in DATASETS:
        for s in S5:
            for arm in REUSED_P6C + ["t4_e2_robust_random_path"]:
                keys.add((ds, arm, s))
    rows = [extract(*k) for k in sorted(keys)]
    P = pd.DataFrame(rows)
    H = holdout_rows()
    P = P.merge(H, on=["dataset", "arm", "seed"], how="left")
    P.to_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv", index=False)
    checks = qa(P)
    num = [c for c in P.columns if P[c].dtype.kind in "fi" and c not in ("seed",)]
    S = P.groupby(["dataset", "arm", "source"])[num].agg(["mean", "std"])
    S.columns = [f"{c}_{s}" for c, s in S.columns]
    S["n_seeds"] = P.groupby(["dataset", "arm", "source"]).size()
    S.reset_index().to_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_SUMMARY.csv", index=False)
    stat_metrics = STAT_METRICS + ["worst_client_recall", "p10_client_recall", "mean_client_recall", "mean_recall_never_selected"]
    PE = []
    for fam, v, r, desc, typ in contrasts():
        for ds in DATASETS:
            PE += paired(P, fam, v, r, desc, typ, ds, stat_metrics)
    PE += interaction_rows(P)
    pd.DataFrame(PE).to_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv", index=False)
    (PKG / "_qa_auto.md").write_text("| Check | Result | Detail |\n|---|---|---|\n" + "\n".join(f"| {n} | {'PASS' if ok else '**FAIL**'} | {d} |" for n, ok, d in checks), encoding="utf-8")
    prov = {"manifest": "docs/supp_v1/EXPERIMENT_MANIFEST.json", "manifest_sha256": M["manifest_sha256"], "code_fingerprint": M["code_fingerprint"],
            "git_commit_at_build": M["git_commit_at_build"], "phase6c_manifest_sha256": P6C["manifest_sha256"], "table4_v2_manifest_sha256": T4["manifest_sha256"],
            "datasets": M["datasets"], "n_new_runs": len(M["runs"]), "qa": [{"check": n, "pass": ok, "detail": d} for n, ok, d in checks],
            "runs": [{"run_id": r["run_id"], "dataset": r["dataset"], "arm": r["arm"], "seed": r["seed"], "family": r["family"], "config": r["config"],
                      "config_sha256": r["config_sha256"], "out_dir": r["out_dir"], "timed": r["timed"]} for r in M["runs"]],
            "reused_evidence": [{"dataset": ds, "arm": arm, "seed": s, "source": source_of(arm), "out_dir": rundir(ds, arm, s).relative_to(ROOT).as_posix(),
                                 "run_complete_sha256": sha256_file(rundir(ds, arm, s) / "COMPLETE.json")} for ds in DATASETS for s in S5 for arm in REUSED_P6C + ["t4_e2_robust_random_path"]],
            "hardware": "Intel Core i5-14400F (10 cores/16 threads), CPU-only, torch 2.15.0+cpu, Python 3.11.9, Windows 11",
            "limitations": ["aggregate-direction differences were not logged and are not reported", "Phase 6C detection metrics of reused arms come from the audited ledger; AP unaudited",
                            "worst-client recall is reported only for family E (client holdout); the Phase 6C client_level_recall.csv scores training data and is not used"]}
    (PKG / "SUPPLEMENTARY_EXPERIMENTS_PROVENANCE.json").write_text(json.dumps(prov, indent=1, default=str), encoding="utf-8")
    print(f"{len(P)} per-seed rows; {len(PE)} paired rows; {sum(ok for _, ok, _ in checks)}/{len(checks)} QA checks pass")
    for n, ok, d in checks:
        if not ok:
            print("FAIL:", n, d)


if __name__ == "__main__":
    main()
