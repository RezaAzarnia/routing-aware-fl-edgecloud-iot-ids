"""Read-only Table 4 evidence audit. Writes only to Table4_Audit_Package/ (new directory; refuses to overwrite).
Inputs: main paper/main.tex (Table 4 parsed from source), locked Phase 6C runs, audited ledger. No training, no test data."""
import json, math, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT.parent / "main paper" / "main.tex"
OUT = ROOT / "Table4_Audit_Package"
if OUT.exists() and any(OUT.iterdir()):
    sys.exit("Table4_Audit_Package already exists and is not empty; refusing to overwrite")
OUT.mkdir(exist_ok=True)
LEDGER = pd.read_csv(ROOT / "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv").set_index(["dataset", "arm", "seed"])
SEEDS = [12, 13, 14, 15, 16]
METRICS = ["F1", "ROC-AUC", "FPR", "Delay (ms)", "PDR", "Path stability", "Transfer efficiency (Mbit/s)"]
MKEY = ["f1", "auc", "fpr", "delay", "pdr", "ps", "te"]

# ---------------------------------------------------------------- parse Table 4 from the manuscript source
lines = TEX.read_text(encoding="utf-8").splitlines()
start = next(i for i, l in enumerate(lines) if "label{tab:overall-results}" in l)
block = "\n".join(lines[start:start + 90])
ds_order = ["ciciot", "unsw"]
parts = re.split(r"\\textit\{(?:CICIoT2023|UNSW-NB15)\}", block)[1:]
names = ["FedAvg", "DP+FedAvg", "Robust no-DP", "Proposed eps~10", "Proposed eps~20"]
T4 = {}
for ds, part in zip(ds_order, parts):
    nums = re.findall(r"&\s*([0-9]+\.[0-9]+)", part)
    rows = [nums[i:i + 7] for i in range(0, 35, 7)]
    # each row: first number follows the method name '&'; the second line starts with '&' too -> 7 values per method
    for n, r in zip(names, rows):
        T4[(ds, n)] = [float(x) for x in r]
assert len(T4) == 10 and all(len(v) == 7 for v in T4.values()), T4
SRC_LINE = start + 1

# ---------------------------------------------------------------- locked-protocol per-seed values (executed runs)
ANALOG = {  # locked arm -> (Table 4 method it is the CLOSEST candidate for, equivalence verdict)
    "scenario_fedavg_random": ("FedAvg", "NOT EQUIVALENT: routing stays enabled (uniform-random selection over routed paths); Table 4 baseline disables routing (random paths)"),
    "clean_fedavg": ("FedAvg", "NOT EQUIVALENT: no attack, no recovery; routing disabled"),
    "robust_random_no_imputation": ("Robust no-DP", "NOT EQUIVALENT: routing enabled with uniform-random selection; Table 4 baseline disables routing"),
    "reference": ("Proposed eps~10 (no-DP counterpart)", "Reference without Gaussian noise; not a Table 4 row"),
    "reference_gaussian": ("Proposed eps~10", "CLOSEST: top-k routing + recovery + MAD filter + central Gaussian (eps_hat 9.9993); different split/attacker assignment/seeds/code"),
}
rows = []
for ds in ds_order:
    for arm in ANALOG:
        for s in SEEDS:
            d = ROOT / "results_phase6c" / ds / arm / f"seed_{s}"
            comp = json.loads((d / "COMPLETE.json").read_text())
            nm = pd.read_csv(d / "network_metrics.csv"); nm = nm[nm.selected == True]
            L = LEDGER.loc[(ds, arm, s)]
            rows.append(dict(dataset=ds, arm=arm, seed=s, run_id=comp["run_id"], out_dir=d.relative_to(ROOT).as_posix(),
                             config_sha256=comp["config_sha256"], code_fingerprint=comp["code_fingerprint"], manifest_sha256=comp["manifest_sha256"],
                             evaluation_partition="report partition of three-way group-disjoint validation (test never loaded)",
                             checkpoint_rule="best round by selection-partition ROC-AUC", threshold_rule="calibration partition, FPR cap 0.15 / min recall 0.6",
                             f1_selected=L.best_f1_audited, auc_selected=L.best_auc_audited, fpr_selected=L.best_fpr_audited,
                             f1_last=L.last_f1_audited, auc_last=L.last_auc_audited, fpr_last=L.last_fpr_audited,
                             delay_ms=nm.end_to_end_delay_ms.mean(), pdr_first_transmission=nm.pdr.mean(),
                             update_delivery_rate=nm.update_delivered.mean(), path_stability=nm.path_stability.mean(),
                             transfer_efficiency_mbps=nm.transfer_efficiency_mbps.mean(),
                             table4_closest_candidate=ANALOG[arm][0], equivalence_to_table4=ANALOG[arm][1],
                             metric_source="detection: audited ledger; network: network_metrics.csv over selected transfers"))
