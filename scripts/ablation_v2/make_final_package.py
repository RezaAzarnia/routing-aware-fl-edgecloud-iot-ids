"""Final manuscript package: checks, Figure A, Figure B, source data, LaTeX table.
Reads only the ablation CSVs and the per-round metrics of the run directories (read-only)."""
import json
from pathlib import Path
import numpy as np, pandas as pd, yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results_ablation_controlled_v2"
OUT = R / "manuscript_final"
OUT.mkdir(exist_ok=True)
P = pd.read_csv(R / "ablation_per_seed.csv")
C = pd.read_csv(R / "ablation_paired_comparisons.csv")
INV = pd.read_csv(R / "ablation_run_inventory.csv")
HV = pd.read_csv(R / "historical_verification.csv")
CD = pd.read_csv(R / "ablation_config_differences.csv")
DSN = {"ciciot": "CICIoT2023", "unsw": "UNSW-NB15"}
SEEDS = [12, 13, 14, 15, 16]
BLUE, ORANGE, GREY = "#0072B2", "#D55E00", "#555555"
plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans", "axes.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white",
                     "savefig.facecolor": "white"})


def runpath(ds, arm, s):
    root = "results_phase6c" if not arm.startswith("abl_") else "results_ablation_controlled_v2/runs"
    return ROOT / root / ds / arm / f"seed_{s}"


# ------------------------------------------------------------------ checks
checks = []


