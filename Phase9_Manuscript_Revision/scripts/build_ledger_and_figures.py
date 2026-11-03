"""Phase 9: authoritative results ledger, paired contrasts and manuscript figures. READ-ONLY on all experiment outputs.

Inputs (never modified): results_phase6c/, results_phase7b/, posthoc_threshold_fix/phase6c_posthoc_with_deltas.csv, docs/phase8/tables/.
Outputs: Phase9_Manuscript_Revision/{ledger,figures,tables}/.   Run: python Phase9_Manuscript_Revision/scripts/build_ledger_and_figures.py
"Original" = value stored by the historical run (before the Phase 7b threshold fix); "audited" = checkpoint re-evaluated with the single decision rule.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
P9 = ROOT / "Phase9_Manuscript_Revision"
LED, FIG, TAB = P9 / "ledger", P9 / "figures", P9 / "tables"
for d in (LED, FIG, FIG / "data", TAB):
    d.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "axes.titlesize": 9, "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "figure.dpi": 150, "svg.fonttype": "none", "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
C = {"ref": "#1b6ca8", "cor": "#d55e00", "grey": "#7a7a7a", "green": "#2a9d8f", "purple": "#7b4fa3", "black": "#222222", "gold": "#b8860b"}
LABEL = {"clean_centralized": "Centralized", "clean_fedavg": "FedAvg (clean)", "scenario_fedavg_random": "FedAvg random\n(attack)", "scenario_fedavg_topk": "FedAvg top-k\n(attack)",
         "robust_random_no_imputation": "Robust random\nno imputation", "reference": "Reference", "corrected": "Corrected", "reference_gaussian": "Reference\n+Gaussian",
         "corrected_gaussian": "Corrected\n+Gaussian", "ctl_delivery_coupled": "Ref + packet-\ncoupled delivery", "ctl_selection_uniform": "Ref + uniform\nselection",
         "ctl_selection_coverage": "Ref + coverage\nselection", "fail0p3_reference": "Reference\n30% failures", "fail0p3_corrected": "Corrected\n30% failures"}


def save(fig, name):
    for ext in ("pdf", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight")
    import os
    if os.environ.get("FIG_PREVIEW_DIR"):
        fig.savefig(Path(os.environ["FIG_PREVIEW_DIR"]) / f"{name}.png", bbox_inches="tight", dpi=110)
    plt.close(fig)


def sd(x):
    return float(np.std(x, ddof=1)) if len(x) > 1 else float("nan")


# ------------------------------------------------------------------ per-run ledger (Phase 6C, original vs audited)
ph = pd.read_csv(ROOT / "posthoc_threshold_fix" / "phase6c_posthoc_with_deltas.csv")
ph = ph[ph["phase"] == 1].copy() if "phase" in ph and ph["phase"].nunique() > 1 else ph.copy()
per = pd.DataFrame({
    "dataset": ph.dataset, "arm": ph.arm, "seed": ph.seed, "evaluation_partition": "report partition of three-way group-disjoint validation (calibration->threshold, selection->checkpoint)",
    "best_round": ph.best_round_recorded,
    "best_auc_original": ph.best_rep_auc_old, "best_auc_audited": ph.best_rep_auc_new, "best_f1_original": ph.best_rep_f1_old, "best_f1_audited": ph.best_rep_f1_new,
    "best_recall_audited": ph.best_rep_recall_new, "best_fpr_audited": ph.best_rep_fpr_new,
    "last_auc_original": ph.last_rep_auc_old, "last_auc_audited": ph.last_rep_auc_new, "last_f1_original": ph.last_rep_f1_old, "last_f1_audited": ph.last_rep_f1_new,
    "last_recall_audited": ph.last_rep_recall_new, "last_fpr_audited": ph.last_rep_fpr_new,
    "source_artifact": ("results_phase6c/" + ph.dataset + "/" + ph.arm + "/seed_" + ph.seed.astype(str) + "/final_validation_metrics.json"),
    "audit_artifact": "posthoc_threshold_fix/phase6c_posthoc_with_deltas.csv",
})
per["n_cond"] = 1
per.drop(columns="n_cond").to_csv(LED / "ledger_per_run_phase6c.csv", index=False)

# network/fairness per run (read-only from run folders)
rows = []
for r in per.itertuples():
    d = ROOT / "results_phase6c" / r.dataset / r.arm / f"seed_{r.seed}"
    rm = pd.read_csv(d / "round_metrics.csv")
    rm = rm[rm["round"] > 0]
    pc = json.loads((d / "phase6c_diagnostics.json").read_text())
    nm = pd.read_csv(d / "network_metrics.csv")
    rows.append(dict(dataset=r.dataset, arm=r.arm, seed=r.seed, delay_ms=rm.mean_end_to_end_delay_ms.mean(), pdr=rm.mean_pdr.mean(), path_stability=rm.mean_path_stability.mean(),
                     transfer_mbps=rm.mean_transfer_efficiency_mbps.mean(), gini=pc["participation"]["selection_gini"],
                     never_selected=pc["participation"]["longest_exclusion_gap_rounds_selection"]["clients_never_selected"],
                     delivered_ratio=float((nm["update_delivered"] == True).mean()), received_ratio=float((nm["received_by_server"] == True).mean()),
                     surrogate_share=rm.loc[rm.received_updates > 0, "surrogate_weight_share"].fillna(0).mean(), kept_real=(rm.kept_updates - rm.imputed_clients.fillna(0)).mean(),
                     max_train_loss=rm.mean_train_loss.max()))
net = pd.DataFrame(rows)
net.to_csv(LED / "ledger_network_fairness_per_run_phase6c.csv", index=False)
full = per.merge(net, on=["dataset", "arm", "seed"])

# arm-level ledger
metrics = ["best_auc_original", "best_auc_audited", "best_f1_audited", "best_recall_audited", "best_fpr_audited", "last_auc_original", "last_auc_audited", "last_f1_audited",
           "last_recall_audited", "last_fpr_audited", "delay_ms", "pdr", "path_stability", "transfer_mbps", "gini", "never_selected", "delivered_ratio", "received_ratio", "surrogate_share"]
g = full.groupby(["dataset", "arm"])
arm = g[metrics].mean().add_suffix("_mean").join(g[metrics].std(ddof=1).add_suffix("_sd")).join(g.size().rename("n_seeds"))
arm["collapsed_runs_last_auc_lt_0.80"] = g["last_auc_audited"].apply(lambda s: int((s < 0.80).sum()))
arm["protocol"] = "Phase 6C validation-only, seeds 12-16, report partition"
arm.round(5).to_csv(LED / "ledger_arm_summary_phase6c.csv")

# ------------------------------------------------------------------ paired contrasts (audited values)


def paired(a, b, ds, col):
    A = full[(full.dataset == ds) & (full.arm == a)].sort_values("seed")[col].to_numpy()
    B = full[(full.dataset == ds) & (full.arm == b)].sort_values("seed")[col].to_numpy()
    d = A - B
    n = len(d)
    s = d.std(ddof=1)
    ci = stats.t.interval(0.95, n - 1, loc=d.mean(), scale=s / math.sqrt(n)) if s > 0 else (np.nan, np.nan)
    flips = [abs((d * np.array(f)).mean()) for f in itertools.product([1, -1], repeat=n)]
    return dict(dataset=ds, contrast=f"{a} - {b}", metric=col, n=n, mean_diff=d.mean(), sd=s, ci95_lo=ci[0], ci95_hi=ci[1], dz=d.mean() / s if s > 0 else np.nan,
                n_first_better=int((d > 0).sum()), n_second_better=int((d < 0).sum()), p_exact_signflip=float(np.mean([f >= abs(d.mean()) - 1e-15 for f in flips])))


pairs = [("corrected", "reference"), ("fail0p3_corrected", "fail0p3_reference"), ("nat_corrected", "nat_reference"), ("reference", "scenario_fedavg_topk"), ("reference", "scenario_fedavg_random"),
         ("reference", "clean_fedavg"), ("reference_gaussian", "reference"), ("corrected_gaussian", "corrected"), ("ctl_selection_uniform", "reference"), ("ctl_selection_coverage", "reference"),
         ("ctl_delivery_coupled", "reference"), ("ctl_imputation_none", "reference"), ("ctl_weighting_uniform", "reference"), ("ctl_momentum0_lr0p5", "reference"),
         ("ctl_imputation_postfilter", "reference"), ("ctl_imputation_cap010", "reference"), ("corrected_gaussian", "reference_gaussian")]
pc = pd.DataFrame([paired(a, b, ds, c) for ds in ("unsw", "ciciot") for a, b in pairs for c in ("best_auc_audited", "last_auc_audited", "best_f1_audited")])
pc.round(5).to_csv(LED / "ledger_paired_contrasts_phase6c_audited.csv", index=False)

# ------------------------------------------------------------------ Phase 7b ledger
p7 = pd.read_csv(ROOT / "docs/phase8/tables/T2a_phase7b_per_run.csv")
p7["protocol"] = "Phase 7b validation-only, UNSW, seeds 17-21, report partition, fixed threshold logic"
p7["source_artifact"] = "results_phase7b/unsw/" + p7.arm + "/seed_" + p7.seed.astype(str) + "/final_validation_metrics.json"
p7.to_csv(LED / "ledger_per_run_phase7b.csv", index=False)

# ================================================================== FIGURES
ORDER_MAIN = ["clean_centralized", "clean_fedavg", "scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation", "reference", "corrected", "reference_gaussian", "corrected_gaussian"]


def dots(ax, x, vals, color, marker="o", w=0.12):
    jit = np.linspace(-w, w, len(vals))
    ax.scatter(np.full(len(vals), x) + jit, vals, s=9, color=color, alpha=0.75, marker=marker, linewidths=0, zorder=3)


# Fig 2: best vs last AUC, per seed
fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.2))
for ax, ds, ttl in zip(axes, ("unsw", "ciciot"), ("UNSW-NB15", "CICIoT2023 (file-group split)")):
    for i, a in enumerate(ORDER_MAIN):
        s = full[(full.dataset == ds) & (full.arm == a)].sort_values("seed")
        for off, col, c, mk in ((-0.17, "best_auc_audited", C["ref"], "o"), (0.17, "last_auc_audited", C["cor"], "s")):
            dots(ax, i + off, s[col].to_numpy(), c, mk, 0.08)
            ax.hlines(s[col].mean(), i + off - 0.13, i + off + 0.13, color=c, lw=1.6, zorder=4)
    ax.set_xticks(range(len(ORDER_MAIN)))
    ax.set_xticklabels([LABEL[a] for a in ORDER_MAIN], fontsize=6)
    ax.set_ylabel("ROC-AUC (report partition)")
    ax.set_title(ttl, loc="left")
    ax.set_ylim(0.45, 1.01)
    ax.grid(axis="y", lw=0.3, alpha=0.5)
axes[0].scatter([], [], color=C["ref"], marker="o", s=12, label="best checkpoint (selected on selection partition)")
axes[0].scatter([], [], color=C["cor"], marker="s", s=12, label="last round (30)")
axes[0].legend(loc="lower right", frameon=False)
fig.tight_layout()
save(fig, "fig02_best_vs_last_auc")
full[full.arm.isin(ORDER_MAIN)][["dataset", "arm", "seed", "best_auc_audited", "last_auc_audited"]].to_csv(FIG / "data" / "fig02_best_vs_last_auc.csv", index=False)

# Fig 3: Reference vs Corrected paired by seed
fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.7), sharey=False)
for ax, (ds, col, ttl) in zip(axes, (("unsw", "best_auc_audited", "UNSW best"), ("unsw", "last_auc_audited", "UNSW last"), ("ciciot", "best_auc_audited", "CIC best"), ("ciciot", "last_auc_audited", "CIC last"))):
    R = full[(full.dataset == ds) & (full.arm == "reference")].sort_values("seed")[col].to_numpy()
    K = full[(full.dataset == ds) & (full.arm == "corrected")].sort_values("seed")[col].to_numpy()
    for r_, k_ in zip(R, K):
        ax.plot([0, 1], [r_, k_], color=C["grey"], lw=0.8, alpha=0.8)
    ax.scatter(np.zeros(5), R, color=C["ref"], s=14, zorder=3)
    ax.scatter(np.ones(5), K, color=C["cor"], s=14, zorder=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Reference", "Corrected"], fontsize=6)
    ax.set_title(ttl, loc="left")
    ax.grid(axis="y", lw=0.3, alpha=0.5)
axes[0].set_ylabel("ROC-AUC")
fig.tight_layout()
save(fig, "fig03_reference_vs_corrected_paired")
full[full.arm.isin(["reference", "corrected"])][["dataset", "arm", "seed", "best_auc_audited", "last_auc_audited"]].to_csv(FIG / "data" / "fig03_reference_vs_corrected_paired.csv", index=False)

# Fig 4: routing / participation trade-off
POL = ["scenario_fedavg_random", "ctl_selection_uniform", "ctl_selection_coverage", "reference", "corrected"]
POLL = {"scenario_fedavg_random": None, "ctl_selection_uniform": "Uniform random", "ctl_selection_coverage": "Coverage-aware", "reference": "Top-k (Reference)", "corrected": "Corrected\n(coverage+packet-coupled)"}
POL = ["ctl_selection_uniform", "ctl_selection_coverage", "reference", "corrected"]
panels = [("pdr", "Mean packet delivery ratio\n(first transmission)", None), ("delay_ms", "Mean end-to-end delay (ms)", None), ("received_ratio", "Updates received by server /\nselected", None),
          ("gini", "Selection Gini (0 = equal)", None), ("never_selected", "Clients never selected (of 50)", None), ("best_auc_audited", "Best-checkpoint ROC-AUC", None)]
fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.6))
for ax, (col, ylab, _) in zip(axes.ravel(), panels):
    for i, a in enumerate(POL):
        v = full[(full.dataset == "unsw") & (full.arm == a)][col].to_numpy()
        ax.bar(i, v.mean(), color=[C["grey"], C["green"], C["ref"], C["cor"]][i], alpha=0.85, width=0.65)
        dots(ax, i, v, C["black"], "o", 0.14)
    ax.set_xticks(range(len(POL)))
    ax.set_xticklabels([POLL[a].replace("\n", " ") for a in POL], rotation=35, ha="right", fontsize=5.5)
    ax.set_ylabel(ylab, fontsize=7)
    if col == "best_auc_audited":
        ax.set_ylim(0.96, 0.99)
axes[0, 0].set_title("UNSW-NB15, 5 seeds (dots = seeds)", loc="left", fontsize=7)
fig.tight_layout()
save(fig, "fig04_routing_fairness_tradeoff")
full[(full.dataset == "unsw") & full.arm.isin(POL)][["arm", "seed", "pdr", "delay_ms", "received_ratio", "gini", "never_selected", "best_auc_audited"]].to_csv(FIG / "data" / "fig04_routing_fairness_tradeoff.csv", index=False)

# Fig 5: attack robustness + MAD filter by genuine-update count
t5b = pd.read_csv(ROOT / "docs/phase8/tables/T5b_mad_filter_by_number_of_real_updates.csv")
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
ax = axes[0]
for i, a in enumerate(["scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation", "reference"]):
    for off, col, c, mk in ((-0.18, "best_auc_audited", C["ref"], "o"), (0.18, "last_auc_audited", C["cor"], "s")):
        v = full[(full.dataset == "unsw") & (full.arm == a)].sort_values("seed")[col].to_numpy()
        dots(ax, i + off, v, c, mk, 0.09)
        ax.hlines(v.mean(), i + off - 0.13, i + off + 0.13, color=c, lw=1.6, zorder=4)
ax.set_xticks(range(4))
ax.set_xticklabels(["FedAvg\nrandom", "FedAvg\ntop-k", "Robust\nrandom", "Reference\n(top-k)"], fontsize=6)
ax.set_ylabel("ROC-AUC, UNSW, 20% sign-flip")
ax.set_title("(a) Undefended vs MAD-filtered", loc="left")
ax.scatter([], [], c=C["ref"], marker="o", s=12, label="best")
ax.scatter([], [], c=C["cor"], marker="s", s=12, label="last")
ax.legend(frameon=False, loc="lower right")
ax = axes[1]
m6 = t5b[t5b.results == "6C"]
x = np.arange(len(m6))
ax.bar(x - 0.2, m6.honest_rejection_rate * 100, 0.4, color=C["green"], label="honest updates rejected")
ax.bar(x + 0.2, m6.malicious_acceptance_rate * 100, 0.4, color=C["cor"], label="malicious updates accepted")
for i, r in enumerate(m6.itertuples()):
    ax.text(i, 104, f"n={int(r.malicious)}", ha="center", fontsize=5.5)
ax.set_xticks(x)
ax.set_xticklabels(m6.n_real_bin.astype(str))
ax.set_xlabel("genuine (non-surrogate) updates in the round")
ax.set_ylabel("% of updates")
ax.set_ylim(0, 112)
ax.set_title("(b) MAD filter vs sparse updates (Phase 6C)", loc="left")
ax.legend(frameon=False, fontsize=6, loc="center right")
fig.tight_layout()
save(fig, "fig05_attack_robustness_and_mad")
t5b.to_csv(FIG / "data" / "fig05b_mad_filter_by_genuine_updates.csv", index=False)

# Fig 6: failures + guard (Phase 7b), per seed last/best AUC
arms7 = ["reference", "corrected", "p7_corrected_guard", "fail0p3_reference", "fail0p3_corrected", "fail0p3_p7_corrected_guard"]
lab7 = ["Reference", "Corrected", "Corrected\n+Guard", "Reference\n30% fail", "Corrected\n30% fail", "Corrected+Guard\n30% fail"]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
for ax, col, ttl in zip(axes, ("best_auc", "last_auc"), ("(a) best checkpoint", "(b) last round (30)")):
    for i, a in enumerate(arms7):
        v = p7[p7.arm == a].sort_values("seed")[col].to_numpy()
        dots(ax, i, v, [C["ref"], C["cor"], C["purple"]][i % 3], "o", 0.15)
        ax.hlines(v.mean(), i - 0.25, i + 0.25, color=C["black"], lw=1.4, zorder=4)
    ax.axhline(0.90, color=C["grey"], lw=0.6, ls="--")
    ax.set_xticks(range(6))
    ax.set_xticklabels(lab7, fontsize=5.5)
    ax.set_title(ttl, loc="left")
    ax.grid(axis="y", lw=0.3, alpha=0.5)
axes[0].set_ylabel("ROC-AUC, UNSW, seeds 17-21")
fig.tight_layout()
save(fig, "fig06_failures_and_guard_phase7b")
p7[p7.arm.isin(arms7)][["arm", "seed", "best_auc", "last_auc", "collapse", "skipped_rounds"]].to_csv(FIG / "data" / "fig06_failures_and_guard_phase7b.csv", index=False)

# Fig 7: Gaussian cost + surrogate share
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6))
for ax, (a, b, ttl) in zip(axes[:2], (("reference", "reference_gaussian", "Reference"), ("corrected", "corrected_gaussian", "Corrected"))):
    for j, (ds, c) in enumerate((("unsw", C["ref"]), ("ciciot", C["cor"]))):
        for i, arm_ in enumerate((a, b)):
            v = full[(full.dataset == ds) & (full.arm == arm_)].sort_values("seed")["best_auc_audited"].to_numpy()
            dots(ax, i + (j - 0.5) * 0.32, v, c, "o", 0.06)
            ax.hlines(v.mean(), i + (j - 0.5) * 0.32 - 0.1, i + (j - 0.5) * 0.32 + 0.1, color=c, lw=1.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["no noise", "+Gaussian"])
    ax.set_title(ttl, loc="left")
    ax.set_ylabel("best-checkpoint ROC-AUC")
axes[0].scatter([], [], c=C["ref"], s=12, label="UNSW")
axes[0].scatter([], [], c=C["cor"], s=12, label="CIC")
axes[0].legend(frameon=False, loc="center left")
ax = axes[2]
ars = ["reference", "reference_gaussian", "corrected", "corrected_gaussian"]
for i, a in enumerate(ars):
    for j, (ds, c) in enumerate((("unsw", C["ref"]), ("ciciot", C["cor"]))):
        v = full[(full.dataset == ds) & (full.arm == a)]["surrogate_share"].to_numpy()
        ax.bar(i + (j - 0.5) * 0.36, v.mean(), 0.34, color=c, alpha=0.85)
ax.axhline(0.10, color=C["black"], lw=0.7, ls="--")
ax.text(3.45, 0.115, "configured cap 0.10 (corrected arms)", ha="right", fontsize=5.5)
ax.set_xticks(range(4))
ax.set_xticklabels(["Ref", "Ref\n+Gauss", "Corr", "Corr\n+Gauss"], fontsize=6)
ax.set_ylabel("surrogate share of aggregate weight")
fig.tight_layout()
save(fig, "fig07_gaussian_and_surrogate_share")
full[full.arm.isin(ars)][["dataset", "arm", "seed", "best_auc_audited", "surrogate_share"]].to_csv(FIG / "data" / "fig07_gaussian_and_surrogate_share.csv", index=False)

# Fig 1: system pipeline (schematic)
fig, ax = plt.subplots(figsize=(7.2, 2.6))
ax.axis("off")
boxes = [(0.00, "IoT clients (50)\nlocal MLP training\n(2 epochs, Dirichlet 0.5)"), (0.19, "Edge routing\nscore = latency,\nstability, security"), (0.38, "Selection (10/round)\ntop-k | coverage-aware\n| uniform"),
         (0.57, "Delivery model\nindependent draw |\npacket-coupled + ARQ"), (0.76, "Cloud server\nMAD filter, surrogate\nimputation, momentum\n(+optional Gaussian)")]
for x0, t in boxes:
    ax.add_patch(plt.Rectangle((x0, 0.35), 0.17, 0.42, fc="#eef3f8", ec=C["ref"], lw=1))
    ax.text(x0 + 0.085, 0.56, t, ha="center", va="center", fontsize=6.3)
for x0 in (0.17, 0.36, 0.55, 0.74):
    ax.annotate("", xy=(x0 + 0.02, 0.56), xytext=(x0, 0.56), arrowprops=dict(arrowstyle="->", color=C["black"]))
ax.text(0.5, 0.92, "Simulated edge-cloud pipeline (one FL round); sign-flip attackers (20%) and client failures act on the update path", ha="center", fontsize=7)
ax.text(0.5, 0.12, "Evaluated protocol: validation-only; calibration -> threshold, selection -> checkpoint, report -> metrics. Final-test data locked.", ha="center", fontsize=6.3, color=C["grey"])
ax.set_xlim(0, 0.95)
ax.set_ylim(0, 1)
save(fig, "fig01_pipeline")
print("ledger + figures written to", P9)
