"""Journal-size ablation figures (6.8 in wide, 400 dpi) from the audited per-seed table and per-round metrics.
Outputs go to results_ablation_controlled_v2/journal_figures/ ; nothing else is written."""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results_ablation_controlled_v2"
OUT = R / "journal_figures"
OUT.mkdir(exist_ok=True)
P = pd.read_csv(R / "ablation_per_seed.csv")
C = pd.read_csv(R / "ablation_paired_comparisons.csv")
DSN = {"ciciot": "CICIoT2023", "unsw": "UNSW-NB15"}
SEEDS = [12, 13, 14, 15, 16]
BLUE, ORANGE, GREY = "#0072B2", "#D55E00", "#555555"
FS = 8
plt.rcParams.update({"font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS, "legend.fontsize": FS,
                     "axes.titlesize": FS, "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                     "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "xtick.major.width": 0.6,
                     "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"})
REF, NOF = "abl_reference_repro", "abl_no_filter"
W = 6.8


def seedval(ds, arm, s, col):
    return float(P[(P.dataset == ds) & (P.arm == arm) & (P.seed == s)][col].iloc[0])


# ------------------------------------------------------------------ Figure A (main)
fig, axs = plt.subplots(1, 2, figsize=(W, 3.0))
fig.subplots_adjust(left=0.085, right=0.995, top=0.85, bottom=0.235, wspace=0.27)
POS = {"auc_best": (0.0, 1.0), "auc_final": (2.7, 3.7)}
counts = {}
for k, ds in enumerate(DSN):
    ax = axs[k]
    gap = 0
    for s in SEEDS:
        for m, (xr, xn) in POS.items():
            yr, yn = seedval(ds, REF, s, m), seedval(ds, NOF, s, m)
            ax.plot([xr, xn], [yr, yn], color="#9a9a9a", lw=0.8, zorder=1)
            ax.scatter([xr], [yr], s=16, color=BLUE, zorder=3, edgecolor="white", lw=0.3)
            ax.scatter([xn], [yn], s=16, color=ORANGE, marker="s", zorder=3, edgecolor="white", lw=0.3)
        if seedval(ds, NOF, s, "auc_best") - seedval(ds, NOF, s, "auc_final") > 0.05:
            gap += 1
    counts[ds] = gap
    for m, (xr, xn) in POS.items():
        for arm, x in ((REF, xr), (NOF, xn)):
            mu = P[(P.dataset == ds) & (P.arm == arm)][m].mean()
            ax.hlines(mu, x - 0.24, x + 0.24, color="black", lw=1.5, zorder=4)
    ax.set_xticks([0, 1, 2.7, 3.7]); ax.set_xticklabels(["Ref.", "No\nfilter", "Ref.", "No\nfilter"])
    ax.text(0.5, -0.30, "Selected checkpoint", ha="center", va="top", transform=ax.get_xaxis_transform(), fontweight="bold")
    ax.text(3.2, -0.30, "Last round (30)", ha="center", va="top", transform=ax.get_xaxis_transform(), fontweight="bold")
    ax.set_xlim(-0.5, 4.2); ax.set_ylim(0.0, 1.03)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel("ROC-AUC (report partition)")
    ax.set_title(f"({'ab'[k]}) {DSN[ds]}", loc="left", fontweight="bold", pad=3)
    ax.grid(axis="y", color="#e4e4e4", lw=0.4); ax.set_axisbelow(True)
    ax.text(4.15, 0.03, f"{gap}/5 seeds\n>0.05 below ckpt.", ha="right", va="bottom", color=ORANGE, fontsize=FS)
h = [Line2D([], [], marker="o", color="w", markerfacecolor=BLUE, markersize=5, label="Reference (MAD filter)"),
     Line2D([], [], marker="s", color="w", markerfacecolor=ORANGE, markersize=5, label="No robust filtering"),
     Line2D([], [], color="#9a9a9a", lw=1, label="Same seed"),
     Line2D([], [], color="black", lw=1.5, label="Mean of 5 seeds")]
fig.legend(handles=h, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.0), columnspacing=1.2, handletextpad=0.4)
fig.savefig(OUT / "Fig_A_Robust_Filtering_Journal.png", dpi=400)
plt.close(fig)

# ------------------------------------------------------------------ Figure A supplementary (trajectories)
fig, axs = plt.subplots(1, 2, figsize=(W, 3.1))
fig.subplots_adjust(left=0.085, right=0.995, top=0.82, bottom=0.17, wspace=0.27)
for k, ds in enumerate(DSN):
    ax = axs[k]
    for arm, c in ((REF, BLUE), (NOF, ORANGE)):
        for s in SEEDS:
            d = ROOT / "results_ablation_controlled_v2/runs" / ds / arm / f"seed_{s}"
            rm = pd.read_csv(d / "round_metrics.csv")
            ax.plot(rm["round"], rm.val_rep_roc_auc, color=c, lw=0.8, alpha=0.85)
            br = int(seedval(ds, arm, s, "best_round"))
            ax.scatter([br], [float(rm[rm["round"] == br].val_rep_roc_auc.iloc[0])], s=22, marker="*", color=c, edgecolor="black", lw=0.35, zorder=5)
    ax.set_xlim(-0.5, 30.5); ax.set_ylim(0, 1.03); ax.set_xlabel("Communication round (0 = initial model)")
    ax.set_ylabel("ROC-AUC (report partition)"); ax.set_title(f"({'ab'[k]}) {DSN[ds]}", loc="left", fontweight="bold", pad=3)
    ax.grid(axis="y", color="#e4e4e4", lw=0.4); ax.set_axisbelow(True)
