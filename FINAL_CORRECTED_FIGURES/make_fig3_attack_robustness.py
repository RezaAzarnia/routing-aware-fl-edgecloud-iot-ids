"""Figure 3 (manuscript) - static-attack robustness, regenerated from the locked per-seed evidence.

Source of every plotted value: Supplementary_Experiments_Package/SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv
(the same file and the same arm/condition mapping used by scripts/supp_final/figures_final.py, panel "F1").
No value is recomputed, filtered or smoothed; the script only changes presentation:
  * legend moved outside the panels, new method labels, marker shape + colour per method;
  * fixed y-limits: selected checkpoint 0.50-1.00, last round 0.20-1.00 (asserted to contain every point);
  * an explicit statement that these are non-adaptive attacks on the NON-PRIVATE reference pipeline.
The script also re-checks every plotted value against the previously published
figures/FIG1_attack_robustness_data.csv and aborts on any difference.

usage (from the repository root):
    python FINAL_CORRECTED_FIGURES/make_fig3_attack_robustness.py
outputs (in FINAL_CORRECTED_FIGURES/): fig3.pdf, fig3.png, fig3_data.csv
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PKG = ROOT / "Supplementary_Experiments_Package"
PER_SEED = PKG / "SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv"
PUBLISHED = PKG / "figures" / "FIG1_attack_robustness_data.csv"

DS = {"unsw": "UNSW-NB15", "ciciot": "CICIoT2023"}
# (label, arm template); SF 20% is the locked Phase 6C run pair (identical to figures_final.py)
CONDS = [("No attack", "atk_{p}_noatk"), ("SF 10%", "atk_{p}_sf10"), ("SF 20%", None),
         ("SF 30%", "atk_{p}_sf30"), ("BSF 20%", "atk_{p}_bsf20"), ("LF 20%", "atk_{p}_lf20")]
PIPES = [  # key, SF20 arm, legend label, colour, marker, x-offset, published pipeline name
    ("fedavg", "scenario_fedavg_topk", "FedAvg (top-k/routed; no filtering or imputation)", "#D55E00", "o", -0.15,
     "FedAvg (no filter, no recovery)"),
    ("ref", "reference", "Non-private MAD + median imputation (top-k/routed)", "#0072B2", "s", 0.15,
     "MAD filter + surrogate recovery"),
]
METRICS = [("auc_sel", "Selected-checkpoint ROC–AUC", (0.50, 1.00)),
           ("auc_last", "Last-round ROC–AUC", (0.20, 1.00))]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y", "grid.alpha": .28,
    "grid.linewidth": .5, "axes.axisbelow": True, "pdf.fonttype": 42, "ps.fonttype": 42,
})


def main():
    P = pd.read_csv(PER_SEED)
    rows = []
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.6), sharex=True)
    for j, ds in enumerate(DS):
        for i, (metric, ylab, ylim) in enumerate(METRICS):
            ax = axs[i, j]
            for x in range(1, len(CONDS)):
                ax.axvline(x - 0.5, color="#d0d0d0", lw=0.6, zorder=0)
            for key, sf20, label, col, mk, dx, pub_name in PIPES:
                for x, (cond, tmpl) in enumerate(CONDS):
                    arm = sf20 if tmpl is None else tmpl.format(p=key)
                    v = P[(P.dataset == ds) & (P.arm == arm)].sort_values("seed")
                    assert len(v) == 5 and list(v.seed) == [12, 13, 14, 15, 16], (ds, arm, list(v.seed))
                    vals = v[metric].to_numpy(dtype=float)
                    assert ylim[0] <= vals.min() and vals.max() <= ylim[1], (ds, arm, metric, vals)
                    xs = x + dx + np.linspace(-0.06, 0.06, len(vals))
                    ax.scatter(xs, vals, s=17, marker=mk, facecolor=col, edgecolor="white", linewidth=0.35,
                               alpha=0.8, zorder=3, clip_on=False)
                    ax.plot([x + dx - 0.11, x + dx + 0.11], [vals.mean()] * 2, color=col, lw=2.2,
                            solid_capstyle="butt", zorder=4, clip_on=False)
                    rows += [dict(dataset=ds, metric=metric, pipeline=label, published_pipeline_name=pub_name,
                                  condition=cond, arm=arm, seed=int(s), run_id=r, source=src, value=float(y))
                             for s, r, src, y in zip(v.seed, v.run_id, v.source, vals)]
            ax.set_ylim(*ylim)
            ax.set_yticks(np.round(np.arange(ylim[0], ylim[1] + 1e-9, 0.1), 2))
            ax.set_ylabel(ylab if j == 0 else "")
            if i == 0:
                ax.set_title(DS[ds], fontweight="bold")
            ax.set_xlim(-0.55, len(CONDS) - 0.45)
    for ax in axs[1]:
        ax.set_xticks(range(len(CONDS)), [c[0] for c in CONDS], rotation=30, ha="right", rotation_mode="anchor")

    handles = [Line2D([], [], ls="none", marker=mk, ms=6, markerfacecolor=col, markeredgecolor="white", label=label)
               for _, _, label, col, mk, _, _ in PIPES]
    handles.append(Line2D([], [], color="#444444", lw=2.2, label="Mean of 5 seeds (12–16)"))
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.995),
               columnspacing=1.6, handletextpad=0.4)
    fig.text(0.5, 0.005,
             "Non-adaptive attacks on the non-private reference pipeline; not a direct test of the Gaussian-perturbed configuration.\n"
             "SF = sign flip, BSF = norm-preserving sign flip, LF = label flip (exposure-controlled malicious clients). "
             "SF 20% points are the locked Phase 6C runs.",
             ha="center", va="bottom", fontsize=7.6, color="#333333")
    fig.tight_layout(rect=(0, 0.06, 1, 0.925), h_pad=0.8, w_pad=1.2)

    data = pd.DataFrame(rows)
    # ---- integrity check against the previously published figure data (no numerical change allowed)
    pub = pd.read_csv(PUBLISHED)
    pub["key"] = pub[["dataset", "metric", "arm"]].astype(str).agg("|".join, axis=1) + "|" + pub.seed.astype(str)
    new = data.assign(key=data[["dataset", "metric", "arm"]].astype(str).agg("|".join, axis=1) + "|" + data.seed.astype(str))
    m = new.merge(pub[["key", "value", "run_id", "pipeline", "condition"]], on="key", suffixes=("", "_pub"), validate="one_to_one")
    assert len(m) == len(new) == len(pub) == 240, (len(m), len(new), len(pub))
    assert (m.value == m.value_pub).all(), "plotted value differs from published data"
    assert (m.run_id == m.run_id_pub).all() and (m.published_pipeline_name == m.pipeline_pub).all() and (m.condition == m.condition_pub).all()

    data.to_csv(HERE / "fig3_data.csv", index=False)
    fig.savefig(HERE / "fig3.pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(HERE / "fig3.png", dpi=400, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"fig3 written; {len(data)} points verified identical to {PUBLISHED.name}")


if __name__ == "__main__":
    main()
