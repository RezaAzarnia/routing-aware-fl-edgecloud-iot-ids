"""Publication figures + underlying data + final weight audit, all derived from SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv / _PAIRED_EFFECTS.csv (run IDs retained in the data files).
usage: python scripts/supp_final/figures_final.py [--pkg Supplementary_Experiments_Package]"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
C = dict(blue="#0072B2", orange="#E69F00", green="#009E73", verm="#D55E00", purple="#CC79A7", sky="#56B4E9", grey="#6b6b6b")
DS = {"unsw": "UNSW-NB15", "ciciot": "CICIoT2023"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25, "grid.linewidth": .5, "figure.dpi": 150,
                     "axes.titlesize": 10, "legend.frameon": False})


def save(fig, pkg, name):
    fig.savefig(pkg / "figures" / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(pkg / "figures" / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def dots(ax, x, vals, color, w=.07):
    ax.scatter(x + np.linspace(-w, w, len(vals)), vals, s=14, color=color, alpha=.55, zorder=3, linewidths=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default="Supplementary_Experiments_Package")
    pkg = ROOT / ap.parse_args().pkg
    (pkg / "figures").mkdir(exist_ok=True)
    P = pd.read_csv(pkg / "SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv")
    E = pd.read_csv(pkg / "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv").drop_duplicates(["family", "dataset", "variant", "reference", "metric"])
    E.to_csv(pkg / "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv", index=False)
    cols = ["dataset", "arm", "seed", "run_id", "source"]

    # ---------------------------------------------------------------- F1 attack robustness
    conds = [("No attack", "atk_{p}_noatk"), ("SF 10%", "atk_{p}_sf10"), ("SF 20%", None), ("SF 30%", "atk_{p}_sf30"), ("BSF 20%", "atk_{p}_bsf20"), ("LF 20%", "atk_{p}_lf20")]
    fig, axs = plt.subplots(2, 2, figsize=(7.4, 5.2), sharex=True)
    rows = []
    for j, ds in enumerate(DS):
        for i, (metric, lab) in enumerate((("auc_sel", "ROC-AUC (selected checkpoint)"), ("auc_last", "ROC-AUC (last round)"))):
            ax = axs[i, j]
            for pipe, col, pname, sf20 in (("fedavg", C["verm"], "FedAvg (no filter, no recovery)", "scenario_fedavg_topk"), ("ref", C["blue"], "MAD filter + surrogate recovery", "reference")):
                for x, (cn, tmpl) in enumerate(conds):
                    arm = sf20 if tmpl is None else tmpl.format(p=pipe)
                    v = P[(P.dataset == ds) & (P.arm == arm)].sort_values("seed")
                    dots(ax, x + (-.12 if pipe == "fedavg" else .12), v[metric].to_numpy(), col)
                    ax.plot([x + (-.12 if pipe == "fedavg" else .12)] * 2, [v[metric].mean()] * 2, marker="_", ms=12, color=col, zorder=4)
                    rows += [dict(dataset=ds, metric=metric, pipeline=pname, condition=cn, arm=arm, seed=s, run_id=r, value=y) for s, r, y in zip(v.seed, v.run_id, v[metric])]
            ax.set_ylabel(lab if j == 0 else "")
            ax.set_title(DS[ds] if i == 0 else "")
    for ax in axs[1]:
        ax.set_xticks(range(len(conds)), [c[0] for c in conds], rotation=30, ha="right")
    axs[0, 0].plot([], [], "s", color=C["verm"], label="FedAvg (no filter, no recovery)")
    axs[0, 0].plot([], [], "s", color=C["blue"], label="MAD filter + surrogate recovery")
    axs[0, 0].legend(loc="lower left", fontsize=7)
    fig.suptitle("Attack robustness (5 seeds; dots = seeds, bars = mean). SF/BSF = sign-flip variants, LF = label flip. Non-adaptive attacks only.", fontsize=8)
    save(fig, pkg, "FIG1_attack_robustness"); pd.DataFrame(rows).to_csv(pkg / "figures" / "FIG1_attack_robustness_data.csv", index=False)

    # ---------------------------------------------------------------- F2 sensitivity forest (paired delta AUC vs parent)
    lab = {"sens_k1p5": "MAD k = 1.5", "sens_k3p5": "MAD k = 3.5", "sens_alpha0p1": "Dirichlet alpha = 0.1", "sens_alpha1p0": "Dirichlet alpha = 1.0", "sens_C0p5x": "Clip 0.5x", "sens_C2x": "Clip 2x",
           "sens_chi0_dp": "chi_rec = 0 (DP)", "sens_chi0": "chi_rec = 0 (no noise)", "sens_chi0p25": "chi_rec = 0.25 (no noise)", "sens_chi0p75": "chi_rec = 0.75 (no noise)"}
    S = E[(E.family == "B_sensitivity") & (E.metric == "auc_sel")].copy()
    S["label"] = S.variant.map(lab)
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.8))
    order = list(lab.values())[::-1]
    for ax, ds in zip(axs, DS):
        s = S[S.dataset == ds].set_index("label").reindex(order)
        y = np.arange(len(order))
        col = [C["blue"] if "(DP)" in k or "k =" in k or "alpha" in k or "Clip" in k else C["green"] for k in order]
        ax.errorbar(s.mean_diff, y, xerr=[s.mean_diff - s.ci95_lo, s.ci95_hi - s.mean_diff], fmt="none", ecolor=C["grey"], elinewidth=1.2, capsize=2)
        ax.scatter(s.mean_diff, y, c=col, s=22, zorder=3)
        ax.axvline(0, color="k", lw=.7)
        ax.set_yticks(y, [f"{k}  (n={int(s.loc[k].n_pairs)})" if pd.notna(s.loc[k].n_pairs) else k for k in order])
        ax.set_xlabel("paired change in ROC-AUC (mean, 95% t-interval)")
        ax.set_title(DS[ds])
    fig.suptitle("Sensitivity (blue: central-DP parent reference_gaussian; green: non-private parent reference). Exact sign-flip p >= 0.0625 for n = 5.", fontsize=8)
    save(fig, pkg, "FIG2_sensitivity_forest"); S.to_csv(pkg / "figures" / "FIG2_sensitivity_forest_data.csv", index=False)

    # ---------------------------------------------------------------- F3 2x2 routing x surrogate
    cells = [("Routing ON, surrogate OFF", "ctl_imputation_none", 0, 0), ("Routing ON, surrogate ON", "reference", 0, 1), ("Routing OFF, surrogate OFF", "t4_e2_robust_random_path", 1, 0), ("Routing OFF, surrogate ON", "ix_routeoff_surron", 1, 1)]
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.2))
    rows = []
    for ax, ds in zip(axs, DS):
        for rt, col, nm in ((0, C["blue"], "routing ON (top-k)"), (1, C["orange"], "routing OFF (uniform random)")):
            xs, ms = [], []
            for lab_, arm, r_, s_ in cells:
                if r_ != rt:
                    continue
                v = P[(P.dataset == ds) & (P.arm == arm)].sort_values("seed")
                dots(ax, s_, v.auc_sel.to_numpy(), col); xs.append(s_); ms.append(v.auc_sel.mean())
                rows += [dict(dataset=ds, cell=lab_, arm=arm, seed=sd, run_id=ri, auc_sel=a) for sd, ri, a in zip(v.seed, v.run_id, v.auc_sel)]
            ax.plot(xs, ms, "-o", color=col, label=nm, ms=4)
        ax.set_xticks([0, 1], ["surrogate OFF", "surrogate ON"]); ax.set_title(DS[ds]); ax.set_ylabel("ROC-AUC (selected)" if ds == "unsw" else "")
    axs[0].legend(fontsize=7)
    save(fig, pkg, "FIG3_routing_x_surrogate"); pd.DataFrame(rows).to_csv(pkg / "figures" / "FIG3_routing_x_surrogate_data.csv", index=False)

    # ---------------------------------------------------------------- F4 participation fairness (client-holdout)
    pol = [("part_topk_indep", "top-k / indep."), ("part_topk_coup", "top-k / coupled"), ("part_coverage_indep", "coverage / indep."), ("part_coverage_coup", "coverage / coupled"),
           ("part_uniform_indep", "uniform / indep."), ("part_uniform_coup", "uniform / coupled")]
    fig, axs = plt.subplots(2, 2, figsize=(7.4, 5.4), sharex=True)
    rows = []
    for j, ds in enumerate(DS):
        for i, (m, ylab) in enumerate((("worst_client_recall", "worst eligible-client held-out recall"), ("selection_gini", "selection Gini (lower = more even)"))):
            ax = axs[i, j]
            for x, (arm, nm) in enumerate(pol):
                v = P[(P.dataset == ds) & (P.arm == arm)].sort_values("seed")
                col = (C["blue"], C["orange"], C["green"])[x // 2]
                dots(ax, x, v[m].to_numpy(), col); ax.plot([x] * 2, [v[m].mean()] * 2, marker="_", ms=12, color=col, zorder=4)
                rows += [dict(dataset=ds, metric=m, policy=nm, arm=arm, seed=s, run_id=r, value=y) for s, r, y in zip(v.seed, v.run_id, v[m])]
            ax.set_xticks(range(6), [p[1] for p in pol], rotation=35, ha="right"); ax.set_ylabel(ylab if j == 0 else "", fontsize=8); ax.set_title(DS[ds] if i == 0 else "")
    fig.subplots_adjust(hspace=.12, wspace=.3)
    fig.suptitle("Participation: held-out client recall uses never-trained-on client holdouts (UNSW: SUPP_V1; CICIoT2023: SUPP_V2 leakage-safe holdout)", fontsize=8)
    save(fig, pkg, "FIG4_participation_fairness"); pd.DataFrame(rows).to_csv(pkg / "figures" / "FIG4_participation_fairness_data.csv", index=False)

    # ---------------------------------------------------------------- F5 scalability
    sc = [("scale_n25_k5", "N=25,k=5"), ("scale_n25_k10", "N=25,k=10"), ("scale_n50_k10", "N=50,k=10"), ("scale_n100_k10", "N=100,k=10"), ("scale_n100_k20", "N=100,k=20")]
    fig, axs = plt.subplots(2, 3, figsize=(8.6, 5.2), sharex="col")
    fig.subplots_adjust(wspace=.45, hspace=.15)
    rows = []
    for j, ds in enumerate(DS):
        for i, (m, ylab) in enumerate((("auc_sel", "ROC-AUC (selected)"), ("wall_seconds", "wall-clock seconds / run"), ("bytes_on_wire", "bytes on wire / run (MB)"))):
            pass
    for r_, ds in enumerate(DS):
        for c_, (m, ylab, f) in enumerate((("auc_sel", "ROC-AUC (selected)", 1), ("wall_seconds", "wall-clock s / run", 1), ("bytes_on_wire", "MB on wire / run (sim.)", 1e-6))):
            ax = axs[r_, c_]
            for x, (arm, nm) in enumerate(sc):
                v = P[(P.dataset == ds) & (P.arm == arm)].sort_values("seed")
                dots(ax, x, v[m].to_numpy() * f, C["blue"]); ax.plot([x] * 2, [v[m].mean() * f] * 2, marker="_", ms=12, color=C["blue"], zorder=4)
                rows += [dict(dataset=ds, metric=m, config=nm, arm=arm, seed=s, run_id=r, value=y * f) for s, r, y in zip(v.seed, v.run_id, v[m])]
            ax.set_xticks(range(5), [s[1] for s in sc], rotation=40, ha="right", fontsize=7); ax.set_ylabel(ylab if True else ""); ax.set_title(DS[ds], fontsize=8, loc="left")
    save(fig, pkg, "FIG5_scalability"); pd.DataFrame(rows).to_csv(pkg / "figures" / "FIG5_scalability_data.csv", index=False)

    # ---------------------------------------------------------------- F6 chi_rec = 0 abstention (DP)
    ab = P[P.arm == "sens_chi0_dp"][["dataset", "seed", "run_id", "abstention_rounds", "auc_sel", "auc_last", "f1_sel"]].merge(
        P[P.arm == "reference_gaussian"][["dataset", "seed", "run_id", "auc_sel", "auc_last", "f1_sel"]], on=["dataset", "seed"], suffixes=("", "_ref"))
    ab["d_auc_sel"] = ab.auc_sel - ab.auc_sel_ref; ab["d_auc_last"] = ab.auc_last - ab.auc_last_ref
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.1), sharey=True)
    for ax, ds in zip(axs, DS):
        v = ab[ab.dataset == ds].sort_values("seed")
        ax.bar(np.arange(5) - .18, v.d_auc_sel, .34, color=C["blue"], label="selected checkpoint")
        ax.bar(np.arange(5) + .18, v.d_auc_last, .34, color=C["orange"], label="last round")
        ax.axhline(0, color="k", lw=.7)
        ax.set_xticks(range(5), [f"s{s}\n{int(a)} abst." for s, a in zip(v.seed, v.abstention_rounds)])
        ax.set_title(DS[ds]); ax.set_ylabel("AUC(chi_rec=0, DP) - AUC(reference_gaussian)" if ds == "unsw" else "")
    axs[0].legend(fontsize=7)
    save(fig, pkg, "FIG6_chi0_abstention"); ab.to_csv(pkg / "figures" / "FIG6_chi0_abstention_data.csv", index=False)

    # ---------------------------------------------------------------- F7 checkpoint vs last-round stability
    grp = [("reference", "reference\n(no noise)"), ("reference_gaussian", "reference_\ngaussian"), ("scenario_fedavg_topk", "FedAvg"), ("ix_routeoff_surron", "routing OFF\n+surrogate"),
           ("part_topk_indep", "participation\ntop-k"), ("part_uniform_coup", "participation\nuniform")]
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    rows = []
    for ax, ds in zip(axs, DS):
        for x, (arm, nm) in enumerate(grp):
            v = P[(P.dataset == ds) & (P.arm == arm)].sort_values("seed")
            dots(ax, x, v.auc_drop_sel_minus_last.to_numpy(), C["purple"]); ax.plot([x] * 2, [v.auc_drop_sel_minus_last.mean()] * 2, marker="_", ms=12, color=C["purple"], zorder=4)
            rows += [dict(dataset=ds, arm=arm, seed=s, run_id=r, auc_sel_minus_last=y, val_auc_sd_last10=z) for s, r, y, z in zip(v.seed, v.run_id, v.auc_drop_sel_minus_last, v.val_auc_sd_last10_rounds)]
        ax.axhline(0, color="k", lw=.7); ax.set_xticks(range(len(grp)), [g[1] for g in grp], fontsize=7); ax.set_title(DS[ds]); ax.set_ylabel("AUC(selected) - AUC(last round)" if ds == "unsw" else "")
    save(fig, pkg, "FIG7_checkpoint_vs_last"); pd.DataFrame(rows).to_csv(pkg / "figures" / "FIG7_checkpoint_vs_last_data.csv", index=False)

    # ---------------------------------------------------------------- final weight audit over every analysed identity
    out = []
    for _, r in P.iterrows():
        d = ROOT / r.out_dir
        ag = pd.read_csv(d / "aggregation_diagnostics.csv")
        priv_dp = bool(r.dp_enabled)
        kept = ag[ag.kept.astype(bool)]
        nu = nh = nr = so = 0
        sh = []
        mxdev = 0.0
        for _, g in kept.groupby("round"):
            n = len(g); nr += 1
            dev = float(np.abs(g.applied_weight_share - 1 / n).max()); mxdev = max(mxdev, dev); nu += dev < 1e-9
            nh += float(g.raw_weight.max() / max(g.raw_weight.min(), 1e-12)) > 1 + 1e-9
            s = float(g.loc[g.is_recovered_update.astype(bool), "applied_weight_share"].sum()); sh.append(s)
            so += int((~g.is_recovered_update.astype(bool)).sum() == 0)
        out.append(dict(dataset=r.dataset, arm=r.arm, seed=r.seed, run_id=r.run_id, source=r.source, central_dp=priv_dp, aggregation_rounds=nr, rounds_exactly_uniform=int(nu), rounds_heterogeneous_raw_weights=int(nh),
                        max_abs_dev_from_uniform=mxdev, surrogate_weight_share_mean=float(np.mean(sh)) if sh else np.nan, surrogate_weight_share_max=float(np.max(sh)) if sh else np.nan,
                        surrogate_only_rounds=int(so), abstention_rounds=r.get("abstention_rounds", np.nan), empty_rounds=r.empty_rounds_no_update_received))
    pd.DataFrame(out).to_csv(pkg / "SUPPLEMENTARY_WEIGHT_AUDIT_FINAL.csv", index=False)
    print("figures:", sorted(p.name for p in (pkg / "figures").glob("*.png")))


if __name__ == "__main__":
    main()