V = pd.DataFrame(rows)
V.to_csv(OUT / "TABLE4_VERIFIED_METRICS.csv", index=False)
col = {"f1": "f1_selected", "auc": "auc_selected", "fpr": "fpr_selected", "delay": "delay_ms", "pdr": "pdr_first_transmission", "ps": "path_stability", "te": "transfer_efficiency_mbps"}

def stat(ds, arm, k):
    x = V[(V.dataset == ds) & (V.arm == arm)][col[k]].to_numpy(float)
    return x.mean(), x.std(ddof=1)

# ---------------------------------------------------------------- paired differences between locked arms (valid pairing: same seed, same partitions)
pairs = [("reference_gaussian", "scenario_fedavg_random"), ("reference_gaussian", "robust_random_no_imputation"), ("reference_gaussian", "clean_fedavg"),
         ("reference", "scenario_fedavg_random"), ("reference", "robust_random_no_imputation"), ("reference_gaussian", "reference")]
pr = []
for ds in ds_order:
    for a, b in pairs:
        for k in MKEY + ["deliv"]:
            c = col.get(k, "update_delivery_rate")
            xa = V[(V.dataset == ds) & (V.arm == a)].sort_values("seed")[c].to_numpy(float)
            xb = V[(V.dataset == ds) & (V.arm == b)].sort_values("seed")[c].to_numpy(float)
            d = xa - xb; mu = d.mean(); sd = d.std(ddof=1); tc = stats.t.ppf(0.975, 4); se = sd / math.sqrt(5)
            pr.append(dict(dataset=ds, first=a, second=b, metric=c, mean_first=xa.mean(), mean_second=xb.mean(), mean_diff=mu, sd_diff=sd, ci95_lo=mu - tc * se, ci95_hi=mu + tc * se,
                           n_first_higher=int((d > 1e-12).sum()), n_first_lower=int((d < -1e-12).sum()), min_attainable_exact_p=0.0625,
                           note="locked-protocol arms only; NOT Table 4 comparisons"))
pd.DataFrame(pr).to_csv(OUT / "TABLE4_LOCKED_ANALOG_PAIRED_DIFFERENCES.csv", index=False)

# ---------------------------------------------------------------- recomputation of the percentages quoted in the manuscript
def pct(ds, m, b, i):
    return (T4[(ds, m)][i] - T4[(ds, b)][i]) / T4[(ds, b)][i] * 100
CLAIMS = [  # text claim, location, value, recomputed
    ("CICIoT2023 delay reduction vs FedAvg", "Results (Proposed eps~20)", 26.6, pct("ciciot", "Proposed eps~20", "FedAvg", 3)),
    ("CICIoT2023 PDR increase vs FedAvg", "Results", 13.4, pct("ciciot", "Proposed eps~20", "FedAvg", 4)),
    ("CICIoT2023 path-stability increase vs FedAvg", "Results", 62.8, pct("ciciot", "Proposed eps~20", "FedAvg", 5)),
    ("CICIoT2023 transfer-efficiency increase vs FedAvg", "Results", 46.0, pct("ciciot", "Proposed eps~20", "FedAvg", 6)),
    ("UNSW-NB15 F1 improvement vs FedAvg", "Results/Conclusion (eps~20)", 8.3, pct("unsw", "Proposed eps~20", "FedAvg", 0)),
    ("UNSW-NB15 ROC-AUC improvement vs FedAvg", "Results/Conclusion", 6.6, pct("unsw", "Proposed eps~20", "FedAvg", 1)),
    ("UNSW-NB15 delay reduction vs FedAvg", "Results/Conclusion", 24.7, -pct("unsw", "Proposed eps~20", "FedAvg", 3)),
    ("UNSW-NB15 path-stability increase vs FedAvg", "Results/Conclusion", 63.5, pct("unsw", "Proposed eps~20", "FedAvg", 5)),
]
CL = pd.DataFrame([dict(claim=c, location=l, manuscript_pct=v, recomputed_from_table4_pct=round(abs(r), 2), arithmetic_status="REPRODUCES" if abs(abs(r) - v) < 0.06 else "DIFFERS", provenance_status="NOT VERIFIED (inputs unsourced)") for c, l, v, r in CLAIMS])
CL.to_csv(OUT / "TABLE4_CLAIM_ARITHMETIC.csv", index=False)

