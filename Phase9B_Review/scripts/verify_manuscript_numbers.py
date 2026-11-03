"""Phase 9B: re-derive every hand-typed in-text number of Phase9_Manuscript_Revision/latex/main.tex from the raw run folders / ledgers.
READ-ONLY. It recomputes values directly from results_phase6c / results_phase7b (not from the ledger CSVs where possible) so that a ledger bug would be caught.
Run: python Phase9B_Review/scripts/verify_manuscript_numbers.py"""
import json, math, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
ph = pd.read_csv(ROOT / "posthoc_threshold_fix" / "phase6c_posthoc_with_deltas.csv")           # audited per-run metrics (independent of the ledger builder)
ph = ph[ph["phase"] == 1].copy()                                                                 # Phase 6C only (240 runs)
assert len(ph) == 240
p7 = pd.read_csv(ROOT / "docs/phase8/tables/T2a_phase7b_per_run.csv")
fails = []
n_ok = 0


def chk(name, got, want, tol):
    global n_ok
    ok = abs(got - want) <= tol
    n_ok += ok
    if not ok:
        fails.append((name, got, want))
    print(("OK  " if ok else "FAIL"), name, f"got={got:.5f} manuscript={want}")


def arm(ds, a, col):
    return ph[(ph.dataset == ds) & (ph.arm == a)].sort_values("seed")[col].to_numpy()


def paired(ds, a, b, col):
    d = arm(ds, a, col) - arm(ds, b, col)
    s = d.std(ddof=1)
    ci = stats.t.interval(0.95, 4, loc=d.mean(), scale=s / math.sqrt(5))
    return d.mean(), ci, int((d > 0).sum())


# --- abstract / results text
for a, want in (("scenario_fedavg_topk", 0.6043), ("scenario_fedavg_random", 0.6493)):
    chk(f"UNSW last AUC mean {a}", arm("unsw", a, "last_rep_auc_new").mean(), want, 6e-4)
chk("UNSW last AUC SD topk", arm("unsw", "scenario_fedavg_topk", "last_rep_auc_new").std(ddof=1), 0.1430, 6e-4)
chk("UNSW last AUC SD random", arm("unsw", "scenario_fedavg_random", "last_rep_auc_new").std(ddof=1), 0.1750, 6e-4)
chk("collapsed topk", int((arm("unsw", "scenario_fedavg_topk", "last_rep_auc_new") < 0.8).sum()), 5, 0)
chk("collapsed random", int((arm("unsw", "scenario_fedavg_random", "last_rep_auc_new") < 0.8).sum()), 4, 0)
chk("CIC undefended last min", min(arm("ciciot", a, "last_rep_auc_new").min() for a in ("scenario_fedavg_random", "scenario_fedavg_topk")), 0.31, 0.006)
chk("CIC undefended last max", max(arm("ciciot", a, "last_rep_auc_new").max() for a in ("scenario_fedavg_random", "scenario_fedavg_topk")), 0.76, 0.006)
chk("CIC undefended best min", min(arm("ciciot", a, "best_rep_auc_new").min() for a in ("scenario_fedavg_random", "scenario_fedavg_topk")), 0.945, 0.001)
chk("CIC undefended best max", max(arm("ciciot", a, "best_rep_auc_new").max() for a in ("scenario_fedavg_random", "scenario_fedavg_topk")), 0.996, 0.001)
chk("UNSW best Reference", arm("unsw", "reference", "best_rep_auc_new").mean(), 0.9838, 6e-5)
chk("UNSW best clean FedAvg", arm("unsw", "clean_fedavg", "best_rep_auc_new").mean(), 0.9843, 6e-5)
chk("UNSW best centralized", arm("unsw", "clean_centralized", "best_rep_auc_new").mean(), 0.991, 6e-4)
chk("CIC best Reference", arm("ciciot", "reference", "best_rep_auc_new").mean(), 0.9962, 6e-5)
m, ci, w = paired("unsw", "reference", "clean_fedavg", "best_rep_auc_new")
chk("Ref-cleanFedAvg mean", m, -0.0005, 6e-5); chk("  CI lo", ci[0], -0.0032, 6e-5); chk("  CI hi", ci[1], 0.0022, 6e-5); chk("  wins", w, 2, 0)
m, ci, w = paired("unsw", "reference", "scenario_fedavg_topk", "best_rep_auc_new"); chk("Ref-topk best", m, 0.0968, 6e-4)
m, ci, w = paired("unsw", "reference", "scenario_fedavg_topk", "last_rep_auc_new"); chk("Ref-topk last", m, 0.3782, 6e-4); chk("  wins", w, 5, 0)
m, ci, w = paired("unsw", "corrected", "reference", "best_rep_auc_new")
chk("Cor-Ref best", m, -0.0082, 6e-5); chk("  CI lo", ci[0], -0.0147, 6e-5); chk("  CI hi", ci[1], -0.0017, 6e-5); chk("  wins", w, 0, 0)
m, ci, w = paired("unsw", "corrected", "reference", "last_rep_auc_new"); chk("Cor-Ref last", m, -0.0152, 6e-5)
m, ci, w = paired("ciciot", "corrected", "reference", "best_rep_auc_new"); chk("CIC Cor-Ref best", m, -0.0003, 6e-5)
m, ci, w = paired("unsw", "fail0p3_corrected", "fail0p3_reference", "last_rep_auc_new")
chk("30% last diff", m, -0.0884, 6e-5); chk("  CI lo", ci[0], -0.1983, 6e-4); chk("  CI hi", ci[1], 0.0215, 6e-4); chk("  wins(first better)", w, 0, 0)
chk("30% Ref last mean", arm("unsw", "fail0p3_reference", "last_rep_auc_new").mean(), 0.9817, 6e-5)
chk("30% Ref last SD", arm("unsw", "fail0p3_reference", "last_rep_auc_new").std(ddof=1), 0.0035, 6e-5)
chk("30% Cor last mean", arm("unsw", "fail0p3_corrected", "last_rep_auc_new").mean(), 0.8933, 6e-5)
chk("30% Cor last SD", arm("unsw", "fail0p3_corrected", "last_rep_auc_new").std(ddof=1), 0.0862, 6e-5)
chk("CIC 30% last diff", paired("ciciot", "fail0p3_corrected", "fail0p3_reference", "last_rep_auc_new")[0], -0.0192, 6e-5)
chk("Gaussian cost Ref UNSW", paired("unsw", "reference_gaussian", "reference", "best_rep_auc_new")[0], -0.0419, 6e-5)
chk("Gaussian cost Ref CIC", paired("ciciot", "reference_gaussian", "reference", "best_rep_auc_new")[0], -0.0032, 6e-5)
chk("Gaussian cost Cor UNSW", paired("unsw", "corrected_gaussian", "corrected", "best_rep_auc_new")[0], -0.0350, 6e-5)
chk("Gaussian cost Cor CIC", paired("ciciot", "corrected_gaussian", "corrected", "best_rep_auc_new")[0], -0.0021, 6e-5)
chk("Ref Gaussian UNSW best", arm("unsw", "reference_gaussian", "best_rep_auc_new").mean(), 0.9419, 6e-5)
for a, want in (("ctl_selection_uniform", -0.0023), ("ctl_selection_coverage", -0.0009)):
    chk(f"UNSW {a} best", paired("unsw", a, "reference", "best_rep_auc_new")[0], want, 6e-5)

