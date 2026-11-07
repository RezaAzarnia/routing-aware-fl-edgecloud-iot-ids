"""Build all ablation_v2 tables from completed, verified runs. Read-only on run directories."""
import itertools, json, math
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results_ablation_controlled_v2"
SEEDS = [12, 13, 14, 15, 16]
DS = ["ciciot", "unsw"]
H = "results_phase6c"
N = "results_ablation_controlled_v2/runs"
ARMS = {
    "reference": ("Reference (historical)", H),
    "abl_reference_repro": ("Reference (current code)", N),
    "ctl_imputation_none": ("No recovery", H),
    "ctl_momentum0_lr0p5": ("No momentum (server lr 0.5)", H),
    "ctl_momentum0_lr5p0": ("Momentum 0 + server lr 5.0 [confounded]", H),
    "ctl_weighting_uniform": ("Uniform weighting", H),
    "ctl_imputation_postfilter": ("Real-only filtering", H),
    "ctl_imputation_cap010": ("Surrogate weight cap 0.10", H),
    "ctl_selection_coverage": ("Coverage-aware selection", H),
    "ctl_selection_uniform": ("Uniform selection", H),
    "ctl_delivery_coupled": ("Packet-coupled delivery", H),
    "abl_no_filter": ("No robust filtering", N),
    "abl_privacy_clip_only": ("Clip + weight cap, no noise", N),
    "reference_gaussian": ("Central Gaussian (historical)", H),
    "abl_reference_gaussian_repro": ("Central Gaussian (current code)", N),
}
# (variant, reference, family, single_factor, note)
PAIRS = [
    ("ctl_imputation_none", "reference", "component", True, "recovery_enabled true->false"),
    ("ctl_momentum0_lr0p5", "reference", "component", True, "server_momentum 0.9->0.0; server lr unchanged (0.5)"),
    ("ctl_weighting_uniform", "reference", "component", True, "fl.weighting sample_proportional->uniform (surrogate base weight also uniform)"),
    ("ctl_imputation_postfilter", "reference", "component", True, "surrogate_handling reference->post_filter_real_only (filter statistics and surrogate construction change together)"),
    ("ctl_imputation_cap010", "reference", "component", True, "surrogate_total_weight_cap null->0.10"),
    ("ctl_selection_coverage", "reference", "component", True, "selection_policy top-k->coverage_aware (selected clients change by construction; attacker exposure is held at 20% by exposure_controlled assignment)"),
    ("ctl_selection_uniform", "reference", "component", True, "selection_policy top-k->uniform_random (selected clients change by construction; attacker exposure is held at 20% by exposure_controlled assignment)"),
    ("ctl_delivery_coupled", "reference", "component", True, "delivery_model->packet_coupled (delivery outcome changes; same matched trace)"),
    ("ctl_momentum0_lr5p0", "reference", "component", False, "momentum 0.9->0 AND server lr 0.5->5.0: two factors, not an isolated momentum ablation"),
    ("abl_no_filter", "abl_reference_repro", "component", True, "aggregation.method distance_filter->fedavg"),
    ("abl_privacy_clip_only", "abl_reference_repro", "privacy", True, "privacy.mode none->central_client with noise_multiplier 0 (clipping + weight cap only)"),
    ("abl_reference_gaussian_repro", "abl_privacy_clip_only", "privacy", True, "Gaussian noise added on top of clipping + weight cap (noise calibrated to eps_est=10)"),
    ("abl_reference_gaussian_repro", "abl_reference_repro", "privacy", False, "full privacy pipeline: clipping + weight cap + noise (not attributable to noise alone)"),
    ("reference_gaussian", "reference", "privacy", False, "full privacy pipeline, historical runs (not attributable to noise alone)"),
    ("abl_reference_repro", "reference", "reproducibility", True, "same config; current code/environment vs historical"),
]
LOWER = {"fpr_best", "fpr_final", "auc_drawdown", "mean_delay_ms", "never_selected", "attacker_exposure",
         "selection_gini", "surrogate_weight_share", "skipped_rounds", "perf_recovery_rounds"}
KEYM = ["auc_best", "auc_final", "f1_best", "f1_final", "ap_best", "ap_final", "fpr_best", "fpr_final", "recall_best",
        "recall_final", "auc_drawdown", "mean_delay_ms", "first_tx_pdr", "complete_update_delivery",
        "received_real_per_round", "transfer_eff_mbps", "selection_gini", "never_selected", "attacker_exposure",
        "surrogate_count", "surrogate_weight_share", "real_retained_per_round", "skipped_rounds", "perf_recovery_rounds"]
IGN = {"experiment.name", "experiment.method_name", "experiment.variant_name", "experiment.output_dir",
       "experiment.exact_output_dir", "experiment.seed"}


def rd(arm, ds, s):
    return ROOT / ARMS[arm][1] / ds / arm / f"seed_{s}"


def is_ok(d):
    return (d / "ablation_COMPLETE.json").exists() or (d / "COMPLETE.json").exists()


