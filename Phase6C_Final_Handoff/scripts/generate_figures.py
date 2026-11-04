"""Generate Figures 1-12 (PDF, SVG, PNG@300dpi + per-figure CSV) from the exported tables only.

usage: python generate_figures.py --handoff <handoff dir>
Uses nothing but tables/*.csv, so it runs on any machine without the experiment folders.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OI = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "verm": "#D55E00", "sky": "#56B4E9", "pink": "#CC79A7",
      "yellow": "#F0E442", "grey": "#666666", "black": "#000000"}
DS = {"unsw": "UNSW-NB15", "ciciot": "CICIoT2023"}
LAB = {"clean_centralized": "Clean central.", "clean_fedavg": "Clean FedAvg", "scenario_fedavg_random": "FedAvg random (attack)",
       "scenario_fedavg_topk": "FedAvg top-k (attack)", "robust_random_no_imputation": "Robust random, no imput.",
       "reference": "Reference", "reference_gaussian": "Reference + Gaussian", "corrected": "Corrected",
       "corrected_gaussian": "Corrected + Gaussian", "nat_reference": "Nat. Reference", "nat_corrected": "Nat. Corrected",
       "nat_selection_uniform": "Nat. uniform sel.", "fail0p0_reference": "Reference f=0.0", "fail0p3_reference": "Reference f=0.3",
       "fail0p3_corrected": "Corrected f=0.3", "ctl_selection_uniform": "ctl: uniform selection",
       "ctl_selection_coverage": "ctl: coverage selection", "ctl_imputation_none": "ctl: no imputation",
       "ctl_imputation_cap010": "ctl: surrogate cap 0.10", "ctl_imputation_postfilter": "ctl: real-only filter + post-filter",
       "ctl_delivery_coupled": "ctl: packet-coupled delivery", "ctl_momentum0_lr0p5": "ctl: momentum 0, lr 0.5",
       "ctl_momentum0_lr5p0": "ctl: momentum 0, lr 5.0", "ctl_weighting_uniform": "ctl: uniform weights"}
MAIN = ["clean_centralized", "clean_fedavg", "scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation",
        "reference", "corrected", "reference_gaussian", "corrected_gaussian"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 9.5, "axes.labelsize": 9,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                     "legend.frameon": False, "legend.fontsize": 7.5, "figure.dpi": 100, "svg.fonttype": "none", "pdf.fonttype": 42})


def save(fig, h: Path, name: str, data: pd.DataFrame, caption: str):
    for ext in ("pdf", "svg", "png"):
        d = h / "figures" / ext.upper()
        d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d / f"{name}.{ext}", dpi=300 if ext == "png" else None, bbox_inches="tight")
    (h / "figures" / "data").mkdir(parents=True, exist_ok=True)
    data.to_csv(h / "figures" / "data" / f"{name}.csv", index=False)
    (h / "figures" / "data" / f"{name}.caption.txt").write_text(caption, encoding="utf-8")
    plt.close(fig)
    print("wrote", name)


def strip(ax, df, arms, col, y_label=None, horizontal=True):
    for i, a in enumerate(arms):
        v = df[df.arm == a][col].to_numpy(float)
        x = np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v))
        ax.scatter(v if horizontal else x, x if horizontal else v, s=14, color=OI["blue"], alpha=0.8, zorder=3, edgecolor="white", linewidth=0.3)
        m, sd = v.mean(), v.std(ddof=1)
        if horizontal:
            ax.errorbar(m, i, xerr=sd, color="black", capsize=2.5, lw=1.1, zorder=4, marker="D", ms=3)
        else:
            ax.errorbar(i, m, yerr=sd, color="black", capsize=2.5, lw=1.1, zorder=4, marker="D", ms=3)
    if horizontal:
        ax.set_yticks(range(len(arms))); ax.set_yticklabels([LAB.get(a, a) for a in arms]); ax.invert_yaxis()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True)
    h = Path(ap.parse_args().handoff)
    T = h / "tables"
    runs = pd.read_csv(T / "all_runs.csv")
    rnd = pd.read_csv(T / "round_metrics.csv")
    net = pd.read_csv(T / "network_metrics.csv")
    sel = pd.read_csv(T / "client_selection.csv")
    pc = pd.read_csv(T / "paired_comparisons.csv")
    notes = []

    # ---- Fig 1: AUC ----
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    rows = []
    for ax, ds in zip(axs, DS):
        d = runs[runs.dataset == ds]
        strip(ax, d, MAIN, "best_auc")
        ax.set_title(DS[ds]); ax.set_xlabel("ROC-AUC, report partition, best checkpoint (n=5 seeds)")
        rows.append(d[d.arm.isin(MAIN)][["dataset", "arm", "seed", "best_auc", "last_auc"]])
        lo = d[d.arm.isin(MAIN)].best_auc.min()
        ax.set_xlim(0.70 if lo < 0.9 else 0.97, 1.0)
        ax.set_xlabel(ax.get_xlabel() + ("\n(x-axis starts at 0.70)" if lo < 0.9 else "\n(x-axis starts at 0.97 - zoomed)"))
    axs[1].set_yticklabels([])
    save(fig, h, "fig01_auc_comparison", pd.concat(rows), "Report-partition ROC-AUC at the best (selection-partition) checkpoint. Dots = individual seeds (12-16), diamond = mean, bars = +/-1 sample SD. Note the different x-axis ranges: UNSW is zoomed from 0.70, CIC from 0.97; CIC differences between the protected methods are <0.001 AUC.")

    # ---- Fig 2: F1, recall, FPR ----
    fig, axs = plt.subplots(2, 3, figsize=(9, 5.2), sharey="row")
    rows = []
    for r_i, ds in enumerate(DS):
        d = runs[runs.dataset == ds]
        for c_i, (col, nm) in enumerate([("best_f1", "F1"), ("best_recall_adr", "recall_adr"), ("best_fpr", "FPR")]):
            ax = axs[r_i, c_i]; strip(ax, d, MAIN, col)
            ax.set_xlabel(nm); ax.set_title(f"{DS[ds]} - {nm}")
            if c_i: ax.set_yticklabels([])
        rows.append(d[d.arm.isin(MAIN)][["dataset", "arm", "seed", "best_f1", "best_recall_adr", "best_fpr", "best_precision"]])
    save(fig, h, "fig02_f1_recall_fpr", pd.concat(rows), "F1, recall_adr and FPR on the report partition at the threshold chosen on a separate calibration partition (best checkpoint). Dots = seeds, diamond = mean +/- SD. FPR is ~0.14-0.15 for nearly all arms because the threshold rule targets a similar operating point; it is not an independent quality measure.")

    # ---- Fig 3: paired reference vs corrected ----
    fig, axs = plt.subplots(2, 2, figsize=(7, 5.4))
    rows = []
    for r_i, ds in enumerate(DS):
        for c_i, (col, nm) in enumerate([("best_auc", "best checkpoint"), ("last_auc", "last round (30)")]):
            ax = axs[r_i, c_i]
            A = runs[(runs.dataset == ds) & (runs.arm == "reference")].set_index("seed")[col]
            B = runs[(runs.dataset == ds) & (runs.arm == "corrected")].set_index("seed")[col]
            for s in A.index:
                ax.plot([0, 1], [A[s], B[s]], marker="o", color=OI["grey"], alpha=0.8, lw=1)
                ax.annotate(str(s), (1.03, B[s]), fontsize=6.5, va="center")
            ax.plot([0, 1], [A.mean(), B.mean()], color="black", lw=2.2, marker="D")
            ax.set_xticks([0, 1]); ax.set_xticklabels(["Reference", "Corrected"]); ax.set_xlim(-0.2, 1.25)
            ax.set_title(f"{DS[ds]} - AUC, {nm}"); ax.set_ylabel("ROC-AUC (report partition)")
            rows += [{"dataset": ds, "metric": col, "seed": s, "reference": A[s], "corrected": B[s], "diff": B[s] - A[s]} for s in A.index]
    save(fig, h, "fig03_paired_reference_vs_corrected", pd.DataFrame(rows), "Paired per-seed ROC-AUC, Reference vs Corrected (same seed = same data partition and training seed; attacker/selection schedules differ by design). Grey = seeds 12-16, black = mean. Corrected is lower in 5/5 seeds on UNSW (exact Wilcoxon p=0.0625, the smallest attainable at n=5) and in 4/5 on CIC best-checkpoint.")

    # ---- Fig 4: loss curves ----
    fig, axs = plt.subplots(1, 2, figsize=(8, 3.6), sharey=True)
    reps = [("reference", OI["blue"]), ("corrected", OI["verm"]), ("fail0p3_corrected", OI["pink"]), ("reference_gaussian", OI["green"]), ("scenario_fedavg_topk", OI["black"])]
    rows = []
    for ax, ds in zip(axs, DS):
        for a, col in reps:
            g = rnd[(rnd.dataset == ds) & (rnd.arm == a) & (rnd["round"] >= 1)].groupby("round").mean_train_loss
            mean, lo, hi = g.mean(), g.min(), g.max()
            ax.plot(mean.index, mean.values, color=col, label=LAB[a], lw=1.5)
            ax.fill_between(mean.index, lo.values, hi.values, color=col, alpha=0.15, linewidth=0)
            rows.append(pd.DataFrame({"dataset": ds, "arm": a, "round": mean.index, "mean_loss": mean.values, "min_loss": lo.values, "max_loss": hi.values}))
        ax.set_yscale("log"); ax.set_xlabel("Federated round"); ax.set_title(DS[ds])
    axs[0].set_ylabel("Mean local training loss (log scale)"); axs[0].legend(loc="upper left")
    save(fig, h, "fig04_training_loss_curves", pd.concat(rows), "Mean client training loss per round (log y-axis), mean over 5 seeds with min-max band. Loss is a training-side quantity, not an evaluation metric. Undefended FedAvg (black) diverges by orders of magnitude; Corrected under 30% failure shows spikes in individual seeds.")

    # ---- Fig 5: best vs last ----
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.6))
    grp = {"baseline": OI["black"], "main": OI["blue"], "control": OI["sky"], "natural_assignment": OI["orange"], "failure_sensitivity": OI["verm"]}
    arms = pd.read_csv(T / "arm_definitions.csv").set_index("arm")["group"].to_dict()
    runs["group"] = runs.arm.map(arms)
    for ax, ds in zip(axs, DS):
        d = runs[runs.dataset == ds]
        for g, c in grp.items():
            x = d[d.group == g]; ax.scatter(x.best_auc, x.last_auc, s=11, color=c, alpha=0.75, label=g, edgecolor="none")
        ax.plot([0.2, 1], [0.2, 1], color="grey", lw=0.8, ls="--"); ax.set_xlim(0.45, 1.005); ax.set_ylim(0.45, 1.005)
        ax.set_xlabel("AUC at best checkpoint"); ax.set_ylabel("AUC at last round"); ax.set_title(f"{DS[ds]} (120 runs, axes start at 0.45)")
    axs[0].legend(loc="lower right", ncol=1)
    save(fig, h, "fig05_best_vs_last_auc", runs[["dataset", "arm", "group", "seed", "best_auc", "last_auc", "auc_drop_best_minus_last", "diverged_loss_gt100"]], "Each point is one run: report-partition AUC at the selected best checkpoint (x) vs the last round (y). Points below the diagonal lose performance after the best round; clusters near AUC 0.5 are collapsed (constant-prediction) final models, hidden if only the best checkpoint is reported.")

    # ---- Fig 6: malicious robustness ----
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.6))
    arms6 = ["scenario_fedavg_random", "scenario_fedavg_topk", "robust_random_no_imputation", "reference", "corrected", "clean_fedavg"]
    rows = []
    for ax, (ds, col) in zip(axs[:2], [("unsw", "last_auc"), ("ciciot", "last_auc")]):
        d = runs[runs.dataset == ds]; strip(ax, d, arms6, col); ax.set_title(f"{DS[ds]} - last-round AUC"); ax.set_xlabel("ROC-AUC (report partition)")
        rows.append(d[d.arm.isin(arms6)][["dataset", "arm", "seed", "best_auc", "last_auc"]])
    ax = axs[2]
    t = runs[runs.arm.isin(arms6[:5])].groupby(["arm"])[["malicious_received_total", "malicious_accepted_total"]].sum() / 10
    t = t.loc[arms6[:5]]
    ax.barh(range(5), t.malicious_received_total, color=OI["sky"], label="received by server"); ax.barh(range(5), t.malicious_accepted_total, color=OI["verm"], label="accepted into aggregate")
    ax.set_yticks(range(5)); ax.set_yticklabels([LAB[a] for a in arms6[:5]]); ax.invert_yaxis(); ax.legend(loc="lower right")
    ax.set_xlabel("Malicious updates per run (mean of 10 runs, both datasets)")
    rows.append(t.reset_index())
    save(fig, h, "fig06_malicious_robustness", pd.concat(rows), "Left/centre: last-round AUC with and without the distance filter (20% sign-flip attackers). Right: malicious updates received vs accepted, mean over the 10 runs (5 seeds x 2 datasets) of each arm over 30 rounds (max 120 selected per run). Filter blocks ~90% of received malicious updates (Reference) vs 100% accepted for undefended FedAvg.")

    # ---- Fig 7: fairness ----
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    arms7 = ["clean_fedavg", "reference", "ctl_selection_uniform", "ctl_selection_coverage", "corrected"]
    d = runs[runs.dataset == "unsw"]
    strip(axs[0], d, arms7, "selection_gini_recomputed"); axs[0].set_xlabel("Gini of per-client selection counts (0 = equal)"); axs[0].set_title("Selection inequality (UNSW)")
    strip(axs[1], d, arms7, "clients_never_selected"); axs[1].set_xlabel("Clients never selected (of 50)"); axs[1].set_title("Coverage"); axs[1].set_yticklabels([])
    for a, c in zip(arms7[1:], [OI["blue"], OI["green"], OI["orange"], OI["verm"]]):
        x = sel[(sel.dataset == "unsw") & (sel.arm == a)].groupby(["seed", "client_id"]).times_selected.sum().groupby("client_id").mean().sort_values(ascending=False).to_numpy()
        axs[2].plot(range(1, len(x) + 1), x, color=c, label=LAB[a], lw=1.5, ls="--" if a == "ctl_selection_coverage" else "-")
    axs[2].set_xlabel("Client rank by selection count"); axs[2].set_ylabel("Mean times selected (of 30 rounds)"); axs[2].set_title("Selection-frequency distribution"); axs[2].legend()
    save(fig, h, "fig07_selection_fairness", runs[runs.arm.isin(arms7)][["dataset", "arm", "seed", "selection_gini_recomputed", "clients_never_selected", "top5_selection_share", "malicious_selected_total"]], "Client-selection fairness (UNSW; selection is determined by the routing/selection policy and is dataset-independent given the seed). Deterministic top-k (Reference) is the least equal (Gini 0.73); coverage-aware selection (Corrected) reduces it to 0.49; uniform random selection to 0.21. The coverage-aware control and Corrected use the same selection policy, so their curves coincide (dashed line hidden under Corrected). Malicious exposure per policy is in the exported CSV.")

    # ---- Fig 8: network ----
    n8 = ["clean_fedavg", "ctl_selection_uniform", "reference", "ctl_selection_coverage", "ctl_delivery_coupled", "corrected"]
    nu = net[net.dataset == "unsw"]
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, (col, nm) in zip(axs, [("pdr_mean", "Mean packet delivery ratio (selected clients)"), ("update_delivered_rate", "Update delivered rate"), ("delay_ms_mean", "Mean end-to-end delay (ms)")]):
        strip(ax, nu, n8, col); ax.set_xlabel(nm)
    axs[1].set_yticklabels([]); axs[2].set_yticklabels([])
    save(fig, h, "fig08_network_reliability", nu[nu.arm.isin(n8)], "Network simulation outputs for selected (participating) clients, UNSW runs. The network trace depends only on the seed and policy, not on the dataset: UNSW and CIC values are identical (max abs difference 0.0), so CIC gives no independent network evidence. Packet-coupled delivery (Corrected) lowers the update delivery rate; Corrected also has ~3.5x higher mean delay because it uses a different delivery/selection configuration (exact cause not isolated).")

    # ---- Fig 9: surrogate / retained real updates ----
    n9 = ["reference", "ctl_imputation_none", "ctl_imputation_cap010", "ctl_imputation_postfilter", "ctl_delivery_coupled", "corrected", "fail0p3_reference", "fail0p3_corrected"]
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.6))
    d = runs[runs.dataset == "unsw"]
    strip(axs[0], d, n9, "real_kept_per_round_mean"); axs[0].set_xlabel("Real updates kept per round"); axs[0].set_title("Retained real updates (UNSW)")
    strip(axs[1], d, n9, "surrogate_weight_share_mean"); axs[1].set_xlabel("Mean surrogate weight share"); axs[1].set_yticklabels([]); axs[1].set_title("Surrogate share of aggregate")
    strip(axs[2], d, n9, "malicious_accepted_total"); axs[2].set_xlabel("Malicious updates accepted per run"); axs[2].set_yticklabels([]); axs[2].set_title("Accepted malicious")
    save(fig, h, "fig09_surrogates_and_retained_updates", d[d.arm.isin(n9)][["arm", "seed", "real_kept_per_round_mean", "surrogate_weight_share_mean", "malicious_accepted_total", "rounds_le1_real_kept", "best_auc", "last_auc"]], "Aggregation diagnostics, UNSW, 5 seeds. Corrected retains fewer real updates per round (4.6 vs 5.9) and has a smaller surrogate share (0.10 vs 0.22) than Reference. Accepted-malicious counts are small (about 4-12 per run) and their seed variance is large; their differences are not statistically distinguishable at n=5.")

    # ---- Fig 10: Gaussian ----
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.6))
    pairs = [("reference", "reference_gaussian"), ("corrected", "corrected_gaussian")]
    rows = []
    for ax, ds in zip(axs, DS):
        d = runs[runs.dataset == ds]
        for i, (a, b) in enumerate(pairs):
            for j, arm in enumerate((a, b)):
                v = d[d.arm == arm].best_auc.to_numpy()
                xx = i * 3 + j
                ax.scatter(np.full(5, xx) + np.linspace(-.12, .12, 5), v, s=14, color=[OI["blue"], OI["orange"]][j], zorder=3)
                ax.errorbar(xx, v.mean(), yerr=v.std(ddof=1), color="black", capsize=3, marker="D", ms=3)
        ax.set_xticks([0, 1, 3, 4]); ax.set_xticklabels(["Reference", "+Gaussian", "Corrected", "+Gaussian"], rotation=15)
        ax.set_title(DS[ds]); ax.set_ylabel("ROC-AUC (report partition, best ckpt)")
        rows.append(d[d.arm.isin(sum(pairs, ()))][["dataset", "arm", "seed", "best_auc", "last_auc", "best_recall_adr", "best_f1", "privacy_epsilon_final_diagnostic", "privacy_noise_std"]])
    save(fig, h, "fig10_gaussian_tradeoff", pd.concat(rows), "Accuracy cost of the Gaussian perturbation. The epsilon recorded for these runs (~10.0 after 30 rounds) is only a diagnostic RDP estimate under assumptions (e.g. Poisson subsampling) that the deterministic top-k / coverage-aware selection does NOT satisfy; it is not a certified differential-privacy guarantee. AUC drops by 0.042 (UNSW) and 0.003 (CIC) for Reference.")

    # ---- Fig 11: failure sensitivity ----
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    n11 = ["fail0p0_reference", "reference", "fail0p3_reference", "corrected", "fail0p3_corrected"]
    n11lab = {"fail0p0_reference": "Ref f=0.0", "reference": "Ref default", "fail0p3_reference": "Ref f=0.3", "corrected": "Corr. default", "fail0p3_corrected": "Corr. f=0.3"}
    rows = []
    for ax, (ds, col, nm) in zip(axs[:2], [("unsw", "last_auc", "UNSW last-round AUC"), ("ciciot", "last_auc", "CIC last-round AUC")]):
        d = runs[runs.dataset == ds]; strip(ax, d, n11, col); ax.set_yticklabels([n11lab[a] for a in n11]); ax.set_xlabel(nm)
        rows.append(d[d.arm.isin(n11)][["dataset", "arm", "seed", "best_auc", "last_auc", "train_loss_max"]])
    ax = axs[2]
    for i, a in enumerate(n11):
        v = runs[(runs.arm == a)].train_loss_max.to_numpy(float)
        ax.scatter(v, np.full(len(v), i) + np.linspace(-.2, .2, len(v)), s=10, color=OI["blue"], alpha=.8)
    ax.set_xscale("log"); ax.set_yticks(range(5)); ax.set_yticklabels([n11lab[a] for a in n11]); ax.invert_yaxis(); ax.set_xlabel("Max training loss over run (log scale; 10 runs/arm)")
    save(fig, h, "fig11_failure_sensitivity_stability", pd.concat(rows), "Sensitivity to the explicit client-failure probability (default vs 0.0 vs 0.3) and numerical stability. Reference is insensitive to failures; Corrected at f=0.3 has seeds with strongly degraded last-round AUC and loss spikes (log x-axis, right). Note failure-sensitivity arms use the same data partitions per seed, but network/failure draws differ.")

    # ---- Fig 12: ablations ----
    ctl = [a for a in LAB if a.startswith("ctl_")] + ["corrected"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    rows = []
    for ax, ds in zip(axs, DS):
        x = pc[(pc.dataset == ds) & (pc["arm_a(baseline)"] == "reference") & (pc.arm_b.isin(ctl)) & (pc.metric == "best_auc")].set_index("arm_b").loc[ctl]
        y = pc[(pc.dataset == ds) & (pc["arm_a(baseline)"] == "reference") & (pc.arm_b.isin(ctl)) & (pc.metric == "last_auc")].set_index("arm_b").loc[ctl]
        yy = np.arange(len(ctl))
        ax.errorbar(x.mean_diff_b_minus_a, yy - 0.12, xerr=[x.mean_diff_b_minus_a - x.ci95_low_t, x.ci95_high_t - x.mean_diff_b_minus_a], fmt="o", color=OI["blue"], capsize=2.5, label="best ckpt")
        ax.errorbar(y.mean_diff_b_minus_a, yy + 0.12, xerr=[y.mean_diff_b_minus_a - y.ci95_low_t, y.ci95_high_t - y.mean_diff_b_minus_a], fmt="s", color=OI["verm"], capsize=2.5, label="last round")
        ax.axvline(0, color="black", lw=0.8); ax.set_yticks(yy); ax.set_yticklabels([LAB[a] for a in ctl]); ax.invert_yaxis()
        ax.set_title(DS[ds])
        if ds == "ciciot": ax.set_xlim(-0.03, 0.01)
        for lab, t in (("best", x), ("last", y)):
            rows.append(t.reset_index().assign(kind=lab)[["dataset", "arm_b", "kind", "mean_diff_b_minus_a", "ci95_low_t", "ci95_high_t", "b_better_seeds", "a_better_seeds", "p_wilcoxon_exact"]])
    axs[0].legend(loc="lower left")
    fig.supxlabel("Paired AUC difference vs Reference (variant - Reference): mean and 95% t-interval, n=5 seeds", fontsize=9)
    save(fig, h, "fig12_ablations_vs_reference", pd.concat(rows), "Single-factor controls (ctl_*) and the full Corrected bundle, each paired against Reference on the same seeds. Intervals are exploratory 95% t-intervals with n=5 (very low power; wide intervals are not evidence of equivalence). ctl_momentum0_lr5p0 on CIC has a very large last-round interval (x-axis clipped at -0.03). No single factor reproduces the Corrected drop, so the Corrected deficit cannot be attributed to one mechanism.")

    notes.append("Figures not generated: per-client selection-frequency by malicious flag, retransmission counts and per-hop routing cost - not recorded per client in the exported tables (retransmission_rounds_mean is exported in network_metrics.csv: it is 0 for all arms except those with packet-coupled delivery/ARQ (Corrected family, ctl_delivery_coupled: ~1.8 rounds per event); no routing-cost measurements other than delay/PDR/route_score exist).")
    (h / "figures" / "FIGURES_NOT_GENERATED.txt").write_text("\n".join(notes), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
