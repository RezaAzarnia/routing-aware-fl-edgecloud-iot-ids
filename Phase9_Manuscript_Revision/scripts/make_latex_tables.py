"""Phase 9: generate every numeric LaTeX table of the manuscript from the ledger CSVs (no hand-typed results).
Run after build_ledger_and_figures.py:  python Phase9_Manuscript_Revision/scripts/make_latex_tables.py"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
P9 = ROOT / "Phase9_Manuscript_Revision"
LED, TAB = P9 / "ledger", P9 / "tables"
TAB.mkdir(exist_ok=True)
arm = pd.read_csv(LED / "ledger_arm_summary_phase6c.csv").set_index(["dataset", "arm"])
pc = pd.read_csv(LED / "ledger_paired_contrasts_phase6c_audited.csv")
p7 = pd.read_csv(LED / "ledger_per_run_phase7b.csv")
mad = pd.read_csv(ROOT / "docs/phase8/tables/T5b_mad_filter_by_number_of_real_updates.csv")
cfgm = pd.read_csv(ROOT / "docs/phase8/tables/T6_baseline_configuration_matrix_phase6c.csv")
NAME = {"clean_centralized": "Centralized (no FL, clean)", "clean_fedavg": "FedAvg, clean", "scenario_fedavg_random": "FedAvg, random selection, attack",
        "scenario_fedavg_topk": "FedAvg, top-k selection, attack", "robust_random_no_imputation": "MAD filter, random selection, no imputation",
        "reference": "Reference", "corrected": "Corrected", "reference_gaussian": "Reference + Gaussian", "corrected_gaussian": "Corrected + Gaussian",
        "fail0p3_reference": "Reference, 30\\% failures", "fail0p3_corrected": "Corrected, 30\\% failures", "nat_reference": "Reference, natural attackers",
        "nat_corrected": "Corrected, natural attackers"}


def pm(m, s, d=4):
    return f"{m:.{d}f}$\\pm${s:.{d}f}" if not np.isnan(s) else f"{m:.{d}f}"


def write(name, body):
    (TAB / name).write_text(body, encoding="utf-8")


# ---- Table: main results
def main_table(ds):
    rows = []
    for a in ["clean_centralized", "clean_fedavg", "scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation", "reference", "corrected", "reference_gaussian", "corrected_gaussian",
              "fail0p3_reference", "fail0p3_corrected", "nat_reference", "nat_corrected"]:
        r = arm.loc[(ds, a)]
        rows.append(f"{NAME[a]} & {pm(r.best_auc_audited_mean, r.best_auc_audited_sd)} & {pm(r.last_auc_audited_mean, r.last_auc_audited_sd)} & {r.best_f1_audited_mean:.3f} & "
                    f"{r.best_recall_audited_mean:.3f} & {r.best_fpr_audited_mean:.3f} & {int(r['collapsed_runs_last_auc_lt_0.80'])}/5 \\\\")
    return ("\\begin{tabular}{@{}lcccccc@{}}\\toprule\nArm & AUC best & AUC last & F1 best & Recall best & FPR best & Collapsed\\\\\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")


write("tab_main_unsw.tex", main_table("unsw"))
write("tab_main_cic.tex", main_table("ciciot"))

# ---- Table: paired contrasts
SEL = [("corrected - reference", "Corrected $-$ Reference"), ("fail0p3_corrected - fail0p3_reference", "Corrected $-$ Reference, 30\\% failures"), ("nat_corrected - nat_reference", "Corrected $-$ Reference, natural attackers"),
       ("reference - scenario_fedavg_topk", "Reference $-$ undefended FedAvg (top-k)"), ("reference - clean_fedavg", "Reference $-$ clean FedAvg"),
       ("reference_gaussian - reference", "Gaussian cost, Reference"), ("corrected_gaussian - corrected", "Gaussian cost, Corrected")]
rows = []
for key, lab in SEL:
    cells = []
    for ds in ("unsw", "ciciot"):
        for met in ("best_auc_audited", "last_auc_audited"):
            r = pc[(pc.dataset == ds) & (pc.contrast == key) & (pc.metric == met)].iloc[0]
            cells.append(f"{r.mean_diff:+.4f} [{r.ci95_lo:+.4f},{r.ci95_hi:+.4f}] ({int(r.n_first_better)}/5)")
    rows.append(f"{lab} & " + " & ".join(cells) + " \\\\")
write("tab_paired.tex", "\\begin{tabular}{@{}lcccc@{}}\\toprule\n & \\multicolumn{2}{c}{UNSW-NB15} & \\multicolumn{2}{c}{CICIoT2023}\\\\\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\n"
      "Contrast (AUC difference) & best & last & best & last\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")

# ---- Table: ablations vs Reference
AB = [("ctl_selection_uniform", "Uniform selection"), ("ctl_selection_coverage", "Coverage-aware selection"), ("ctl_delivery_coupled", "Packet-coupled delivery (ARQ)"), ("ctl_imputation_none", "No surrogate imputation"),
      ("ctl_imputation_postfilter", "Real-only filter, post-filter surrogates"), ("ctl_imputation_cap010", "Surrogate cap 0.10"), ("ctl_weighting_uniform", "Uniform client weights"),
      ("ctl_momentum0_lr0p5", "No server momentum ($\\mu{=}0$, $\\eta_s{=}0.5$)"), ("ctl_momentum0_lr5p0", "No server momentum ($\\mu{=}0$, $\\eta_s{=}5$)")]
rows = []
for a, lab in AB:
    cells = []
    for ds in ("unsw", "ciciot"):
        for met in ("best_auc_audited", "last_auc_audited"):
            r = pc[(pc.dataset == ds) & (pc.contrast == f"{a} - reference") & (pc.metric == met)]
            if len(r):
                r = r.iloc[0]
                cells.append(f"{r.mean_diff:+.4f} ({int(r.n_first_better)}/5)")
            else:
                s1 = arm.loc[(ds, a)]
                s0 = arm.loc[(ds, "reference")]
                cells.append(f"{s1[met.replace('_audited','_audited') + '_mean'] - s0[met + '_mean']:+.4f}")
    rows.append(f"{lab} & " + " & ".join(cells) + " \\\\")
write("tab_ablation.tex", "\\begin{tabular}{@{}lcccc@{}}\\toprule\n & \\multicolumn{2}{c}{UNSW-NB15} & \\multicolumn{2}{c}{CICIoT2023}\\\\\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\n"
      "Single change to Reference & best & last & best & last\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")

# ---- Table: routing / network / fairness
POL = [("scenario_fedavg_random", "Uniform random (FedAvg arm)"), ("ctl_selection_uniform", "Uniform random"), ("ctl_selection_coverage", "Coverage-aware"), ("reference", "Top-k, independent draws (Reference)"),
       ("ctl_delivery_coupled", "Top-k, packet-coupled"), ("corrected", "Coverage-aware, packet-coupled (Corrected)")]
rows = []
for ds, dn in (("unsw", "UNSW-NB15"), ("ciciot", "CICIoT2023")):
    for a, lab in POL[1:]:
        r = arm.loc[(ds, a)]
        rows.append(f"{dn} & {lab} & {r.pdr_mean:.3f} & {r.delay_ms_mean:.1f} & {r.path_stability_mean:.3f} & {r.transfer_mbps_mean:.1f} & {r.received_ratio_mean:.3f} & {r.gini_mean:.3f} & {r.never_selected_mean:.1f} \\\\")
write("tab_network.tex", "\\begin{tabular}{@{}llccccccc@{}}\\toprule\nDataset & Policy & PDR & Delay (ms) & Path stab. & Transfer (Mbit/s) & Received/sel. & Gini & Never sel.\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")

# ---- Table: Phase 7b
A7 = [("reference", "Reference"), ("corrected", "Corrected"), ("p7_corrected_guard", "Corrected + Guard"), ("fail0p3_reference", "Reference, 30\\% failures"), ("fail0p3_corrected", "Corrected, 30\\% failures"),
      ("fail0p3_p7_corrected_guard", "Corrected + Guard, 30\\% failures"), ("ctl_delivery_coupled", "Packet-coupled control"), ("p7_delivery_guard", "Packet-coupled + Guard")]
rows = []
for a, lab in A7:
    s = p7[p7.arm == a]
    rows.append(f"{lab} & {pm(s.best_auc.mean(), s.best_auc.std(ddof=1))} & {pm(s.last_auc.mean(), s.last_auc.std(ddof=1))} & {s.best_f1.mean():.3f} & {s.last_f1.mean():.3f} & {s.best_recall.mean():.3f} & {s.collapse.sum()}/5 & {int(s.skipped_rounds.sum())} \\\\")
write("tab_phase7b.tex", "\\begin{tabular}{@{}lccccccc@{}}\\toprule\nArm (UNSW, seeds 17--21) & AUC best & AUC last & F1 best & F1 last & Recall best & Collapses & Skipped rounds\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")

# ---- Table: MAD
rows = []
for r in mad[mad.results == "6C"].itertuples():
    rows.append(f"{r.n_real_bin} & {int(r.rounds)} & {int(r.honest_rejected)}/{int(r.honest)} ({100 * r.honest_rejection_rate:.1f}\\%) & {int(r.malicious_accepted)}/{int(r.malicious)} ({100 * r.malicious_acceptance_rate:.1f}\\%) \\\\")
write("tab_mad.tex", "\\begin{tabular}{@{}lccc@{}}\\toprule\nGenuine updates in round & Rounds & Honest rejected & Malicious accepted\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")

# ---- Table: baseline configuration matrix (condensed)
sel = cfgm[cfgm.arm.isin(["scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation", "reference", "corrected", "reference_gaussian", "corrected_gaussian", "ctl_delivery_coupled", "ctl_selection_uniform",
                          "ctl_selection_coverage", "ctl_imputation_none", "ctl_weighting_uniform", "ctl_momentum0_lr0p5"])]
rows = []
tex = lambda v: str(v).replace("_", "\\_")
for r in sel.itertuples():
    sel_pol = "top\\_k" if r.selection == "default" else tex(r.selection)
    deliv = "independent" if r.delivery == "default" else "packet-coupled"
    sh = "pre-filter" if r.surrogate_handling == "default" else "post-filter"
    cap = "--" if r.sur_cap == "default" else r.sur_cap
    rows.append(f"{tex(r.arm)} & {tex(r.agg)} & {sel_pol} & {deliv} & {'yes' if str(r.recovery) == 'True' else 'no'} & {sh} & {cap} & {'uniform' if r.weighting == 'uniform' else 'samples'} & {r.momentum} & {tex(r.dp)} \\\\")
write("tab_config.tex", "\\begin{tabular}{@{}lllllllllc@{}}\\toprule\nArm & Aggregation & Selection & Delivery & Impute & Surrogates & Sur.\\ cap & Weights & Momentum & DP\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")
print("tables written")
