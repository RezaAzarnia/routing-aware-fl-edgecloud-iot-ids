"""Table 4 v2: per-seed extraction, independent recomputation checks, summaries, paired effects, replacement table, provenance.
Reads only run directories (validation-only artifacts) and the audited ledger; never touches the reserved test data.
usage: python scripts/table4_v2/analyse.py   -> Table4_V2_Package/ (refuses to overwrite non-empty output)"""
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
from t4_common import (MANIFEST, NEW_ARMS, OUT_ROOT, ROOT, SEEDS, DATASETS, load_manifest, sha256_file, sha256_text_file, verify_run_dir)  # noqa: E402

PKG = ROOT / "Table4_V2_Package"
LEDGER = pd.read_csv(ROOT / "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv").set_index(["dataset", "arm", "seed"])
P6C = json.loads((ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
T4M = load_manifest(MANIFEST)
COMPARATORS = ["scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation", "reference", "reference_gaussian"]
ARM_LABEL = {
    "scenario_fedavg_topk": "FedAvg, top-k selection, routed paths",
    "scenario_fedavg_random": "FedAvg, uniform selection, routed paths",
    "t4_e1_fedavg_random_path": "FedAvg, uniform selection, random paths (E1)",
    "robust_random_no_imputation": "MAD filter, uniform selection, routed paths",
    "t4_e2_robust_random_path": "MAD filter, uniform selection, random paths (E2)",
    "t4_e3_dpfedavg_random_path": "DP+FedAvg, uniform selection, random paths (E3)",
    "reference": "Reference pipeline, no noise",
    "reference_gaussian": "Proposed, $\\varepsilon\\approx10$",
    "t4_e4_proposed_eps20": "Proposed, $\\varepsilon\\approx20$ (E4)",
}
ALL_ARMS = list(ARM_LABEL)
NEW = set(NEW_ARMS)


def rundir(ds, arm, seed):
    return ROOT / (OUT_ROOT if arm in NEW else "results_phase6c") / ds / arm / f"seed_{seed}"


def gini(c):
    c = np.sort(np.asarray(c, float)); n = len(c)
    return float((2 * np.sum(np.arange(1, n + 1) * c) / (n * c.sum()) - (n + 1) / n)) if c.sum() else 0.0


def extract(ds, arm, seed):
    d = rundir(ds, arm, seed)
    fv = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
    meta = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))
    rm = pd.read_csv(d / "round_metrics.csv"); rmr = rm[rm["round"] > 0]
    nm = pd.read_csv(d / "network_metrics.csv"); nm = nm[nm.selected == True]
    ag = pd.read_csv(d / "aggregation_diagnostics.csv")
    rec = json.loads((d / "COMPLETE.json").read_text(encoding="utf-8"))
    sel, last = fv["report_partition_at_selected_threshold"], fv["last_round_report_partition"]
    row = dict(dataset=ds, arm=arm, seed=seed, run_id=rec["run_id"], source="new (current code)" if arm in NEW else "locked Phase 6C (reused)",
               out_dir=d.relative_to(ROOT).as_posix(), config_sha256=rec["config_sha256"], code_fingerprint=rec["code_fingerprint"],
               manifest_sha256=rec["manifest_sha256"], test_data_loaded=meta.get("test_data_loaded"), best_round=fv["best_round"])
    # detection: new runs use the corrected evaluation directly; reused historical runs use the audited ledger for F1/AUC/FPR
    for tag, blk, lc in (("sel", sel, "best"), ("last", last, "last")):
        for m, key, lcol in (("f1", "f1", "f1_audited"), ("auc", "roc_auc", "auc_audited"), ("fpr", "fpr", "fpr_audited"), ("recall", "recall_adr", "recall_audited")):
            row[f"{m}_{tag}"] = float(blk[key]) if arm in NEW else float(LEDGER.loc[(ds, arm, seed)][f"{lc}_{lcol}"])
        row[f"ap_{tag}"] = float(blk["pr_auc"])
        for c in ("tn", "fp", "fn", "tp"):
            row[f"{c}_{tag}"] = int(blk[c])
    row["ap_source"] = "run output (corrected evaluation)" if arm in NEW else "run output (original evaluation; AP not audited)"
    dl = nm[nm.update_delivered == True]
    row.update(delay_ms_delivered=float(dl.end_to_end_delay_ms.mean()), delay_ms_all_selected=float(nm.end_to_end_delay_ms.mean()),
               pdr_first_transmission=float(nm.pdr.mean()), update_delivery_rate=float(nm.update_delivered.mean()),
               received_genuine_per_round=float(rmr.received_updates.mean()),
               retained_genuine_per_round=float(len(ag[(ag.kept == True) & (ag.is_recovered_update == False)]) / len(rmr)),
               surrogate_updates_total=int(rmr.imputed_clients.sum()),
               path_stability=float(nm.path_stability.mean()), te_mbps_delivered=float(dl.transfer_efficiency_mbps.mean()),
               te_mbps_all_selected=float(nm.transfer_efficiency_mbps.mean()),
               bytes_attempted=float(nm.update_bytes.sum()), bytes_delivered=float(dl.update_bytes.sum()), bytes_on_wire=float(nm.bytes_on_wire.sum()),
               bytes_attempted_roundlog=float(rmr.communication_bytes.sum()),
               selection_gini=gini([int((nm.client_id == c).sum()) for c in range(50)]),
               attacker_exposure=float(nm.malicious.mean()), explicit_failure_rate=float(nm.explicit_client_failure.mean()))
    priv = json.loads((d / "privacy_plan.json").read_text(encoding="utf-8"))
    dp = priv.get("privacy_enabled", False)
    row.update(dp_enabled=dp, dp_effective_noise_multiplier=priv.get("effective_noise_multiplier") if dp else np.nan,
               dp_target_epsilon=priv.get("target_epsilon") if dp else np.nan,
               dp_epsilon_planned_estimate=priv.get("planned_epsilon_estimate") if dp else np.nan,
               dp_epsilon_final_estimate=float(rmr.privacy_epsilon_estimate.iloc[-1]) if dp else np.nan,
               dp_nsr_mean=float(rmr.privacy_noise_to_signal_ratio.mean()) if dp else np.nan,
               dp_clipped_fraction_mean=float(rmr.privacy_clipped_fraction.mean()) if dp else np.nan,
               dp_amplification_valid=priv.get("subsampling_amplification_valid") if dp else np.nan,
               dp_certified=priv.get("epsilon_is_certified_guarantee") if dp else np.nan)
    return row