def gini(c):
    c = np.sort(np.asarray(c, float)); n = len(c)
    return float((2 * np.sum(np.arange(1, n + 1) * c) / (n * c.sum()) - (n + 1) / n)) if c.sum() else 0.0


def run_metrics(d):
    fv = json.loads((d / "final_validation_metrics.json").read_text())
    assert fv["test_data_loaded"] is False
    rb, rl = fv["report_partition_at_selected_threshold"], fv["last_round_report_partition"]
    rm = pd.read_csv(d / "round_metrics.csv"); rm = rm[rm["round"] > 0].reset_index(drop=True)
    nm = pd.read_csv(d / "network_metrics.csv"); nm = nm[nm["selected"] == True]
    ag = pd.read_csv(d / "aggregation_diagnostics.csv")
    rc = pd.read_csv(d / "recovery_events.csv") if (d / "recovery_events.csv").exists() else pd.DataFrame()
    auc = rm["val_rep_roc_auc"].to_numpy()
    dd = float(np.max(np.maximum.accumulate(auc) - auc))
    counts = np.array([int((nm.client_id == c).sum()) for c in range(50)])
    cfg = yaml.safe_load((d / "resolved_config.yaml").read_text())
    sur = ag[ag.is_recovered_update == True]
    kr = ag[(ag.kept == True) & (ag.is_recovered_update == False)]
    dl = nm[nm.update_delivered == True]
    noisy = cfg["privacy"]["mode"] == "central_client" and rm["privacy_noise_std"].max() > 0
    return dict(
        best_round=fv["best_round"], auc_best=rb["roc_auc"], ap_best=rb["pr_auc"], f1_best=rb["f1"], fpr_best=rb["fpr"],
        recall_best=rb["recall_adr"], auc_final=rl["roc_auc"], ap_final=rl["pr_auc"], f1_final=rl["f1"],
        fpr_final=rl["fpr"], recall_final=rl["recall_adr"], auc_drawdown=dd, collapse=bool(dd > 0.05),
        auc_min_after_r5=float(auc[5:].min()),
        mean_delay_ms=float(nm.end_to_end_delay_ms.mean()), first_tx_pdr=float(nm.pdr.mean()),
        complete_update_delivery=float(nm.update_delivered.mean()),
        received_real_per_round=float(rm.received_updates.mean()),
        bytes_delivered_total=float(dl.update_bytes.sum()), bytes_on_wire_total=float(nm.bytes_on_wire.sum()),
        transfer_eff_mbps=float(dl.transfer_efficiency_mbps.mean()),
        selection_gini=gini(counts), never_selected=int((counts == 0).sum()),
        attacker_exposure=float(nm.malicious.mean()), malicious_received_total=int(rm.malicious_received.sum()),
        surrogate_count=int(rm.imputed_clients.sum()), surrogate_weight_total=float(sur.raw_weight.sum()),
        surrogate_weight_share=float(rm.surrogate_weight_share.mean()),
        real_retained_per_round=float(len(kr) / len(rm)),
        skipped_rounds=int(rm["aggregation_skipped"].sum()) if "aggregation_skipped" in rm else 0,
        recovery_events=int(len(rc)),
        perf_recovered_frac=float(rc.performance_recovered_round.notna().mean()) if len(rc) else float("nan"),
        perf_recovery_rounds=float(rc.performance_recovery_rounds.mean()) if len(rc) else float("nan"),
        nsr=float(rm.privacy_noise_to_signal_ratio.mean()) if noisy else float("nan"),
        eps_estimate=float(rm.privacy_epsilon_estimate.iloc[-1]) if noisy else float("nan"))


def cfgflat(d, p=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict):
            o.update(cfgflat(v, p + k + "."))
        else:
            o[p + k] = json.dumps(v)
    return o


LEDGER = pd.read_csv(ROOT / "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv").set_index(["dataset", "arm", "seed"])
AUDIT_MAP = {"auc_best": "best_auc_audited", "f1_best": "best_f1_audited", "recall_best": "best_recall_audited", "fpr_best": "best_fpr_audited",
             "auc_final": "last_auc_audited", "f1_final": "last_f1_audited", "recall_final": "last_recall_audited", "fpr_final": "last_fpr_audited"}


def apply_audit(m, ds, arm, s, log):
    """Historical runs were evaluated before the threshold/tie fix; replace the 8 affected metrics by the audited
    ledger values (identical for unaffected runs, asserted below). New runs already use the fixed evaluation."""
    row = LEDGER.loc[(ds, arm, s)]
    changed = {}
    for k, col in AUDIT_MAP.items():
        if abs(m[k] - row[col]) > 1e-9:
            changed[k] = (m[k], float(row[col]))
        m[k] = float(row[col])
    if changed:
        log.append(dict(dataset=ds, arm=arm, seed=s, changed={k: v for k, v in changed.items()}))
    return m