def chk(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


new = INV[INV.status == "newly_executed"]
chk("40 newly executed runs: 4 arms x 2 datasets x seeds 12-16",
    len(new) == 40 and set(new.seed.astype(int)) == set(SEEDS) and new.groupby(["dataset", "arm"]).size().eq(5).all()
    and new.arm.nunique() == 4, f"{len(new)} runs")
chk("no missing/failed run in the inventory", not INV.status.isin(["missing", "failed_or_partial", "failed_analysis"]).any())
chk("130 historical runs verified (13 arms x 2 datasets x 5 seeds)", len(HV) == 130 and (HV.verify_problems == "none").all(), f"{len(HV)} rows")
used_hist = INV[INV.status == "verified_reused"]
chk("historical runs used in the comparisons (110) are a subset of the 130 verified",
    len(used_hist) == 110 and set(used_hist.arm).issubset(set(HV.arm)), f"{len(used_hist)} used")
chk("every (dataset, arm) has exactly seeds 12-16", P.groupby(["dataset", "arm"]).seed.apply(lambda x: sorted(x) == SEEDS).all())
chk("all paired comparisons use 5 seeds matched by seed", all(g.n_seeds.max() == 5 for _, g in C.groupby(["variant", "reference", "dataset"])))
meta_ok = all(json.loads((runpath(ds, arm, s) / "run_metadata.json").read_text()).get("test_data_loaded") is False
              for ds in DSN for arm in P.arm.unique() for s in SEEDS)
chk("test_data_loaded is false in all 150 run_metadata.json files used", meta_ok)
exp = P.groupby("arm").attacker_exposure.agg(["min", "max"])
chk("attacker exposure is 0.20 in every arm (exposure_controlled): no exposure difference is claimed",
    exp["min"].round(6).eq(0.2).all() and exp["max"].round(6).eq(0.2).all(), f"min {exp['min'].min():.4f}, max {exp['max'].max():.4f}")
chk("reference re-run reproduces the historical reference exactly (best/last AUC, F1, FPR)", all(
    abs(C[(C.variant == "abl_reference_repro") & (C.dataset == ds) & (C.metric == m)].mean_diff.iloc[0]) < 1e-12
    and C[(C.variant == "abl_reference_repro") & (C.dataset == ds) & (C.metric == m)].sd_diff.iloc[0] < 1e-12
    for ds in DSN for m in ["auc_best", "auc_final", "f1_best", "fpr_best"]))
chk("selected-checkpoint and last-round metrics are separate columns and differ", not np.allclose(P.auc_best, P.auc_final))
sf = CD[CD.family == "component"].groupby("variant").n_fields.max()
chk("component variants change exactly one config field, except the momentum+learning-rate arm (2 fields)",
    all(sf[v] == 1 for v in sf.index if v != "ctl_momentum0_lr5p0") and sf["ctl_momentum0_lr5p0"] == 2, str(sf.to_dict()))
cp = CD[CD.variant == "abl_privacy_clip_only"].n_fields.iloc[0]
chk("clip-only vs reference changes several fields (pipeline switch, not single factor)", cp > 1, f"{cp} fields")
gn = CD[(CD.variant == "abl_reference_gaussian_repro") & (CD.reference == "abl_privacy_clip_only")].changed_fields.iloc[0]
chk("Gaussian vs clip-only differs only in noise-related fields (mode/clip unchanged)",
    "noise_multiplier" in gn and "privacy.mode" not in gn and "privacy.clip_norm" not in gn, gn)
cfg_ok = True
for ds in DSN:
    for arm in P.arm.unique():
        c = yaml.safe_load((runpath(ds, arm, 12) / "resolved_config.yaml").read_text())
        if (c["attack"].get("assignment") != "exposure_controlled" or c["fl"]["num_clients"] != 50 or c["fl"]["rounds"] != 30
                or c["experiment"]["validation_only"] is not True):
            cfg_ok = False
chk("all arms: 50 clients, 30 rounds, exposure_controlled attackers, validation_only", cfg_ok)
chk("10 Gaussian re-run completion records exist", all((runpath(ds, "abl_reference_gaussian_repro", s) / "ablation_COMPLETE.json").exists() for ds in DSN for s in SEEDS))
ckpt_ok = True
try:
    import torch
    for ds in DSN:
        for s in SEEDS:
            for nm in ("best_model_state.pt", "last_model_state.pt"):
                torch.load(runpath(ds, "abl_reference_gaussian_repro", s) / nm, map_location="cpu", weights_only=False)
except Exception:  # noqa
    ckpt_ok = False
chk("Gaussian re-run checkpoints load without error (their writer, first or second execution, remains ambiguous)", ckpt_ok)
sel0 = P[(P.arm == "abl_no_filter") & (P.best_round == 0)]
chk("INFO: no-filter seeds whose selected checkpoint is round 0 (untrained model)", True, f"{len(sel0)}: " + ", ".join(f"{r.dataset}/seed{r.seed}" for r in sel0.itertuples()))

# ------------------------------------------------------------------ Figure A
ref, nof = "abl_reference_repro", "abl_no_filter"
rowsA, trajA = [], []
for ds in DSN:
    for arm in (ref, nof):
        for s in SEEDS:
            q = P[(P.dataset == ds) & (P.arm == arm) & (P.seed == s)].iloc[0]
            rowsA.append(dict(dataset=ds, arm=arm, seed=s, auc_selected_checkpoint=q.auc_best, auc_last_round=q.auc_final,
                              selected_round=int(q.best_round), max_drawdown_report_auc=q.auc_drawdown,
                              collapse_flag_drawdown_gt_0p05=bool(q.collapse),
                              source=f"ablation_per_seed.csv: dataset={ds}, arm={arm}, seed={s}"))
            rm = pd.read_csv(runpath(ds, arm, s) / "round_metrics.csv")
            for _, x in rm.iterrows():
                trajA.append(dict(dataset=ds, arm=arm, seed=s, round=int(x["round"]), report_partition_roc_auc=x["val_rep_roc_auc"],
                                  source=f"{runpath(ds, arm, s).relative_to(ROOT).as_posix()}/round_metrics.csv"))
A = pd.DataFrame(rowsA)
A["last_minus_selected_auc"] = A.auc_last_round - A.auc_selected_checkpoint
A["last_round_degraded_gt_0p05"] = A.last_minus_selected_auc < -0.05
T = pd.DataFrame(trajA)
A.groupby(["dataset", "arm"]).agg(seeds=("seed", "size"), last_round_degraded_seeds=("last_round_degraded_gt_0p05", "sum"), drawdown_gt_0p05_seeds=("collapse_flag_drawdown_gt_0p05", "sum"), mean_selected_auc=("auc_selected_checkpoint", "mean"), mean_last_auc=("auc_last_round", "mean"), min_last_auc=("auc_last_round", "min")).reset_index().to_csv(OUT / "figure_A_summary_counts.csv", index=False)
A.to_csv(OUT / "figure_A_source_data.csv", index=False)
T.to_csv(OUT / "figure_A_trajectory_source_data.csv", index=False)
fig, axs = plt.subplots(2, 2, figsize=(7.0, 5.7), gridspec_kw=dict(hspace=0.55, wspace=0.28))
POS = {"auc_selected_checkpoint": (0, 1), "auc_last_round": (2.6, 3.6)}
for k, ds in enumerate(DSN):
    ax = axs[0, k]
    a = A[A.dataset == ds]
    for s in SEEDS:
        for m, (xr, xn) in POS.items():
            yr = a[(a.arm == ref) & (a.seed == s)][m].iloc[0]
            yn = a[(a.arm == nof) & (a.seed == s)][m].iloc[0]
            ax.plot([xr, xn], [yr, yn], color="#999999", lw=0.7, zorder=1)
            ax.scatter([xr], [yr], s=14, color=BLUE, zorder=3, edgecolor="white", lw=0.3)
            ax.scatter([xn], [yn], s=14, color=ORANGE, marker="s", zorder=3, edgecolor="white", lw=0.3)
    for m, (xr, xn) in POS.items():
        for arm, x in ((ref, xr), (nof, xn)):
            ax.hlines(a[a.arm == arm][m].mean(), x - 0.22, x + 0.22, color="black", lw=1.4, zorder=4)
    ax.set_xticks([0, 1, 2.6, 3.6])
    ax.set_xticklabels(["Reference", "No robust\nfiltering", "Reference", "No robust\nfiltering"], fontsize=6.3)
    ax.text(0.5, -0.31, "Selected checkpoint", ha="center", transform=ax.get_xaxis_transform(), fontsize=7, fontweight="bold")
    ax.text(3.1, -0.31, "Last round (30)", ha="center", transform=ax.get_xaxis_transform(), fontsize=7, fontweight="bold")
    ax.set_ylim(0.0, 1.02); ax.set_xlim(-0.5, 4.1); ax.set_ylabel("Report-partition ROC-AUC")
    ax.set_title(f"({'ab'[k]}) {DSN[ds]}: paired seeds", loc="left", fontsize=7.5, fontweight="bold")
    ax.grid(axis="y", color="#e2e2e2", lw=0.4); ax.set_axisbelow(True)
    nc = int(a[a.arm == nof].collapse_flag_drawdown_gt_0p05.sum())
    ax.text(3.1, 0.06, f"drawdown > 0.05 in {nc}/5 seeds", ha="center", fontsize=6.3, color=ORANGE)
    ax = axs[1, k]
    t = T[T.dataset == ds]
    for arm, c in ((ref, BLUE), (nof, ORANGE)):
        for s in SEEDS:
            g = t[(t.arm == arm) & (t.seed == s)]
            ax.plot(g["round"], g.report_partition_roc_auc, color=c, lw=0.8, alpha=0.8)
            br = int(a[(a.arm == arm) & (a.seed == s)].selected_round.iloc[0])
            ax.scatter([br], [g[g["round"] == br].report_partition_roc_auc.iloc[0]], s=16, marker="*", color=c,
                       edgecolor="black", lw=0.3, zorder=5)
    ax.set_ylim(0.0, 1.02); ax.set_xlim(-0.5, 30.5)
    ax.set_xlabel("Communication round (0 = initial model)"); ax.set_ylabel("Report-partition ROC-AUC")
    ax.set_title(f"({'cd'[k]}) {DSN[ds]}: per-round trajectories", loc="left", fontsize=7.5, fontweight="bold")
    ax.grid(axis="y", color="#e2e2e2", lw=0.4); ax.set_axisbelow(True)
h = [Line2D([], [], marker="o", color="w", markerfacecolor=BLUE, markersize=4.5, label="Reference (MAD filter), 5 seeds"),
     Line2D([], [], marker="s", color="w", markerfacecolor=ORANGE, markersize=4.5, label="No robust filtering, 5 seeds"),
     Line2D([], [], color="black", lw=1.4, label="Mean over seeds"),
     Line2D([], [], marker="*", color="w", markerfacecolor="white", markeredgecolor="black", markersize=7,
            label="Selected checkpoint (per seed)")]
fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, fontsize=6.5, bbox_to_anchor=(0.5, -0.01))
fig.savefig(OUT / "Fig_A_Robust_Filtering_400dpi.png", dpi=400, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ Figure B and table rows
ROWS = [  # variant, reference, table label, type, group
    ("ctl_imputation_none", "reference", "No recovery (no surrogates)", "S", 0),
    ("ctl_momentum0_lr0p5", "reference", r"No server momentum ($\mu{=}0$, $\eta_s{=}0.5$)", "S", 0),
    ("ctl_weighting_uniform", "reference", "Uniform client weighting", "S", 0),
    ("ctl_imputation_postfilter", "reference", "Real-only filter statistics", "S", 0),
    ("ctl_imputation_cap010", "reference", "Surrogate weight cap 0.10", "S", 0),
    ("ctl_selection_coverage", "reference", "Coverage-aware selection", "S", 0),
    ("ctl_selection_uniform", "reference", "Uniform random selection", "S", 0),
    ("ctl_delivery_coupled", "reference", "Packet-coupled delivery", "S", 0),
    ("abl_no_filter", "abl_reference_repro", "No robust filtering", "S", 1),
    ("abl_privacy_clip_only", "abl_reference_repro", "Clipping + weight cap, no noise", "P", 2),
    ("abl_reference_gaussian_repro", "abl_privacy_clip_only", "Gaussian noise added to clip-only", "S", 2),
    ("abl_reference_gaussian_repro", "abl_reference_repro", "Full pipeline (clip + cap + noise)", "M", 2),
    ("ctl_momentum0_lr5p0", "reference", r"Momentum 0 and $\eta_s{=}5$", "M", 3),
]
GROUPS = {0: "Single-factor changes, historical reference", 1: "Single-factor change, current-code reference",
          2: "Privacy pipeline (current-code runs)"}


def cget(v, r, ds, m):
    q = C[(C.variant == v) & (C.reference == r) & (C.dataset == ds) & (C.metric == m)]
    assert len(q) == 1, (v, r, ds, m)
    return q.iloc[0]


srcB = []
for v, r, lab, typ, grp in ROWS:
    for ds in DSN:
        for m, kind in (("auc_best", "selected_checkpoint"), ("auc_final", "last_round")):
            c = cget(v, r, ds, m)
            a = P[(P.dataset == ds) & (P.arm == r)].set_index("seed")[m]
            b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")[m]
            d = b - a
            srcB.append(dict(dataset=ds, variant=v, reference=r, label=lab.replace("$", "").replace("\\", ""),
                             comparison_type={"S": "single-factor", "P": "pipeline-level", "M": "multi-factor"}[typ], metric=kind,
                             ref_mean=c.mean_ref, var_mean=c.mean_var, mean_diff=c.mean_diff, sd_diff=c.sd_diff,
                             ci95_lo_t4df=c.ci95_lo, ci95_hi_t4df=c.ci95_hi, n_seeds_variant_lower=int(c.n_var_lower),
                             n_seeds_variant_higher=int(c.n_var_higher), exact_signflip_p=c.exact_signflip_p,
                             collapse_seeds_variant=int(P[(P.dataset == ds) & (P.arm == v)].collapse.sum()),
                             collapse_seeds_reference=int(P[(P.dataset == ds) & (P.arm == r)].collapse.sum()),
                             seed_diffs="; ".join(f"{s}:{d[s]:.6f}" for s in SEEDS),
                             source="ablation_paired_comparisons.csv; ablation_per_seed.csv"))
B = pd.DataFrame(srcB)
B.to_csv(OUT / "figure_B_source_data.csv", index=False)
for _, x in B.iterrows():
    m = "auc_best" if x.metric == "selected_checkpoint" else "auc_final"
    a = P[(P.dataset == x.dataset) & (P.arm == x.reference)].sort_values("seed")[m].to_numpy()
    b = P[(P.dataset == x.dataset) & (P.arm == x.variant)].sort_values("seed")[m].to_numpy()
    assert abs((b - a).mean() - x.mean_diff) < 1e-12 and abs((b - a).std(ddof=1) - x.sd_diff) < 1e-12
chk("Figure B / table values recomputed from ablation_per_seed.csv equal ablation_paired_comparisons.csv", True, f"{len(B)} rows")

figrows = [r for r in ROWS if r[0] != "ctl_momentum0_lr5p0"]
FIGLAB = {("abl_privacy_clip_only", "abl_reference_repro"): "Clip + weight cap, no noise\n[pipeline switch vs. reference]",
          ("abl_reference_gaussian_repro", "abl_privacy_clip_only"): "Gaussian noise added\n[single factor vs. clip-only]",
          ("abl_reference_gaussian_repro", "abl_reference_repro"): "Clip + cap + noise\n[multi-factor vs. reference]",
          ("ctl_momentum0_lr0p5", "reference"): "No server momentum\n(mu = 0, server lr 0.5)"}
fig, axs = plt.subplots(1, 2, figsize=(7.0, 5.6), sharey=True, gridspec_kw=dict(wspace=0.06))
ypos, yl, glist, y = {}, [], [], 0.0
for g in (0, 1, 2):
    glist.append((g, y)); y += 1
    for r in figrows:
        if r[4] == g:
            ypos[(r[0], r[1])] = y; yl.append((y, r)); y += 1
    y += 0.4
ymax = y
for k, ds in enumerate(DSN):
    ax = axs[k]
    ax.axvline(0, color=GREY, lw=0.6)
    for (v, r_, lab, typ, grp) in figrows:
        yy = ypos[(v, r_)]
        for m, off, mk, col in (("auc_best", -0.17, "o", BLUE), ("auc_final", 0.17, "D", ORANGE)):
            c = cget(v, r_, ds, m)
            a = P[(P.dataset == ds) & (P.arm == r_)].set_index("seed")[m]
            b = P[(P.dataset == ds) & (P.arm == v)].set_index("seed")[m]
            d = (b - a).to_numpy()
            ax.scatter(d, np.full(len(d), yy + off), s=6, color=col, alpha=0.4, lw=0, zorder=2)
            ax.errorbar(c.mean_diff, yy + off, xerr=[[c.mean_diff - c.ci95_lo], [c.ci95_hi - c.mean_diff]], fmt=mk, ms=3.5,
                        color=col, ecolor=col, elinewidth=0.9, capsize=1.5, zorder=3, markeredgecolor="white", markeredgewidth=0.3)
    for g, gy in glist:
        ax.axhspan(gy - 0.42, gy + 0.42, color="#efefef", zorder=0)
        ax.text(0.01, gy, GROUPS[g], transform=ax.get_yaxis_transform(), fontsize=6.4, fontweight="bold", va="center", ha="left")
    ax.set_yticks([q[0] for q in yl])
    if k == 0:
        ax.set_yticklabels([FIGLAB.get((r[0], r[1]), r[2]) for _, r in yl], fontsize=6.3)
    else:
        ax.tick_params(labelleft=False)
    ax.set_ylim(ymax - 0.4, -0.6)
    ax.set_xscale("symlog", linthresh=0.01, linscale=0.7)
    ax.set_xlim(-0.9, 0.03)
    ax.set_xticks([-0.5, -0.1, -0.01, 0, 0.01]); ax.set_xticklabels(["-0.5", "-0.1", "-0.01", "0", "0.01"], fontsize=6)
    ax.set_xlabel("Paired ROC-AUC difference (variant - reference)\nsymmetric-log axis, linear within +/-0.01", fontsize=6.6)
    ax.set_title(f"({'ab'[k]}) {DSN[ds]}", loc="left", fontsize=7.5, fontweight="bold")
    ax.grid(axis="x", color="#e2e2e2", lw=0.4); ax.set_axisbelow(True)
h = [Line2D([], [], marker="o", color=BLUE, markersize=4, lw=0.9, label="Selected checkpoint (mean, 95% t-interval)"),
     Line2D([], [], marker="D", color=ORANGE, markersize=4, lw=0.9, label="Last round (mean, 95% t-interval)"),
     Line2D([], [], marker="o", color="#888888", markersize=2.5, lw=0, alpha=0.6, label="Individual seeds (5)")]
fig.legend(handles=h, loc="lower center", ncol=3, frameon=False, fontsize=6.3, bbox_to_anchor=(0.5, -0.045))
fig.savefig(OUT / "Fig_B_Component_Effects_400dpi.png", dpi=400, bbox_inches="tight")
plt.close(fig)


# ------------------------------------------------------------------ LaTeX table
def ms(x, n=4):
    return f"{x:+.{n}f}".replace("-", "$-$")


def refrow(name, arm):
    cells = []
    for ds in DSN:
        g = P[(P.dataset == ds) & (P.arm == arm)]
        cells += [f"{g.auc_best.mean():.4f} ({g.auc_best.std(ddof=1):.4f})", f"{g.auc_final.mean():.4f} ({g.auc_final.std(ddof=1):.4f})",
                  f"{int(g.collapse.sum())}/5 dd"]
    return f"\\textit{{{name}}} & ref. & " + " & ".join(cells) + r" \\"


def varrow(v, r, lab, typ):
    cells = []
    for ds in DSN:
        cb, cl = cget(v, r, ds, "auc_best"), cget(v, r, ds, "auc_final")
        cells += [f"{ms(cb.mean_diff)} ({cb.sd_diff:.4f})", f"{ms(cl.mean_diff)} ({cl.sd_diff:.4f})",
                  f"{int(cb.n_var_lower)}/{int(cl.n_var_lower)} lower"]
    return f"{lab} & {typ} & " + " & ".join(cells) + r" \\"


L = [r"\begin{table*}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3.2pt}",
     r"\caption{Component-wise comparison of ROC-AUC on the report partition (five paired seeds, 12--16). Reference rows: mean (SD) of the selected-checkpoint and last-round ROC-AUC, and the number of seeds (dd) whose per-round report-partition AUC drops by more than 0.05 below its running maximum at some round (maximum drawdown). Variant rows: mean (SD) of the paired difference (variant $-$ reference), and the number of seeds in which the variant is lower at the selected checkpoint / in the last round. Type: S, one configuration field changed; P, pipeline-level switch (several fields change together); M, multi-factor variant. The attacker fraction among selected clients is 20\% in every arm. With five seeds the smallest attainable two-sided exact $p$ is 0.0625; differences are descriptive, and a small difference is not evidence of equivalence.}",
     r"\label{tab:component_analysis}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{@{}llccc ccc@{}}", r"\toprule",
     r" & & \multicolumn{3}{c}{CICIoT2023} & \multicolumn{3}{c}{UNSW-NB15} \\", r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}",
     r"Configuration & Type & Selected ckpt. & Last round & Seeds & Selected ckpt. & Last round & Seeds \\", r"\midrule"]
