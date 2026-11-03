"""Phase 8: READ-ONLY audit tables built from existing Phase 6C / Phase 7b outputs and the Phase 7b post-hoc files.

Nothing is retrained and no historical file is modified; every table is written to docs/phase8/tables/.
Run:  python scripts/phase8/phase8_tables.py
Units: MB = 1e6 bytes (decimal); communication figures are UPLINK model-update payload only (no downlink broadcast).
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "phase8" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
SEEDS_6C = range(12, 17)


def run_dirs(results: str, dataset: str, arm: str):
    """Completed seed directories only (ignores *.incomplete.* attempt folders)."""
    return sorted(p for p in (ROOT / results / dataset / arm).glob("seed_[0-9][0-9]") if (p / "COMPLETE.json").exists())


def arms(results: str, dataset: str):
    return sorted(p.name for p in (ROOT / results / dataset).iterdir() if p.is_dir() and not p.name.startswith("_"))


# ---------------------------------------------------------------- T1 original vs audited metrics (Phase 6C)
def table_original_vs_audited():
    df = pd.read_csv(ROOT / "posthoc_threshold_fix" / "phase6c_posthoc_with_deltas.csv")
    cols = ["best_rep_auc_old", "best_rep_auc_new", "best_rep_f1_old", "best_rep_f1_new", "last_rep_auc_old", "last_rep_auc_new", "last_rep_f1_old", "last_rep_f1_new"]
    g = df.groupby(["dataset", "arm"])
    t = g[cols].mean()
    t["n_runs"] = g.size()
    t["max_abs_best_dauc"] = g["best_dauc"].apply(lambda s: s.abs().max())
    t["n_last_round_changed"] = g["affected_last"].sum()
    t["n_best_changed"] = g["affected_best"].sum()
    t.round(5).to_csv(OUT / "T1_phase6c_original_vs_audited_by_arm.csv")
    return t


# ---------------------------------------------------------------- T2 Phase 7b arm summary + paired contrasts
P7B_ARMS = ["reference", "corrected", "p7_corrected_guard", "fail0p3_reference", "fail0p3_corrected", "fail0p3_p7_corrected_guard", "ctl_delivery_coupled", "p7_delivery_guard"]


def phase7b_runs():
    rows = []
    for arm in P7B_ARMS:
        for d in run_dirs("results_phase7b", "unsw", arm):
            fv = json.loads((d / "final_validation_metrics.json").read_text())
            rm = pd.read_csv(d / "round_metrics.csv")
            rm = rm[rm["round"] > 0]
            b, l = fv["report_partition_at_selected_threshold"], fv["last_round_report_partition"]
            rows.append(dict(arm=arm, seed=int(d.name.split("_")[1]), best_auc=b["roc_auc"], best_f1=b["f1"], best_recall=b["recall_adr"], best_fpr=b["fpr"],
                             last_auc=l["roc_auc"], last_f1=l["f1"], last_recall=l["recall_adr"], last_fpr=l["fpr"],
                             max_train_loss=float(rm["mean_train_loss"].max()), skipped_rounds=int(rm["aggregation_skipped"].fillna(0).sum())))
    df = pd.DataFrame(rows)
    df["collapse"] = ((df.last_auc < 0.90) | (df.max_train_loss > 100)).astype(int)   # pre-registered definition
    return df


def paired(df, a, b, col):
    A = df[df.arm == a].sort_values("seed")[col].to_numpy()
    B = df[df.arm == b].sort_values("seed")[col].to_numpy()
    d = A - B
    n = len(d)
    sd = d.std(ddof=1)
    ci = stats.t.interval(0.95, n - 1, loc=d.mean(), scale=sd / math.sqrt(n)) if sd > 0 else (np.nan, np.nan)
    flips = [abs((d * np.array(s)).mean()) for s in itertools.product([1, -1], repeat=n)]   # exact sign-flip test (min p = 2/2^n)
    return dict(contrast=f"{a} - {b}", metric=col, n=n, mean_diff=d.mean(), sd_diff=sd, cohen_dz=d.mean() / sd if sd > 0 else np.nan,
                n_better=int((d > 0).sum()), n_worse=int((d < 0).sum()), n_equal=int((d == 0).sum()), ci95_lo=ci[0], ci95_hi=ci[1],
                p_signflip_exact=float(np.mean([f >= abs(d.mean()) - 1e-15 for f in flips])), per_seed=json.dumps(np.round(d, 4).tolist()))


def table_phase7b():
    df = phase7b_runs()
    df.to_csv(OUT / "T2a_phase7b_per_run.csv", index=False)
    summ = df.groupby("arm").agg(["mean", "std"])[["best_auc", "best_f1", "best_recall", "best_fpr", "last_auc", "last_f1", "last_recall", "last_fpr"]].loc[P7B_ARMS]
    summ.columns = ["_".join(c) for c in summ.columns]
    summ["collapses"] = df.groupby("arm")["collapse"].sum()
    summ["skipped_rounds"] = df.groupby("arm")["skipped_rounds"].sum()
    summ.round(4).to_csv(OUT / "T2b_phase7b_arm_summary.csv")
    pairs = [("p7_corrected_guard", "corrected"), ("fail0p3_p7_corrected_guard", "fail0p3_corrected"), ("p7_delivery_guard", "ctl_delivery_coupled"),
             ("corrected", "reference"), ("fail0p3_corrected", "fail0p3_reference"), ("fail0p3_p7_corrected_guard", "fail0p3_reference")]
    rows = [paired(df, a, b, c) for a, b in pairs for c in ("best_auc", "last_auc", "best_f1", "last_f1", "best_recall", "best_fpr")]
    pd.DataFrame(rows).round(5).to_csv(OUT / "T2c_phase7b_paired_contrasts.csv", index=False)


# ---------------------------------------------------------------- T3 communication accounting and delivery vs PDR
def table_communication():
    rows = []
    for ds in ("unsw", "ciciot"):
        for arm in arms("results_phase6c", ds):
            att = dl = wire = sel = rec = 0
            pdr_w = []
            n = 0
            for d in run_dirs("results_phase6c", ds, arm):
                nm = pd.read_csv(d / "network_metrics.csv")
                if nm.empty:
                    continue
                n += 1
                nb = nm["update_bytes"]
                att += nb.sum()
                dl += nb[nm["update_delivered"] == True].sum()
                wire += nm["bytes_on_wire"].sum() if "bytes_on_wire" in nm else nb.sum()
                sel += len(nm)
                rec += int((nm["received_by_server"] == True).sum())
                pdr_w.append(nm["pdr"].mean())
            if n == 0:
                continue
            rows.append(dict(dataset=ds, arm=arm, n_runs=n, attempted_payload_MB_per_run=att / n / 1e6, delivered_payload_MB_per_run=dl / n / 1e6,
                             on_wire_MB_per_run=wire / n / 1e6, update_delivery_ratio=dl / max(att, 1), received_over_selected=rec / max(sel, 1),
                             mean_packet_pdr_first_tx=float(np.mean(pdr_w))))
    t = pd.DataFrame(rows)
    t["pdr_minus_update_received"] = t["mean_packet_pdr_first_tx"] - t["received_over_selected"]
    t.round(4).to_csv(OUT / "T3_communication_and_delivery_phase6c.csv", index=False)


# ---------------------------------------------------------------- T4 selection fairness / coverage / attacker exposure
def table_selection():
    rows = []
    for ds in ("unsw", "ciciot"):
        for arm in arms("results_phase6c", ds):
            g, ns, ms, mr, sel_tot = [], [], [], [], []
            wc, p10, rec_ns, rec_sel = [], [], [], []
            for d in run_dirs("results_phase6c", ds, arm):
                pc = json.loads((d / "phase6c_diagnostics.json").read_text())
                part, up = pc["participation"], pc["updates"]
                g.append(part["selection_gini"])
                ns.append(part["longest_exclusion_gap_rounds_selection"]["clients_never_selected"])
                rm = pd.read_csv(d / "round_metrics.csv")
                rm = rm[rm["round"] > 0]
                cl = pd.read_csv(d / "client_level_recall.csv")
                cl = cl[cl["attack_samples"] >= 50]          # recall is only meaningful with enough attack rows
                if len(cl):
                    wc.append(cl["recall"].min()); p10.append(cl["recall"].quantile(0.10))
                    if (cl["times_selected"] == 0).any():
                        rec_ns.append(cl.loc[cl["times_selected"] == 0, "recall"].mean())
                    rec_sel.append(cl.loc[cl["times_selected"] > 0, "recall"].mean())
                ms.append(rm["malicious_selected"].sum() / max(rm["selected_clients"].sum(), 1))
                mr.append(rm["malicious_received"].sum() / max(rm["received_updates"].sum(), 1))
            if g:
                rows.append(dict(dataset=ds, arm=arm, n_runs=len(g), selection_gini=np.mean(g), clients_never_selected=np.mean(ns),
                                 malicious_share_of_selected=np.mean(ms), malicious_share_of_received=np.mean(mr),
                                 worst_client_recall=np.mean(wc), p10_client_recall=np.mean(p10),
                                 mean_recall_never_selected_clients=np.mean(rec_ns) if rec_ns else np.nan, mean_recall_selected_clients=np.mean(rec_sel)))
    pd.DataFrame(rows).round(4).to_csv(OUT / "T4_selection_fairness_and_attacker_exposure_phase6c.csv", index=False)


# ---------------------------------------------------------------- T5 surrogate weights and MAD behaviour by number of genuine updates
def table_surrogate_and_mad():
    rows, mad = [], []
    for results, seeds_label in (("results_phase6c", "6C"), ("results_phase7b", "7b")):
        for ds in ("unsw", "ciciot"):
            if not (ROOT / results / ds).exists():
                continue
            for arm in arms(results, ds):
                s, mx, inf = [], [], []
                for d in run_dirs(results, ds, arm):
                    rm = pd.read_csv(d / "round_metrics.csv")
                    rm = rm[(rm["round"] > 0) & (rm["received_updates"] > 0)]
                    s.append(rm["surrogate_weight_share"].fillna(0).mean())
                    mx.append(rm["max_applied_weight_share"].max())
                    inf.append((rm["weight_cap_infeasible_strict"] == True).mean())
                    ad = pd.read_csv(d / "aggregation_diagnostics.csv")
                    if ad.empty or not ad["actual_aggregation_method"].astype(str).str.contains("distance_filter").any():
                        continue
                    real = ad[ad["is_recovered_update"] == False]
                    n_real = real.groupby("round").size().rename("n_real")
                    ad = ad.join(n_real, on="round")
                    for (rnd), grp in ad.groupby("round"):
                        r = grp[grp["is_recovered_update"] == False]
                        mad.append(dict(results=seeds_label, dataset=ds, arm=arm, n_real=len(r),
                                        honest=int((~r["is_malicious_client"].astype(bool)).sum()), honest_rejected=int(((~r["is_malicious_client"].astype(bool)) & (~r["kept"].astype(bool))).sum()),
                                        malicious=int(r["effective_malicious_update"].astype(bool).sum()), malicious_accepted=int((r["effective_malicious_update"].astype(bool) & r["kept"].astype(bool)).sum())))
                if s:
                    rows.append(dict(results=seeds_label, dataset=ds, arm=arm, n_runs=len(s), mean_surrogate_weight_share=np.mean(s),
                                     max_applied_weight_share=np.nanmax(mx), frac_rounds_strict_cap_infeasible=np.mean(inf)))
    pd.DataFrame(rows).round(4).to_csv(OUT / "T5a_surrogate_weight_share.csv", index=False)
    m = pd.DataFrame(mad)
    if not m.empty:
        m["n_real_bin"] = pd.cut(m["n_real"], [0, 2, 3, 5, 100], labels=["1-2", "3", "4-5", ">=6"])
        agg = m.groupby(["results", "n_real_bin"], observed=True)[["honest", "honest_rejected", "malicious", "malicious_accepted"]].sum()
        agg["honest_rejection_rate"] = agg["honest_rejected"] / agg["honest"].clip(lower=1)
        agg["malicious_acceptance_rate"] = agg["malicious_accepted"] / agg["malicious"].clip(lower=1)
        agg["rounds"] = m.groupby(["results", "n_real_bin"], observed=True).size()
        agg.round(4).to_csv(OUT / "T5b_mad_filter_by_number_of_real_updates.csv")


# ---------------------------------------------------------------- T6 baseline configuration comparison (UNSW configs; CIC differs only by dataset block)
def table_config_matrix():
    import yaml
    paths = {"method": ("experiment", "method_name"), "agg": ("aggregation", "method"), "surrogate_handling": ("aggregation", "surrogate_handling"),
             "routing": ("routing", "enabled"), "selection": ("routing", "selection_policy"), "delivery": ("routing", "delivery_model"),
             "recovery": ("failure", "recovery_enabled"), "fail_p": ("failure", "client_failure_probability"), "sur_cap": ("failure", "surrogate_total_weight_cap"),
             "attack": ("attack", "attack_type"), "mal_frac": ("attack", "malicious_fraction"), "assign": ("attack", "assignment"),
             "weighting": ("fl", "weighting"), "momentum": ("fl", "server_momentum"), "server_lr": ("fl", "server_learning_rate"),
             "dp": ("privacy", "mode"), "clip": ("privacy", "clip_norm"), "client_cap": ("privacy", "max_client_weight_share"), "eps_target": ("privacy", "target_epsilon")}
    rows = []
    for f in sorted((ROOT / "configs" / "phase6c").glob("unsw_*.yaml")):
        y = yaml.safe_load(f.read_text(encoding="utf-8"))
        rows.append({"arm": f.stem.replace("unsw_", ""), **{k: (y.get(a, {}) or {}).get(b, "default") for k, (a, b) in paths.items()}})
    pd.DataFrame(rows).to_csv(OUT / "T6_baseline_configuration_matrix_phase6c.csv", index=False)


if __name__ == "__main__":
    table_config_matrix()
    table_original_vs_audited()
    table_phase7b()
    table_communication()
    table_selection()
    table_surrogate_and_mad()
    print("tables written to", OUT)