# --- audit claims
d = ph.best_dauc.abs()
chk("max |best dAUC|", d.max(), 0.0037, 6e-5)
chk("max |best dF1|", ph.best_df1.abs().max(), 0.001, 6e-4)
chk("runs with last-round change (AUC or F1 >1e-3)", int(ph.affected_last.sum()), 17, 0)
chk("runs with last-round AUC change >1e-3", int((ph.last_dauc.abs() > 1e-3).sum()), 12, 0)
chk("runs with last-round AUC change >1e-2", int((ph.last_dauc.abs() > 1e-2).sum()), 7, 0)

# --- network (recomputed from raw run folders)
def route(ds, a):
    v = []
    for s in range(12, 17):
        d = ROOT / "results_phase6c" / ds / a / f"seed_{s}"
        rm = pd.read_csv(d / "round_metrics.csv"); rm = rm[rm["round"] > 0]
        pc = json.loads((d / "phase6c_diagnostics.json").read_text())
        nm = pd.read_csv(d / "network_metrics.csv")
        v.append([rm.mean_pdr.mean(), rm.mean_end_to_end_delay_ms.mean(), rm.mean_path_stability.mean(), rm.mean_transfer_efficiency_mbps.mean(),
                  pc["participation"]["selection_gini"], pc["participation"]["longest_exclusion_gap_rounds_selection"]["clients_never_selected"],
                  float((nm.update_delivered == True).mean()), float((nm.received_by_server == True).mean())])
    return np.mean(v, axis=0)
