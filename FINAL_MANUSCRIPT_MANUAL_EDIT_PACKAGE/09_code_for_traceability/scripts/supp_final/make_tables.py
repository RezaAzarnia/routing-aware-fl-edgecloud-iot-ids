"""Builds PROVENANCE.json, generated tables (markdown + LaTeX) from the verified per-seed / paired CSVs. Read-only on runs.
usage: python scripts/supp_final/make_tables.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "Supplementary_Experiments_Package"
sys.path.insert(0, str(ROOT / "scripts" / "supp_v2"))
from supp_common import V1_MANIFEST, MANIFEST, load_manifest, sha256_file  # noqa: E402

P = pd.read_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv")
E = pd.read_csv(PKG / "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv")
DSN = {"unsw": "UNSW-NB15", "ciciot": "CICIoT2023"}


def ms(ds, arm, m, d=4):
    v = P[(P.dataset == ds) & (P.arm == arm)][m].astype(float)
    return f"{v.mean():.{d}f} ({v.std(ddof=1):.{d}f})" if len(v) > 1 else f"{v.mean():.{d}f}"


def eff(ds, var, ref, m="auc_sel", fam=None):
    q = E[(E.dataset == ds) & (E.variant == var) & (E.reference == ref) & (E.metric == m)]
    if fam:
        q = q[q.family == fam]
    if q.empty:
        return "n/a", None
    r = q.iloc[0]
    return f"{r.mean_diff:+.4f} [{r.ci95_lo:+.4f}, {r.ci95_hi:+.4f}] (n={int(r.n_pairs)}; {int(r.n_deteriorated) if pd.notna(r.n_deteriorated) else '-'}↓/{int(r.n_improved) if pd.notna(r.n_improved) else '-'}↑)", r


tabs = {}
# T1 attack
rows = []
for ds in DSN:
    for cn, tm, sf20 in (("no attack", "noatk", None), ("SF 10%", "sf10", None), ("SF 20%", None, ("scenario_fedavg_topk", "reference")), ("SF 30%", "sf30", None), ("BSF 20%", "bsf20", None), ("LF 20%", "lf20", None)):
        fa = sf20[0] if sf20 else f"atk_fedavg_{tm}"; rf = sf20[1] if sf20 else f"atk_ref_{tm}"
        rows.append([DSN[ds], cn, ms(ds, fa, "auc_sel"), ms(ds, rf, "auc_sel"), ms(ds, fa, "auc_last"), ms(ds, rf, "auc_last"),
                     ms(ds, rf, "malicious_retention", 3) if cn != "no attack" else "-", ms(ds, rf, "honest_rejection", 3), eff(ds, rf, fa)[0]])
tabs["T1_attack"] = (["Dataset", "Condition", "FedAvg AUC sel", "MAD+surr AUC sel", "FedAvg AUC last", "MAD+surr AUC last", "malicious retained", "honest rejected", "paired Δ AUC sel (ref − FedAvg) [95% CI]"], rows)
# T2 sensitivity
lab = {"sens_k1p5": ("MAD k=1.5", "reference_gaussian"), "sens_k3p5": ("MAD k=3.5", "reference_gaussian"), "sens_alpha0p1": ("Dirichlet α=0.1", "reference_gaussian"), "sens_alpha1p0": ("Dirichlet α=1.0", "reference_gaussian"),
       "sens_C0p5x": ("clip 0.5×", "reference_gaussian"), "sens_C2x": ("clip 2×", "reference_gaussian"), "sens_chi0_dp": ("χrec=0 (DP)", "reference_gaussian"), "sens_chi0": ("χrec=0 (no noise)", "reference"),
       "sens_chi0p25": ("χrec=0.25 (no noise)", "reference"), "sens_chi0p75": ("χrec=0.75 (no noise)", "reference")}
rows = [[DSN[ds], l, ref, eff(ds, a, ref, fam="B_sensitivity")[0]] for ds in DSN for a, (l, ref) in lab.items()]
tabs["T2_sensitivity"] = (["Dataset", "Variant", "Parent arm", "paired Δ ROC-AUC (selected) [95% CI]"], rows)
# T3 2x2
rows = []
for ds in DSN:
    for l, a in (("routing ON / surrogate OFF", "ctl_imputation_none"), ("routing ON / surrogate ON", "reference"), ("routing OFF / surrogate OFF", "t4_e2_robust_random_path"), ("routing OFF / surrogate ON", "ix_routeoff_surron")):
        rows.append([DSN[ds], l, ms(ds, a, "auc_sel"), ms(ds, a, "f1_sel"), ms(ds, a, "surrogate_weight_share_mean", 3), ms(ds, a, "rounds_surrogate_only", 3)])
    ir = E[(E.dataset == ds) & (E.variant == "interaction") & (E.metric == "auc_sel")].iloc[0]
    rows.append([DSN[ds], "interaction contrast", f"{ir.mean_diff:+.4f} [{ir.ci95_lo:+.4f}, {ir.ci95_hi:+.4f}]", f"exact sign-flip p={ir.exact_signflip_p:.4f} (n=5, floor 0.0625)", "", ""])
tabs["T3_interaction"] = (["Dataset", "Cell", "ROC-AUC sel mean (SD)", "F1 sel mean (SD)", "surrogate weight share", "surrogate-only rounds (fraction)"], rows)
# T4 participation
rows = []
for ds in DSN:
    for a, l in (("part_topk_indep", "top-k / indep."), ("part_topk_coup", "top-k / coupled"), ("part_coverage_indep", "coverage / indep."), ("part_coverage_coup", "coverage / coupled"), ("part_uniform_indep", "uniform / indep."), ("part_uniform_coup", "uniform / coupled")):
        rows.append([DSN[ds], l, ms(ds, a, "auc_sel"), ms(ds, a, "selection_gini", 3), ms(ds, a, "clients_never_selected", 1), ms(ds, a, "worst_client_recall", 3), ms(ds, a, "p10_client_recall", 3), ms(ds, a, "mean_recall_never_selected", 3), ms(ds, a, "surrogate_weight_share_mean", 3)])
tabs["T4_participation"] = (["Dataset", "Policy / network", "ROC-AUC sel", "selection Gini", "never-selected clients", "worst eligible-client held-out recall", "P10 recall", "mean recall of never-selected", "surrogate weight share"], rows)
# T5 scalability
rows = []
for ds in DSN:
    for a, l in (("scale_n25_k5", "N=25,k=5"), ("scale_n25_k10", "N=25,k=10"), ("scale_n50_k10", "N=50,k=10 (n=3 seeds)"), ("scale_n100_k10", "N=100,k=10"), ("scale_n100_k20", "N=100,k=20")):
        v = P[(P.dataset == ds) & (P.arm == a)]
        rows.append([DSN[ds], l, ms(ds, a, "auc_sel"), f"{v.wall_seconds.mean():.0f}", f"{v.cpu_seconds.mean():.0f}", f"{v.peak_working_set_mb.mean():.0f}", f"{v.mean_local_train_seconds_per_client.mean():.3f}", f"{v.bytes_on_wire.mean() / 1e6:.1f}", f"{v.surrogate_weight_share_mean.mean():.3f}"])
    v = P[(P.dataset == ds) & (P.arm == "reference_gaussian")]
    rows.append([DSN[ds], "N=50,k=10 reference_gaussian (n=5)", ms(ds, "reference_gaussian", "auc_sel"), f"{v.wall_seconds.mean():.0f}", f"{v.cpu_seconds.mean():.0f}", f"{v.peak_working_set_mb.mean():.0f}", f"{v.mean_local_train_seconds_per_client.mean():.3f}", f"{v.bytes_on_wire.mean() / 1e6:.1f}", f"{v.surrogate_weight_share_mean.mean():.3f}"])
tabs["T5_scalability"] = (["Dataset", "Configuration (3 seeds 12-14)", "ROC-AUC sel", "wall s/run", "CPU s/run", "peak working set MB", "local-train s/client-update", "simulated MB on wire/run", "surrogate weight share"], rows)
# T6 chi0 abstention
a = pd.read_csv(PKG / "V2_ABSTENTION_AND_ACCOUNTING_PER_RUN.csv")
a = a[a.arm == "sens_chi0_dp"]
rows = []
for _, r in a.iterrows():
    ref = P[(P.dataset == r.dataset) & (P.arm == "reference_gaussian") & (P.seed == r.seed)].iloc[0]
    me = P[(P.dataset == r.dataset) & (P.arm == "sens_chi0_dp") & (P.seed == r.seed)].iloc[0]
    rows.append([DSN[r.dataset], int(r.seed), int(r.abstention_rounds), r.abstention_round_ids if isinstance(r.abstention_round_ids, str) else "-", int(r.noisy_release_rounds), int(r.attempted_rounds),
                 f"{r.eps_release_diag:.3f}", f"{r.eps_attempted_diag:.3f}", f"{me.auc_sel:.4f}", f"{ref.auc_sel:.4f}", f"{me.auc_sel - ref.auc_sel:+.4f}", f"{me.auc_last - ref.auc_last:+.4f}", r.run_id])
tabs["T6_chi0_abstention"] = (["Dataset", "Seed", "abstention rounds", "round ids", "noisy releases", "attempted rounds", "ε release-based (diagnostic)", "ε attempted-round (diagnostic)", "AUC sel χ=0", "AUC sel reference_gaussian", "Δ sel", "Δ last", "V2 run id"], rows)


def md(h, rows):
    return "| " + " | ".join(h) + " |\n|" + "---|" * len(h) + "\n" + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows) + "\n"


def tex(h, rows, cap, lab):
    esc = lambda s: str(s).replace("%", "\\%").replace("&", "\\&").replace("_", "\\_").replace("α", "$\\alpha$").replace("χrec", "$\\chi_{\\mathrm{rec}}$").replace("χ", "$\chi$").replace("−", "$-$").replace("↓", "$\\downarrow$").replace("↑", "$\\uparrow$").replace("Δ", "$\\Delta$").replace("ε", "$\\varepsilon$").replace("×", "$\\times$").replace("≥", "$\\geq$").replace("-1", "-1")  # noqa: E731
    body = "\n".join(" & ".join(esc(c) for c in r) + " \\\\" for r in rows)
    return (f"\\begin{{table*}}[!t]\n\\caption{{{cap}}}\n\\label{{{lab}}}\n\\centering\\tiny\n\\setlength{{\\tabcolsep}}{{2pt}}\n\\begin{{tabular}}{{@{{}}{'l' * len(h)}@{{}}}}\n\\toprule\n" + " & ".join(esc(c) for c in h) + " \\\\\n\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")


caps = {"T1_attack": ("Attack robustness (five paired seeds 12--16; mean (SD); selected-checkpoint and last-round ROC--AUC). SF: sign-flip with exposure-controlled malicious fraction; BSF: norm-preserving sign-flip; LF: label flipping. All attacks are static and non-adaptive. SF 20\\% rows are the reused locked Phase~6C arms.", "tab:supp-attack"),
        "T2_sensitivity": ("Sensitivity of selected-checkpoint ROC--AUC to MAD coefficient, Dirichlet concentration, clipping threshold and $\\chi_{\\mathrm{rec}}$ (paired difference to the parent arm, 95\\% $t$-interval; $n$ = paired seeds; $\\downarrow/\\uparrow$ = seeds where the variant is lower/higher). With $n=5$ the smallest attainable two-sided exact sign-flip $p$ is 0.0625; no claim of statistical significance is made. $\\chi_{\\mathrm{rec}}$ is inert under the central-DP pipeline (see text).", "tab:supp-sens"),
        "T3_interaction": ("Routing$\\times$surrogate $2\\times2$ design (five seeds; matched traces within each routing state). Interaction = (surrogate effect | routing ON) $-$ (surrogate effect | routing OFF).", "tab:supp-interaction"),
        "T4_participation": ("Participation and held-out client recall (client holdouts never used for training; UNSW-NB15 from SUPP\\_V1, CICIoT2023 from SUPP\\_V2 with the leakage-safe holdout; the two protocols are not mixed). Recall is computed only for clients with at least 10 held-out attack rows (UNSW 43.8, CICIoT2023 48.4 of 50 on average).", "tab:supp-participation"),
        "T5_scalability": ("Scalability of the proposed central-DP pipeline (seeds 12--14). Wall-clock and CPU seconds are measured on one shared CPU host and are not controlled benchmarks; bytes are simulated serialized-update accounting.", "tab:supp-scale"),
        "T6_chi0_abstention": ("$\\chi_{\\mathrm{rec}}=0$ under the central-DP pipeline with the no-valid-contribution rule (SUPP\\_V2, five seeds). $\\varepsilon$ values are diagnostic RDP estimates under a Poisson-subsampling assumption, not certified guarantees.", "tab:supp-chi0")}
md_out = "# Generated tables (all values from SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv / _PAIRED_EFFECTS.csv)\n\n"
tx = "% Auto-generated supplementary tables. Requires booktabs. Source: Supplementary_Experiments_Package CSVs (run IDs in PER_SEED.csv).\n"
for k, (h, rows) in tabs.items():
    pd.DataFrame(rows, columns=h).to_csv(PKG / f"TABLE_{k}.csv", index=False)
    md_out += f"## {k}\n\n" + md(h, rows) + "\n"
    tx += "\n" + tex(h, rows, *caps[k])
(PKG / "GENERATED_TABLES.md").write_text(md_out, encoding="utf-8")
(PKG / "SUPPLEMENTARY_TABLES_GENERATED.tex").write_text(tx, encoding="utf-8")

# provenance
M1, M2 = load_manifest(V1_MANIFEST), load_manifest(MANIFEST)
qa = json.loads((PKG / "FINAL_QA_RESULTS.json").read_text())
prov = {"schema": "supplementary_final_provenance_v1", "git_head_at_analysis": __import__("subprocess").run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
        "supp_v1": {"manifest": "docs/supp_v1/EXPERIMENT_MANIFEST.json", "manifest_sha256": M1["manifest_sha256"], "code_fingerprint": M1["code_fingerprint"], "runs_locked": 278, "verified": 246, "failed": 7, "pending": 25,
                    "status": "frozen; failed/pending identities completed under SUPP_V2"},
        "supp_v2": {"manifest": "docs/supp_v2/EXPERIMENT_MANIFEST.json", "manifest_sha256": M2["manifest_sha256"], "code_fingerprint": M2["code_fingerprint"], "runs_locked": 44, "verified": 44, "source_overlay": ["src_v2/data.py", "src_v2/experiment.py"],
                    "overlay_sha256": {f: sha256_file(ROOT / f) for f in ("src_v2/data.py", "src_v2/experiment.py")}},
        "reused_evidence": {"phase6c_manifest": "docs/phase6c/EXPERIMENT_MANIFEST.json", "table4_v2_manifest": "docs/table4_v2/EXPERIMENT_MANIFEST.json",
                            "phase6c_ledger": "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv", "ledger_sha256": sha256_file(ROOT / "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv"),
                            "note": "Phase 6C detection metrics for reused arms come from the audited ledger (AP unaudited)"},
        "datasets": M2["datasets"], "analysis_rules": ["one row per (dataset, arm, seed) identity; 8 V2 regression controls are bit-identical to V1 and counted once (V1 row kept)",
                                                         "sens_chi0_dp (both datasets) taken entirely from SUPP_V2 (seeds 12/14 bit-identical to V1)", "CICIoT2023 participation exists only under the V2 client-holdout protocol and is never compared with Phase 6C CIC runs",
                                                         "statistics: paired t-interval (df n-1), exact sign-flip test, min attainable two-sided p 0.0625 for n=5 and 0.25 for n=3; exploratory"],
        "identity_rows": {k: int(v) for k, v in P.source.value_counts().items()}, "final_qa": {"pass": qa["n_pass"], "fail": qa["n_fail"], "file": "FINAL_QA_RESULTS.json"},
        "scripts": {f"scripts/supp_final/{f}": sha256_file(ROOT / "scripts/supp_final" / f) for f in ("final_qa.py", "holdout_eval.py", "analyse_final.py", "figures_final.py", "make_tables.py")},
        "per_seed_file_sha256": {f: sha256_file(PKG / f) for f in ("SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv", "SUPPLEMENTARY_EXPERIMENTS_SUMMARY.csv", "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv", "SUPPLEMENTARY_HOLDOUT_CLIENT_METRICS.csv")},
        "runs": [{"run_id": r["run_id"], "dataset": r["dataset"], "arm": r["arm"], "seed": int(r["seed"]), "source": r["source"], "out_dir": r["out_dir"], "config_sha256": r["config_sha256"], "manifest_sha256": r["provenance_manifest_sha256"],
                  "regression_twin_v2": None if pd.isna(r["regression_twin_v2_run_id"]) else r["regression_twin_v2_run_id"]} for _, r in P.iterrows()],
        "hardware": "Intel Core i5-14400F, CPU-only, torch 2.15.0+cpu, Python 3.11.9, Windows 11", "reserved_test_sets_accessed": False,
        "limitations": ["no adaptive attack implemented", "aggregate-direction differences not logged", "epsilon values are diagnostic, not certified DP", "holdout labels used for the coupled-network driver link quality (disclosed)",
                        "CICIoT2023 provenance: byte-equivalent to a third-party release; official UNB provenance unverified", "wall-clock figures from one shared host, not controlled benchmarks"]}
(PKG / "SUPPLEMENTARY_EXPERIMENTS_PROVENANCE.json").write_text(json.dumps(prov, indent=1, default=str), encoding="utf-8")
print("ok", len(prov["runs"]), list(tabs))