h = [Line2D([], [], color=BLUE, lw=1.2, label="Reference (5 seeds)"), Line2D([], [], color=ORANGE, lw=1.2, label="No robust filtering (5 seeds)"),
     Line2D([], [], marker="*", color="w", markerfacecolor="white", markeredgecolor="black", markersize=8, label="Selected checkpoint")]
fig.legend(handles=h, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.0), columnspacing=1.2, handletextpad=0.4)
fig.savefig(OUT / "Fig_A_Trajectories_Supplementary.png", dpi=400)
plt.close(fig)

# ------------------------------------------------------------------ Figure B (main)
ROWS = [  # variant, reference, label, filled(single factor)
    ("abl_no_filter", "abl_reference_repro", "No robust filtering", True),
    ("ctl_imputation_none", "reference", "No recovery", True),
    ("ctl_momentum0_lr0p5", "reference", "No momentum (same lr)", True),
    ("ctl_imputation_postfilter", "reference", "Real-only filtering", True),
    ("abl_privacy_clip_only", "abl_reference_repro", "Clip + weight cap", False),
    ("abl_reference_gaussian_repro", "abl_privacy_clip_only", "+ Gaussian noise", True),
    ("abl_reference_gaussian_repro", "abl_reference_repro", "Full privacy pipeline", False),
]


def cget(v, r, ds, m):
    q = C[(C.variant == v) & (C.reference == r) & (C.dataset == ds) & (C.metric == m)]
    assert len(q) == 1
    return q.iloc[0]


fig, axs = plt.subplots(1, 2, figsize=(W, 3.3), sharey=True)
fig.subplots_adjust(left=0.215, right=0.995, top=0.855, bottom=0.165, wspace=0.05)
n = len(ROWS)
for k, ds in enumerate(DSN):
    ax = axs[k]
    ax.axvline(0, color=GREY, lw=0.6)
    for i, (v, r, lab, filled) in enumerate(ROWS):
        y = i
        for m, off, mk, col in (("auc_best", -0.2, "o", BLUE), ("auc_final", 0.2, "D", ORANGE)):
            c = cget(v, r, ds, m)
            a = P[(P.dataset == ds) & (P.arm == r)].set_index("seed")[m]
            b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")[m]
            d = (b - a).to_numpy()
            ax.scatter(d, np.full(len(d), y + off), s=5, color=col, alpha=0.4, lw=0, zorder=2)
            ax.errorbar(c.mean_diff, y + off, xerr=[[c.mean_diff - c.ci95_lo], [c.ci95_hi - c.mean_diff]], fmt=mk, ms=4.2,
                        mfc=col if filled else "white", mec=col, mew=0.9, color=col, ecolor=col, elinewidth=0.9, capsize=1.8, zorder=3)
    ax.set_ylim(n - 0.45, -0.6)
    ax.set_yticks(range(n))
    if k == 0:
        ax.set_yticklabels([r[2] for r in ROWS])
    else:
        ax.tick_params(labelleft=False)
    ax.set_xscale("symlog", linthresh=0.01, linscale=0.7)
    ax.set_xlim(-0.9, 0.03)
    ax.set_xticks([-0.5, -0.1, -0.01, 0, 0.01]); ax.set_xticklabels(["-0.5", "-0.1", "-0.01", "0", "0.01"])
    ax.set_xlabel("Paired ROC-AUC difference")
    ax.set_title(f"({'ab'[k]}) {DSN[ds]}", loc="left", fontweight="bold", pad=3)
    ax.grid(axis="x", color="#e4e4e4", lw=0.4); ax.set_axisbelow(True)
h = [Line2D([], [], marker="o", color=BLUE, markersize=4.5, lw=1, label="Selected checkpoint"),
     Line2D([], [], marker="D", color=ORANGE, markersize=4.5, lw=1, label="Last round"),
     Line2D([], [], marker="o", color="#555555", markerfacecolor="#555555", markersize=4.5, lw=0, label="Single factor"),
     Line2D([], [], marker="o", color="#555555", markerfacecolor="white", markersize=4.5, lw=0, label="Pipeline / multi-factor")]
fig.legend(handles=h, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.6, 1.0), columnspacing=1.0, handletextpad=0.3)
fig.savefig(OUT / "Fig_B_Component_Effects_Journal.png", dpi=400)
plt.close(fig)

# ------------------------------------------------------------------ verification against the audited tables
chk = []
for ds in DSN:
    for arm in (REF, NOF):
        for s in SEEDS:
            d = ROOT / "results_ablation_controlled_v2/runs" / ds / arm / f"seed_{s}"
            fv = json.loads((d / "final_validation_metrics.json").read_text())
            chk.append(abs(fv["report_partition_at_selected_threshold"]["roc_auc"] - seedval(ds, arm, s, "auc_best")) < 1e-12)
            chk.append(abs(fv["last_round_report_partition"]["roc_auc"] - seedval(ds, arm, s, "auc_final")) < 1e-12)
for v, r, lab, filled in ROWS:
    for ds in DSN:
        for m in ("auc_best", "auc_final"):
            c = cget(v, r, ds, m)
            a = P[(P.dataset == ds) & (P.arm == r)].sort_values("seed")[m].to_numpy()
            b = P[(P.dataset == ds) & (P.arm == v)].sort_values("seed")[m].to_numpy()
            chk.append(abs((b - a).mean() - c.mean_diff) < 1e-12)
print("verification:", sum(chk), "/", len(chk), "values agree; gap>0.05 counts:", counts)