L.append(refrow("Reference (historical runs)", "reference"))
for v, r, lab, typ, grp in ROWS:
    if grp == 0:
        L.append(varrow(v, r, lab, typ))
L.append(r"\midrule")
L.append(refrow("Reference (current-code re-run)", "abl_reference_repro"))
L.append(varrow("abl_no_filter", "abl_reference_repro", "No robust filtering", "S"))
L.append(varrow("abl_privacy_clip_only", "abl_reference_repro", "Clipping + weight cap, no noise", "P"))
L.append(varrow("abl_reference_gaussian_repro", "abl_reference_repro", "Full pipeline (clip + cap + noise)", "M"))
L.append(r"\midrule")
L.append(refrow("Clipping + weight cap, no noise", "abl_privacy_clip_only"))
L.append(varrow("abl_reference_gaussian_repro", "abl_privacy_clip_only", "Gaussian noise added", "S"))
L.append(r"\midrule")
L.append(r"\textit{Multi-factor variant relative to the historical reference} & & & & & & & \\")
L.append(varrow("ctl_momentum0_lr5p0", "reference", r"Momentum 0 and $\eta_s{=}5$", "M"))
L += [r"\bottomrule", r"\end{tabular}}", r"\end{table*}"]
(OUT / "ablation_final_table.tex").write_text("\n".join(L) + "\n", encoding="utf-8")

md = ["# Automated checks (generated by make_final_package.py)", "", "| Check | Result | Detail |", "|---|---|---|"]
for n, ok, d in checks:
    md.append(f"| {n} | {'PASS' if ok else '**FAIL**'} | {str(d)[:170]} |")
(OUT / "_checks_auto.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(sum(ok for _, ok, _ in checks), "/", len(checks), "checks pass")
for n, ok, d in checks:
    if not ok:
        print("FAIL:", n, d)
