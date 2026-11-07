"""ablation_figure.png (400 dpi), ablation_figure_source_data.csv and ablation_table.tex from the CSVs only."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results_ablation_controlled_v2"
C = pd.read_csv(OUT / "ablation_paired_comparisons.csv")
P = pd.read_csv(OUT / "ablation_per_seed.csv")
S = pd.read_csv(OUT / "ablation_summary.csv")

ROWS = [  # (variant, reference, label)
    ("ctl_imputation_none", "reference", "No recovery"),
    ("ctl_momentum0_lr0p5", "reference", "No server momentum"),
    ("ctl_weighting_uniform", "reference", "Uniform weighting"),
    ("ctl_imputation_postfilter", "reference", "Real-only filtering"),
    ("ctl_imputation_cap010", "reference", "Surrogate cap (0.10)"),
    ("ctl_selection_coverage", "reference", "Coverage-aware selection"),
    ("ctl_selection_uniform", "reference", "Uniform selection"),
    ("ctl_delivery_coupled", "reference", "Packet-coupled delivery"),
    ("abl_no_filter", "abl_reference_repro", "No robust filtering"),
    ("abl_privacy_clip_only", "abl_reference_repro", "Clip + weight cap (no noise)"),
    ("abl_reference_gaussian_repro", "abl_privacy_clip_only", "+ Gaussian noise (vs clip-only)"),
]
DSN = {"ciciot": "CICIoT2023", "unsw": "UNSW-NB15"}
COL = {"best": "#0072B2", "final": "#D55E00"}
plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans", "axes.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "xtick.major.width": 0.6, "ytick.major.width": 0.6})


def get(v, r, ds, m):
    q = C[(C.variant == v) & (C.reference == r) & (C.dataset == ds) & (C.metric == m)]
    return q.iloc[0] if len(q) else None


src = []
fig = plt.figure(figsize=(7.2, 6.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], hspace=0.42, wspace=0.12)
axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
for k, ds in enumerate(["ciciot", "unsw"]):
    ax = axes[k]
    ax.axvline(0, color="#666", lw=0.6)
    for i, (v, r, lab) in enumerate(ROWS):
        y = len(ROWS) - 1 - i
        for m, off, mk, kind in (("auc_best", 0.17, "o", "best"), ("auc_final", -0.17, "D", "final")):
            row = get(v, r, ds, m)
            if row is None:
                continue
            a = P[(P.dataset == ds) & (P.arm == r)].set_index("seed")[m]
            b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")[m]
            d = (b - a).dropna()
            ax.scatter(d.values, np.full(len(d), y + off), s=5, color=COL[kind], alpha=0.35, lw=0, zorder=2)
            ax.errorbar(row.mean_diff, y + off, xerr=[[row.mean_diff - row.ci95_lo], [row.ci95_hi - row.mean_diff]],
                        fmt=mk, ms=3.6, color=COL[kind], ecolor=COL[kind], elinewidth=0.9, capsize=1.6, zorder=3,
                        label=("Best checkpoint" if kind == "best" else "Final round") if i == 0 else None)
            src.append(dict(panel="ab", dataset=ds, variant=v, reference=r, metric=m, mean_diff=row.mean_diff,
                            ci95_lo=row.ci95_lo, ci95_hi=row.ci95_hi, n_seeds=row.n_seeds))
    ax.set_yticks(range(len(ROWS)))
    ax.set_yticklabels([x[2] for x in ROWS][::-1] if k == 0 else [], fontsize=6.5)
    ax.set_xscale("symlog", linthresh=0.01, linscale=0.8)
    ax.set_xlim(-0.9, 0.03)
    ax.set_xticks([-0.5, -0.1, -0.01, 0, 0.01])
    ax.set_xticklabels(["-.5", "-.1", "-.01", "0", ".01"])
    ax.set_xlabel("Paired difference in ROC-AUC (variant - reference)")
    ax.set_title(f"({'ab'[k]}) {DSN[ds]}", loc="left", fontsize=7.5, fontweight="bold")
    ax.grid(axis="x", color="#ddd", lw=0.4)
    ax.set_ylim(-0.6, len(ROWS) - 0.4)
axes[0].legend(frameon=False, fontsize=6.3, loc="lower left")

# (c) delivery reliability and (d) real updates retained after filtering, per selected variant
VAR = [("reference", "Reference"), ("ctl_delivery_coupled", "Packet-\ncoupled"), ("ctl_selection_uniform", "Uniform\nsel."),
       ("ctl_selection_coverage", "Coverage\nsel."), ("ctl_imputation_none", "No\nrecovery")]
for j, (met, ttl, yl) in enumerate([("complete_update_delivery", "(c) Complete-update delivery rate", "Fraction of selected updates"),
                                      ("real_retained_per_round", "(d) Real updates retained by the filter", "Per round (of 10 selected)")]):
    ax = fig.add_subplot(gs[1, j])
    w = 0.38
    for k, ds in enumerate(["ciciot", "unsw"]):
        for i, (arm, _) in enumerate(VAR):
            x = P[(P.dataset == ds) & (P.arm == arm)][met]
            ax.bar(i + (k - 0.5) * w, x.mean(), w * 0.92, yerr=x.std(ddof=1), capsize=1.5, error_kw=dict(lw=0.7),
                   color=["#0072B2", "#E69F00"][k], hatch=["", "///"][k], edgecolor="white", lw=0.3,
                   label=DSN[ds] if i == 0 else None)
            src.append(dict(panel="cd", dataset=ds, variant=arm, metric=met, mean=x.mean(), sd=x.std(ddof=1), n_seeds=len(x)))
    ax.set_xticks(range(len(VAR))); ax.set_xticklabels([v[1] for v in VAR], fontsize=6)
    ax.set_title(ttl, loc="left", fontsize=7.5, fontweight="bold"); ax.set_ylabel(yl)
    ax.grid(axis="y", color="#ddd", lw=0.4); ax.set_axisbelow(True)
    if j == 0:
        ax.legend(frameon=False, fontsize=6.3, loc="upper center", ncol=2); ax.set_ylim(0, 1.15)
fig.savefig(OUT / "ablation_figure.png", dpi=400, bbox_inches="tight")
pd.DataFrame(src).to_csv(OUT / "ablation_figure_source_data.csv", index=False)

# LaTeX table: best-checkpoint ROC-AUC mean +- SD, delta and CI, improved/deteriorated seeds
def f(x, n=3): return f"{x:.{n}f}"
L = [r"\begin{table*}[t]", r"\centering", r"\caption{Component-wise comparison on the validation report partition (5 paired seeds). "
     r"$\Delta$: variant minus reference in best-checkpoint ROC-AUC (mean, 95\% $t$-interval); $\uparrow/\downarrow$: seeds in which the variant "
     r"improved/deteriorated; Final: final-round ROC-AUC difference. Rows marked $^\dagger$ change which clients are selected; the attacker fraction among selected clients is held at 20\% by the exposure-controlled assignment. "
     r"With five seeds the smallest attainable exact two-sided $p$ is 0.0625, so no difference is declared significant.}",
     r"\label{tab:component_analysis}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
     r"\begin{tabular}{l rrrc rrrc}", r"\toprule",
     r" & \multicolumn{4}{c}{CICIoT2023} & \multicolumn{4}{c}{UNSW-NB15} \\",
     r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}",
     r"Variant & $\Delta$AUC & 95\% CI & $\Delta$Final & $\uparrow/\downarrow$ & $\Delta$AUC & 95\% CI & $\Delta$Final & $\uparrow/\downarrow$ \\", r"\midrule"]
for v, r, lab in ROWS:
    mark = r"$^\dagger$" if "selection" in v else ""
    cells = []
    for ds in ["ciciot", "unsw"]:
        a, b = get(v, r, ds, "auc_best"), get(v, r, ds, "auc_final")
        if a is None:
            cells += ["--"] * 4; continue
        cells += [f(a.mean_diff, 4), f"[{f(a.ci95_lo, 4)}, {f(a.ci95_hi, 4)}]", f(b.mean_diff, 4), f"{int(a.n_improved)}/{int(a.n_deteriorated)}"]
    L.append(f"{lab}{mark} & " + " & ".join(cells) + r" \\")
L += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
(OUT / "ablation_table.tex").write_text("\n".join(L) + "\n", encoding="utf-8")
print("figure + table written")