R = {a: route("unsw", a) for a in ("ctl_selection_uniform", "ctl_selection_coverage", "reference", "ctl_delivery_coupled", "corrected")}
C = {a: route("ciciot", a) for a in ("ctl_selection_uniform", "reference")}
chk("PDR top-k", R["reference"][0], 0.851, 6e-4); chk("PDR uniform", R["ctl_selection_uniform"][0], 0.782, 6e-4)
chk("PDR rel gain %", 100 * (R["reference"][0] / R["ctl_selection_uniform"][0] - 1), 8.9, 0.06)
chk("delay topk", R["reference"][1], 76.6, 0.06); chk("delay uniform", R["ctl_selection_uniform"][1], 81.5, 0.06)
chk("delay rel %", 100 * (R["reference"][1] / R["ctl_selection_uniform"][1] - 1), -6.0, 0.06)
chk("CIC delay rel %", 100 * (C["reference"][1] / C["ctl_selection_uniform"][1] - 1), -7.5, 0.06)
chk("CIC transfer rel %", 100 * (C["reference"][3] / C["ctl_selection_uniform"][3] - 1), 16.6, 0.06)
chk("transfer rel % UNSW", 100 * (R["reference"][3] / R["ctl_selection_uniform"][3] - 1), 15.5, 0.06)
chk("path stab uniform", R["ctl_selection_uniform"][2], 0.855, 6e-4); chk("path stab topk", R["reference"][2], 0.923, 6e-4)
chk("Gini topk", R["reference"][4], 0.731, 6e-4); chk("Gini coverage", R["ctl_selection_coverage"][4], 0.486, 6e-4); chk("Gini uniform", R["ctl_selection_uniform"][4], 0.205, 6e-4)
chk("never topk", R["reference"][5], 27.2, 0.06); chk("never coverage", R["ctl_selection_coverage"][5], 8.0, 0.06)
chk("PDR coverage", R["ctl_selection_coverage"][0], 0.833, 6e-4); chk("delay coverage", R["ctl_selection_coverage"][1], 76.3, 0.06)
chk("delivered topk indep", R["reference"][6], 0.848, 6e-4); chk("delivered topk coupled", R["ctl_delivery_coupled"][6], 0.681, 6e-4)
chk("delay coupled", R["ctl_delivery_coupled"][1], 262.6, 0.06); chk("transfer coupled", R["ctl_delivery_coupled"][3], 4.4, 0.06)
chk("PDR coupled", R["ctl_delivery_coupled"][0], 0.850, 6e-4)
chk("Corrected delay ratio", R["corrected"][1] / R["reference"][1], 3.5, 0.05); chk("Corrected delivered", R["corrected"][6], 0.626, 6e-4)

# --- MAD pooled
t5b = pd.read_csv(ROOT / "docs/phase8/tables/T5b_mad_filter_by_number_of_real_updates.csv"); t = t5b[t5b.results == "6C"]
chk("pooled malicious acceptance %", 100 * t.malicious_accepted.sum() / t.malicious.sum(), 15.0, 0.06)
chk("pooled honest rejection %", 100 * t.honest_rejected.sum() / t.honest.sum(), 5.3, 0.06)
chk("honest n", t.honest.sum(), 33356, 0); chk("malicious n", t.malicious.sum(), 7930, 0)
r3 = t[t.n_real_bin == "3"].iloc[0]; chk("n=3 honest rej %", 100 * r3.honest_rejected / r3.honest, 39.0, 0.06); chk("n=3 mal acc %", 100 * r3.malicious_accepted / r3.malicious, 30.6, 0.06)
r6 = t[t.n_real_bin == ">=6"].iloc[0]; chk(">=6 mal acc %", 100 * r6.malicious_accepted / r6.malicious, 14.1, 0.06)

# --- Phase 7b
def g(a, c): return p7[p7.arm == a][c]
chk("P7b fail corrected last mean", g("fail0p3_corrected", "last_auc").mean(), 0.8401, 6e-5); chk("P7b fail guard last mean", g("fail0p3_p7_corrected_guard", "last_auc").mean(), 0.9261, 6e-5)
chk("P7b fail ref last mean", g("fail0p3_reference", "last_auc").mean(), 0.9760, 6e-5); chk("P7b fail ref last SD", g("fail0p3_reference", "last_auc").std(ddof=1), 0.0056, 6e-5)
chk("collapses fail corrected", int(g("fail0p3_corrected", "collapse").sum()), 2, 0); chk("collapses fail guard", int(g("fail0p3_p7_corrected_guard", "collapse").sum()), 1, 0)
chk("skipped fail guard", int(g("fail0p3_p7_corrected_guard", "skipped_rounds").sum()), 17, 0); chk("skipped p7 corrected guard", int(g("p7_corrected_guard", "skipped_rounds").sum()), 2, 0)
dd = g("fail0p3_p7_corrected_guard", "last_auc").to_numpy()[np.argsort(p7[p7.arm == "fail0p3_p7_corrected_guard"].seed.to_numpy())] - g("fail0p3_corrected", "last_auc").to_numpy()[np.argsort(p7[p7.arm == "fail0p3_corrected"].seed.to_numpy())]
chk("guard better seeds", int((dd > 1e-12).sum()), 3, 0); chk("excl. seed17 mean", dd[1:].mean(), -0.0067, 6e-5); chk("seed19 delta", dd[2], -0.147, 6e-4)

# --- payload / dataset constants
for ds, want in (("unsw", 174728), ("ciciot", 95368)):
    chk(f"payload {ds}", int(pd.read_csv(ROOT / f"results_phase6c/{ds}/reference/seed_12/network_metrics.csv").update_bytes.iloc[0]), want, 0)
print(f"\n{n_ok} checks passed, {len(fails)} failed")
for f in fails:
    print("FAIL:", f)
sys.exit(1 if fails else 0)