METRICS_DET = ["f1", "auc", "fpr", "ap", "recall"]
MET_ALL = [f"{m}_{t}" for m in METRICS_DET for t in ("sel", "last")] + ["delay_ms_delivered", "delay_ms_all_selected", "pdr_first_transmission", "update_delivery_rate",
                                                                      "received_genuine_per_round", "retained_genuine_per_round", "path_stability", "te_mbps_delivered",
                                                                      "te_mbps_all_selected", "bytes_attempted", "bytes_delivered", "bytes_on_wire", "selection_gini", "attacker_exposure"]
LOWER = {"fpr_sel", "fpr_last", "delay_ms_delivered", "delay_ms_all_selected", "selection_gini"}
# (variant, reference, factor description, comparison type)
PAIRS = [
    ("t4_e1_fedavg_random_path", "scenario_fedavg_random", "path assignment (routed -> random), FedAvg baseline", "single-factor: path assignment"),
    ("t4_e2_robust_random_path", "robust_random_no_imputation", "path assignment (routed -> random), MAD-filter baseline", "single-factor: path assignment"),
    ("scenario_fedavg_topk", "scenario_fedavg_random", "client selection (uniform-random -> top-k), routed paths, FedAvg", "single-factor: client selection"),
    ("t4_e2_robust_random_path", "t4_e1_fedavg_random_path", "aggregation (FedAvg -> MAD filter), random paths", "single-factor: aggregation"),
    ("robust_random_no_imputation", "scenario_fedavg_random", "aggregation (FedAvg -> MAD filter), routed paths", "single-factor: aggregation"),
    ("t4_e3_dpfedavg_random_path", "t4_e1_fedavg_random_path", "central DP pipeline on FedAvg (clip + weight cap + Gaussian noise, eps~10)", "bundle: privacy pipeline"),
    ("reference_gaussian", "reference", "central DP pipeline on the reference (clip + weight cap + Gaussian noise, eps~10)", "bundle: privacy pipeline"),
    ("t4_e4_proposed_eps20", "reference_gaussian", "privacy target eps~10 -> eps~20 (noise calibration only)", "single-factor: privacy target"),
    ("reference_gaussian", "t4_e3_dpfedavg_random_path", "proposed eps~10 vs DP+FedAvg (selection, path, aggregation, recovery all differ)", "multi-factor bundle (descriptive)"),
    ("t4_e4_proposed_eps20", "t4_e3_dpfedavg_random_path", "proposed eps~20 vs DP+FedAvg (selection, path, aggregation, recovery, eps target differ)", "multi-factor bundle (descriptive)"),
]