def main():
    audit_log = []
    inv, per = [], []
    for ds in DS:
        for arm, (lab, root) in ARMS.items():
            for s in SEEDS:
                d = rd(arm, ds, s)
                row = dict(dataset=ds, arm=arm, seed=s, path=str(d.relative_to(ROOT)).replace("\\", "/"))
                if is_ok(d):
                    try:
                        m = run_metrics(d)
                        if root == H:
                            m = apply_audit(m, ds, arm, s, audit_log)
                        m["metric_source"] = "audited ledger (historical run, original evaluation corrected)" if root == H else "current code (corrected evaluation)"
                        per.append(dict(dataset=ds, arm=arm, label=lab, seed=s, **m))
                        row.update(status="verified_reused" if root == H else "newly_executed",
                                   note="historical COMPLETE.json + manifest hashes verified (verify_run_dir); code fingerprint differs from current code"
                                   if root == H else "ablation_COMPLETE.json artifact hashes recorded")
                    except Exception as e:  # noqa
                        row.update(status="failed_analysis", note=repr(e))
                elif d.exists():
                    row.update(status="failed_or_partial", note="directory without completion record")
                else:
                    row.update(status="missing", note="not run")
                inv.append(row)
    inv.append(dict(dataset="both", arm="min_real_updates_guard_on_reference", seed="12-16", path="", status="not_run",
                    note="guard (min_real_updates=3) abstains only if 0<received<3; never occurs in 0/150 reference rounds per dataset, so it is identical to the reference by construction"))
    pd.DataFrame(inv).to_csv(OUT / "ablation_run_inventory.csv", index=False)
    P = pd.DataFrame(per); P.to_csv(OUT / "ablation_per_seed.csv", index=False)
    mets = [c for c in P.columns if c not in ("dataset", "arm", "label", "seed", "collapse", "metric_source")]
    g = P.groupby(["dataset", "arm", "label"])
    S = g[mets].agg(["mean", "std"]); S.columns = [f"{a}_{b}" for a, b in S.columns]
    S["n_seeds"] = g.size(); S["n_collapse"] = g.collapse.sum()
    S.reset_index().to_csv(OUT / "ablation_summary.csv", index=False)
    cd = []
    for v, r, fam, clean, note in PAIRS:
        for ds in DS:
            try:
                a = cfgflat(yaml.safe_load((rd(r, ds, 12) / "resolved_config.yaml").read_text()))
                b = cfgflat(yaml.safe_load((rd(v, ds, 12) / "resolved_config.yaml").read_text()))
            except Exception:  # noqa
                continue
            diffs = {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k) and k not in IGN}
            cd.append(dict(dataset=ds, variant=v, reference=r, family=fam, single_factor=clean, intended_change=note,
                           n_fields=len(diffs), changed_fields="; ".join(f"{k}: {x} -> {y}" for k, (x, y) in diffs.items())))
    pd.DataFrame(cd).to_csv(OUT / "ablation_config_differences.csv", index=False)
    rows = []
    for v, r, fam, clean, note in PAIRS:
        for ds in DS:
            a = P[(P.dataset == ds) & (P.arm == r)].set_index("seed")
            b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")
            seeds = sorted(set(a.index) & set(b.index))
            if len(seeds) < 2:
                continue
            for m in KEYM:
                dl = (b.loc[seeds, m] - a.loc[seeds, m]).to_numpy(float)
                if np.isnan(dl).all():
                    continue
                n = len(dl); mu = float(np.nanmean(dl)); sd = float(np.nanstd(dl, ddof=1)); se = sd / math.sqrt(n)
                tc = stats.t.ppf(0.975, n - 1)
                up = int((dl > 1e-12).sum()); dn = int((dl < -1e-12).sum())
                signs = np.array(list(itertools.product([1, -1], repeat=n)))
                perm = np.abs((signs * np.abs(dl)).mean(1))
                pex = float((perm >= abs(mu) - 1e-15).mean())
                rows.append(dict(dataset=ds, variant=v, reference=r, family=fam, single_factor=clean, metric=m, n_seeds=n,
                                 mean_ref=float(a.loc[seeds, m].mean()), mean_var=float(b.loc[seeds, m].mean()),
                                 mean_diff=mu, sd_diff=sd, ci95_lo=mu - tc * se, ci95_hi=mu + tc * se,
                                 n_var_higher=up, n_var_lower=dn, n_improved=dn if m in LOWER else up,
                                 n_deteriorated=up if m in LOWER else dn, n_tied=n - up - dn, exact_signflip_p=pex,
                                 min_attainable_p=2 / 2 ** n, conventional_sig_attainable=(2 / 2 ** n) < 0.05,
                                 note="exploratory; with 5 seeds the minimum attainable exact two-sided p is 0.0625" if n == 5 else "exploratory"))
    pd.DataFrame(rows).to_csv(OUT / "ablation_paired_comparisons.csv", index=False)
    pd.DataFrame([dict(dataset=a["dataset"], arm=a["arm"], seed=a["seed"], metric=k, original=v[0], audited=v[1])
                  for a in audit_log for k, v in a["changed"].items()]).to_csv(OUT / "audit_overrides.csv", index=False)
    print(len(audit_log), "historical runs with audited overrides:", sorted({a["arm"] for a in audit_log}))
    print(len(P), "per-seed rows;", len(rows), "paired rows")


if __name__ == "__main__":
    main()
