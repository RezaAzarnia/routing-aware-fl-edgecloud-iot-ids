"""Read-only verification of the historical Phase-6C runs that the ablation reuses. Writes a CSV; never modifies results."""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import verify_run_dir, sha256_text_file, code_fingerprint  # noqa: E402
ARMS = ["reference","ctl_imputation_none","ctl_imputation_postfilter","ctl_imputation_cap010","ctl_momentum0_lr0p5",
        "ctl_momentum0_lr5p0","ctl_weighting_uniform","ctl_selection_uniform","ctl_selection_coverage","ctl_delivery_coupled",
        "reference_gaussian","corrected","scenario_fedavg_topk"]
m = json.loads((ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json").read_text())
cur_fp = code_fingerprint()
rows = []
for run in m["runs"]:
    if run["arm"] not in ARMS: continue
    d = ROOT / run["out_dir"] if "out_dir" in run else None
    probs = verify_run_dir(d, run, m, strict_commit=True)
    cfg_now = sha256_text_file(ROOT / run["config"]) if "config" in run else ""
    rows.append({"run_id": run["run_id"], "dataset": run["dataset"], "arm": run["arm"], "seed": run["seed"],
                 "out_dir": run["out_dir"], "verify_problems": "; ".join(probs) or "none",
                 "config_file_matches_manifest": cfg_now == run["config_sha256"],
                 "code_fingerprint_manifest_vs_current": "same" if cur_fp == m["code_fingerprint"] else "DIFFERENT"})
out = ROOT / "results_ablation_controlled_v2" / "historical_verification.csv"
out.parent.mkdir(exist_ok=True)
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
bad = [r for r in rows if r["verify_problems"] != "none"]
print(len(rows), "runs;", len(bad), "with problems"); 
import collections; print(collections.Counter(r["verify_problems"] for r in rows)); print(rows[0])