def paired_rows(P):
    rows = []
    for ds in DATASETS:
        for v, r, desc, typ in PAIRS:
            a = P[(P.dataset == ds) & (P.arm == r)].set_index("seed")
            b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")
            seeds = sorted(set(a.index) & set(b.index))
            if len(seeds) < 5:
                continue
            for m in MET_ALL:
                d = (b.loc[seeds, m] - a.loc[seeds, m]).to_numpy(float)
                n = len(d); mu = float(d.mean()); sd = float(d.std(ddof=1)); se = sd / math.sqrt(n)
                tc = stats.t.ppf(0.975, n - 1)
                up, dn = int((d > 1e-12).sum()), int((d < -1e-12).sum())
                signs = np.array(list(itertools.product([1, -1], repeat=n)))
                perm = np.abs((signs * np.abs(d)).mean(1))
                pex = float((perm >= abs(mu) - 1e-15).mean())
                rows.append(dict(dataset=ds, variant=v, reference=r, factor=desc, comparison_type=typ, metric=m, n_pairs=n, mean_reference=float(a.loc[seeds, m].mean()),
                                 mean_variant=float(b.loc[seeds, m].mean()), mean_diff=mu, sd_diff=sd, ci95_lo=mu - tc * se, ci95_hi=mu + tc * se,
                                 n_variant_higher=up, n_variant_lower=dn, n_tied=n - up - dn,
                                 n_improved=dn if m in LOWER else up, n_deteriorated=up if m in LOWER else dn,
                                 exact_signflip_p=pex, min_attainable_exact_p=2 / 2 ** n,
                                 per_seed_diffs="; ".join(f"{s}:{x:.6g}" for s, x in zip(seeds, d)),
                                 note="exploratory; 5 pairs: the smallest attainable two-sided exact p is 0.0625, so no difference can reach p<0.05; a small difference is not evidence of equivalence"))
    return pd.DataFrame(rows)