# ---------------------------------------------------------------- per-row evidence audit (dataset x method x metric)
CAND = {"FedAvg": "scenario_fedavg_random", "DP+FedAvg": None, "Robust no-DP": "robust_random_no_imputation", "Proposed eps~10": "reference_gaussian", "Proposed eps~20": None}
CFG = {"FedAvg": "old suite `fedavg_scenario` (routing off, no DP, FedAvg, recovery off; attack+failure on) - inferred from src/suites.py@7c75b2d, no run record",
       "DP+FedAvg": "old suite `fedavg_dp_scenario` (routing off, recovery off, FedAvg + central Gaussian eps 10) - inferred, no run record",
       "Robust no-DP": "old suite `robust_no_dp_scenario` (routing off, recovery off, distance filter, no DP) - inferred, no run record",
       "Proposed eps~10": "CIC: configs/ciciot2023_eps10.yaml (exists); UNSW: configs/full.yaml (target eps 10) - config files exist, outputs do not",
       "Proposed eps~20": "CIC: configs/ciciot2023_eps20.yaml (exists); UNSW: no eps-20 config; only suite `privacy_sweep` (seeds 2-4) could produce it - provenance ambiguous"}
audit_rows = []
for ds in ds_order:
    for m in names:
        for k, mn in zip(MKEY, METRICS):
            man = T4[(ds, m)][MKEY.index(k)]
            arm = CAND[m]
            if arm:
                mu, sd = stat(ds, arm, k); an = f"{arm}: {mu:.4f} (SD {sd:.4f}), 5 seeds, locked protocol"
            else:
                an = "no locked-protocol arm exists"
            audit_rows.append(dict(dataset={"ciciot": "CICIoT2023", "unsw": "UNSW-NB15"}[ds], method=m, metric=mn, manuscript_value=man,
                                   status="NOT VERIFIED", executed_run_ids="none found", seeds="documented plan: 2-6 (README); none found in artifacts",
                                   source_path="none (no results/ directory, no final_test_metrics.csv, not in Zenodo archive, not in git history)",
                                   configuration_evidence=CFG[m], closest_locked_analog=an,
                                   comment="Value has no identifiable source; closeness to the analog is not verification"))
A = pd.DataFrame(audit_rows)
A.to_csv(OUT / "_table4_row_audit.csv", index=False)

# discrepancy rows: manuscript vs closest locked analog
disc = []
for ds in ds_order:
    for m in ["FedAvg", "Robust no-DP", "Proposed eps~10"]:
        arm = CAND[m]
        for k, mn in zip(MKEY, METRICS):
            mu, sd = stat(ds, arm, k); man = T4[(ds, m)][MKEY.index(k)]
            disc.append(dict(dataset=ds, method=m, metric=mn, manuscript=man, locked_analog=arm, locked_mean=round(mu, 4), locked_sd=round(sd, 4), difference=round(man - mu, 4),
                             relative_pct=round((man - mu) / mu * 100, 1)))
D = pd.DataFrame(disc); D.to_csv(OUT / "_table4_discrepancy_rows.csv", index=False)

def md_table(df, cols=None, floatfmt=4):
    cols = cols or list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join((f"{r[c]:.{floatfmt}f}" if isinstance(r[c], float) else str(r[c])) for c in cols) + " |")
    return "\n".join(out)

(OUT / "_row_audit_table.md").write_text(md_table(A, ["dataset", "method", "metric", "manuscript_value", "status", "closest_locked_analog"]), encoding="utf-8")
(OUT / "_discrepancy_table.md").write_text(md_table(D, ["dataset", "method", "metric", "manuscript", "locked_analog", "locked_mean", "locked_sd", "difference", "relative_pct"]), encoding="utf-8")
(OUT / "_claims_table.md").write_text(md_table(CL), encoding="utf-8")
paired_md = pd.DataFrame(pr)
(OUT / "_paired_table.md").write_text(md_table(paired_md[paired_md.metric.isin(["f1_selected", "auc_selected", "fpr_selected", "delay_ms", "pdr_first_transmission", "update_delivery_rate", "path_stability", "transfer_efficiency_mbps"])],
                                              ["dataset", "first", "second", "metric", "mean_first", "mean_second", "mean_diff", "sd_diff", "ci95_lo", "ci95_hi", "n_first_higher", "n_first_lower"]), encoding="utf-8")
print("rows:", len(V), "audit rows:", len(A), "T4 parsed:", len(T4), "table4 line", SRC_LINE)
print(CL.to_string())