def qa_checks(P):
    out = []

    def add(name, ok, detail=""):
        out.append((name, bool(ok), detail))
    runs = {r["run_id"]: r for r in T4M["runs"]}
    bad = []
    for rid, r in runs.items():
        problems = verify_run_dir(ROOT / r["out_dir"], r, T4M)
        if problems:
            bad.append((rid, problems[:2]))
    add("all 40 new runs verify against the locked manifest (artifact hashes, config hash, code fingerprint, 30 rounds, test_data_loaded=false, accounting invariants)", not bad, f"{len(runs) - len(bad)}/40 verified {bad[:2]}")
    new = P[P.arm.isin(NEW)]
    add("test_data_loaded is false for all 40 new runs", (new.test_data_loaded == False).all())  # noqa: E712
    ph = pd.read_csv(ROOT / "results_ablation_controlled_v2/historical_verification.csv")
    ph = ph[ph.arm.isin(COMPARATORS)]
    add(f"reused comparator runs ({len(ph)}) pass the Phase 6C manifest verification", (ph.verify_problems == "none").all(), f"{len(ph)} runs")
    add("every (dataset, arm) has exactly seeds 12-16", P.groupby(["dataset", "arm"]).seed.apply(lambda x: sorted(x) == SEEDS).all())
    # independent recomputation from logged counts
    err = 0.0
    for _, r in P.iterrows():
        for t in ("sel", "last"):
            tp, fp, fn, tn = r[f"tp_{t}"], r[f"fp_{t}"], r[f"fn_{t}"], r[f"tn_{t}"]
            f1 = 2 * tp / max(2 * tp + fp + fn, 1); fpr = fp / max(fp + tn, 1)
            if r.arm in NEW:
                err = max(err, abs(f1 - r[f"f1_{t}"]), abs(fpr - r[f"fpr_{t}"]))
    add("F1 and FPR of the 40 new runs recomputed from logged confusion counts (tp, fp, fn, tn)", err < 1e-9, f"max abs error {err:.2e}")
    # checkpoint-selection provenance: best_round = argmax of the selection-partition AUC; stored selection predictions reproduce it
    worst_sel, worst_auc = 0, 0.0
    for _, r in P.iterrows():
        d = rundir(r.dataset, r.arm, r.seed)
        rm = pd.read_csv(d / "round_metrics.csv"); x = rm[rm["round"] > 0]
        worst_sel += int(x.loc[x.val_roc_auc.idxmax(), "round"] != r.best_round and abs(x.val_roc_auc.max() - x[x["round"] == r.best_round].val_roc_auc.iloc[0]) > 1e-9)
        if r.arm in NEW:
            vp = pd.read_csv(d / "validation_predictions.csv")
            worst_auc = max(worst_auc, abs(roc_auc_score(vp.y_true, vp.probability_attack) - float(rm[rm["round"] == r.best_round].val_roc_auc.iloc[0])))
    add("selected checkpoint = round with maximal selection-partition ROC-AUC (all 90... runs)", worst_sel == 0, f"{worst_sel} mismatches")
    add("selection-partition ROC-AUC recomputed from stored predictions equals the logged value (new runs)", worst_auc < 1e-5, f"max abs error {worst_auc:.2e}")
    acc = (P.bytes_attempted - P.bytes_attempted_roundlog).abs().max()
    add("attempted bytes from network log equals the round log", acc < 1, f"max diff {acc:.1f} B")
    dp = P[P.dp_enabled == True]  # noqa: E712
    add("DP runs: subsampling_amplification_valid=false and epsilon_is_certified_guarantee=false (no certified DP claim)", (dp.dp_amplification_valid == False).all() and (dp.dp_certified == False).all(), f"{len(dp)} DP runs")  # noqa: E712
    for tgt, arm in ((10.0, "t4_e3_dpfedavg_random_path"), (20.0, "t4_e4_proposed_eps20")):
        x = P[P.arm == arm]
        add(f"{arm}: calibrated noise multiplier and planned epsilon match the target {tgt}", (abs(x.dp_epsilon_planned_estimate - tgt) < 0.01).all(), f"sigma {x.dp_effective_noise_multiplier.iloc[0]:.4f}")
    # matched conditions (causal comparability)
    def net(ds, arm, s):
        return pd.read_csv(rundir(ds, arm, s) / "network_metrics.csv")
    def eq_runs(arm_a, arm_b, cols, files=()):
        ok = True
        for ds in DATASETS:
            for s in SEEDS:
                a, b = net(ds, arm_a, s), net(ds, arm_b, s)
                for c in cols:
                    ok &= a[c].equals(b[c]) if a[c].dtype != float else np.allclose(a[c], b[c], equal_nan=True, rtol=0, atol=0)
                for f in files:
                    ok &= sha256_file(rundir(ds, arm_a, s) / f) == sha256_file(rundir(ds, arm_b, s) / f)
        return ok
    cond = ["round", "client_id", "malicious", "explicit_client_failure", "explicit_failure_draw"]
    files = ("client_distribution.csv", "attacker_assignment.csv")
    add("E1 vs routed-path FedAvg random-selection arm: identical selected clients, attackers, failure draws, client data distribution and attacker assignment (all 10 dataset-seed pairs)",
        eq_runs("t4_e1_fedavg_random_path", "scenario_fedavg_random", cond, files))
    add("E2 vs routed-path MAD-filter random-selection arm: same identity checks", eq_runs("t4_e2_robust_random_path", "robust_random_no_imputation", cond, files))
    add("E1, E2, E3 share identical network traces (random-path stream is policy-independent)", eq_runs("t4_e1_fedavg_random_path", "t4_e2_robust_random_path", cond + ["edge_id", "end_to_end_delay_ms", "pdr", "update_delivered"]) and
        eq_runs("t4_e1_fedavg_random_path", "t4_e3_dpfedavg_random_path", cond + ["edge_id", "end_to_end_delay_ms", "pdr", "update_delivered"]))
    add("E4 vs existing Gaussian reference: identical network traces, selected clients and attackers (privacy target is the only change)",
        eq_runs("t4_e4_proposed_eps20", "reference_gaussian", cond + ["edge_id", "end_to_end_delay_ms", "pdr", "update_delivered"], files))
    # path assignment really differs between E1 and routed arm, nothing else about the network state
    diff_edges = any(not net(ds, "t4_e1_fedavg_random_path", s).edge_id.equals(net(ds, "scenario_fedavg_random", s).edge_id) for ds in DATASETS for s in SEEDS)
    add("E1 path assignment differs from the routed arm (the intended single factor)", diff_edges)
    split_ok = all(sha256_text_file(rundir(ds, a, s) / "validation_split_info.json") == sha256_text_file(rundir(ds, "scenario_fedavg_random", s) / "validation_split_info.json")
                   for ds in DATASETS for s in SEEDS for a in NEW)
    add("data split hash (validation_split_info.json) identical to the locked Phase 6C run of the same dataset and seed (all new runs)", split_ok)
    return out


def fmt(x, n=4):
    return f"{x:.{n}f}"


def build_table(S, PE):
    def cell(ds, arm, col, n=4, sd=True):
        r = S[(S.dataset == ds) & (S.arm == arm)].iloc[0]
        return f"{r[col + '_mean']:.{n}f}" + (f" ({r[col + '_sd']:.{n}f})" if sd else "")
    order = [("Baselines: no recovery, no DP", ["scenario_fedavg_topk", "scenario_fedavg_random", "t4_e1_fedavg_random_path", "robust_random_no_imputation", "t4_e2_robust_random_path"]),
             ("Baseline with central DP", ["t4_e3_dpfedavg_random_path"]),
             ("Reference pipeline (top-k selection, routed paths, median surrogates, MAD filter)", ["reference", "reference_gaussian", "t4_e4_proposed_eps20"])]
    cols = [("f1_sel", "F1", 4), ("auc_sel", "AUC", 4), ("auc_last", "AUC$_\\mathrm{last}$", 4), ("fpr_sel", "FPR", 4), ("delay_ms_delivered", "Delay", 1),
            ("pdr_first_transmission", "PDR", 3), ("update_delivery_rate", "Deliv.", 3), ("path_stability", "Path st.", 3), ("te_mbps_delivered", "TE", 1)]
    L = [r"\begin{table*}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{2.4pt}",
         r"\caption{Controlled comparison of the evaluated configurations on the report partition of the locked validation split (five paired seeds, 12--16; mean (SD)). Detection metrics are at the selected checkpoint; AUC$_\mathrm{last}$ is the final-round ROC-AUC. Delay (ms) and TE (transfer efficiency, Mbit/s of delivered payload per delivered update) are means over delivered updates; PDR is the packet delivery ratio on the first transmission, and Deliv. is the fraction of selected updates actually delivered (a separate event from PDR). Path st. is the mean path stability. Attackers (20\% sign-flip, exposure-controlled), failures ($p=0.1$), data partitions and network traces are matched across all rows. Random-path rows replace routed path assignment by random edges with the client-selection sequence unchanged. Epsilon values are diagnostic RDP estimates, not certified guarantees. No test data were used.}",
         r"\label{tab:main-controlled}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{@{}l" + "c" * len(cols) + r"@{}}", r"\toprule",
         "Configuration & " + " & ".join(c[1] for c in cols) + r" \\"]
    for ds, name in (("ciciot", "CICIoT2023"), ("unsw", "UNSW-NB15")):
        L.append(r"\midrule")
        L.append(r"\multicolumn{" + str(len(cols) + 1) + r"}{@{}l}{\textit{" + name + r"}} \\")
        for grp, arms in order:
            L.append(r"\multicolumn{" + str(len(cols) + 1) + r"}{@{}l}{\scriptsize\textit{" + grp + r"}} \\")
            for a in arms:
                L.append(ARM_LABEL[a] + " & " + " & ".join(cell(ds, a, c, n) for c, _, n in cols) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}}", r"\end{table*}", ""]
    # paired-effects table
    keep = [("t4_e1_fedavg_random_path", "scenario_fedavg_random", "Path assignment, FedAvg (routed $\\rightarrow$ random)"),
            ("t4_e2_robust_random_path", "robust_random_no_imputation", "Path assignment, MAD filter (routed $\\rightarrow$ random)"),
            ("scenario_fedavg_topk", "scenario_fedavg_random", "Client selection, FedAvg (uniform $\\rightarrow$ top-k)"),
            ("t4_e2_robust_random_path", "t4_e1_fedavg_random_path", "Aggregation (FedAvg $\\rightarrow$ MAD filter), random paths"),
            ("t4_e3_dpfedavg_random_path", "t4_e1_fedavg_random_path", "DP pipeline on FedAvg (bundle: clip + cap + noise)"),
            ("reference_gaussian", "reference", "DP pipeline on the reference (bundle)"),
            ("t4_e4_proposed_eps20", "reference_gaussian", "Privacy target $\\varepsilon\\approx10\\rightarrow20$ (noise only)"),
            ("reference_gaussian", "t4_e3_dpfedavg_random_path", "Proposed $\\varepsilon\\approx10$ vs DP+FedAvg (multi-factor)")]
    pm = [("auc_sel", "$\\Delta$AUC", 4), ("auc_last", "$\\Delta$AUC$_\\mathrm{last}$", 4), ("delay_ms_delivered", "$\\Delta$Delay (ms)", 1), ("pdr_first_transmission", "$\\Delta$PDR", 3),
          ("update_delivery_rate", "$\\Delta$Deliv.", 3), ("path_stability", "$\\Delta$Path st.", 3), ("te_mbps_delivered", "$\\Delta$TE", 2)]
    L += [r"\begin{table*}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{2.4pt}",
          r"\caption{Five-seed paired effects (variant $-$ reference): mean and SD of the per-seed differences, with the number of seeds in which the variant is lower. With five pairs the smallest attainable two-sided exact sign-flip $p$ is 0.0625, so no difference is declared significant and small differences are not evidence of equivalence. Only rows labelled single factor change one configuration field; bundles change several components together and are not attributed to one mechanism.}",
          r"\label{tab:main-paired}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{@{}l" + "c" * len(pm) + r"@{}}", r"\toprule", "Contrast & " + " & ".join(c[1] for c in pm) + r" \\"]
    for ds, name in (("ciciot", "CICIoT2023"), ("unsw", "UNSW-NB15")):
        L.append(r"\midrule")
        L.append(r"\multicolumn{" + str(len(pm) + 1) + r"}{@{}l}{\textit{" + name + r"}} \\")
        for v, r_, lab in keep:
            cells = []
            for m, _, n in pm:
                q = PE[(PE.dataset == ds) & (PE.variant == v) & (PE.reference == r_) & (PE.metric == m)].iloc[0]
                cells.append(f"{q.mean_diff:+.{n}f} ({q.sd_diff:.{n}f}) [{int(q.n_variant_lower)}/5]".replace("-", "$-$"))
            L.append(lab + " & " + " & ".join(cells) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}}", r"\end{table*}", ""]
    return "\n".join(L)


def main():
    if PKG.exists() and any(PKG.iterdir()):
        sys.exit("Table4_V2_Package exists and is not empty; refusing to overwrite")
    PKG.mkdir(exist_ok=True)
    rows = [extract(ds, arm, s) for ds in DATASETS for arm in ALL_ARMS for s in SEEDS]
    P = pd.DataFrame(rows)
    P.to_csv(PKG / "TABLE4_V2_PER_SEED.csv", index=False)
    g = P.groupby(["dataset", "arm"])
    num = [c for c in P.columns if P[c].dtype.kind in "fi" and c not in ("seed", "best_round")] + ["best_round"]
    S = g[num].agg(["mean", "std"]); S.columns = [f"{a}_{'mean' if b == 'mean' else 'sd'}" for a, b in S.columns]
    S["n_seeds"] = g.size(); S = S.reset_index()
    S["label"] = S.arm.map(ARM_LABEL)
    S.to_csv(PKG / "TABLE4_V2_SUMMARY.csv", index=False)
    PE = paired_rows(P)
    PE.to_csv(PKG / "TABLE4_V2_PAIRED_EFFECTS.csv", index=False)
    (PKG / "TABLE4_V2_FINAL_TABLE.tex").write_text(build_table(S, PE), encoding="utf-8")
    qa = qa_checks(P)
    (PKG / "_qa_auto.md").write_text("| Check | Result | Detail |\n|---|---|---|\n" + "\n".join(f"| {n} | {'PASS' if ok else '**FAIL**'} | {d} |" for n, ok, d in qa) + "\n", encoding="utf-8")
    print(len(P), "per-seed rows;", len(PE), "paired rows;", sum(ok for _, ok, _ in qa), "/", len(qa), "QA checks pass")
    for n, ok, d in qa:
        if not ok:
            print("FAIL:", n, d)


if __name__ == "__main__":
    main()
