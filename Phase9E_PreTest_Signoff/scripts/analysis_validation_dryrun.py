"""Phase 9E: validation-based dry run of the FROZEN final-test analysis pipeline. Reads NO test data.
Builds pseudo final-test result files from the audited VALIDATION report-partition metrics of the 50 primary runs (same JSON schema as
final_test_result_v2), runs scripts/final_test/analyze_final_test.py on them, and checks that the paired contrasts reproduce the independently built
validation ledger (Phase9_Manuscript_Revision/ledger/ledger_paired_contrasts_phase6c_audited.csv) to numerical precision.
python Phase9E_PreTest_Signoff/scripts/analysis_validation_dryrun.py"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / "docs" / "final_test" / "FINAL_TEST_MANIFEST.json").read_text(encoding="utf-8"))
post = pd.read_csv(ROOT / "posthoc_threshold_fix" / "phase6c_posthoc_with_deltas.csv")
post = post[post["phase"] == 1].set_index(["dataset", "arm", "seed"])
PRIMARY = {"reference", "clean_fedavg", "scenario_fedavg_topk", "corrected", "reference_gaussian"}


def block(prefix, key):
    g = lambda s: float(post.loc[key, f"{prefix}_rep_{s}_new"])
    return {"threshold": 0.5, "tp": 0, "fp": 0, "fn": 0, "tn": 0, "roc_auc": g("auc"), "pr_auc": float("nan"), "f1": g("f1"), "recall_adr": g("recall"),
            "precision": g("precision"), "fpr": g("fpr")}


with tempfile.TemporaryDirectory() as tmp:
    res, out = Path(tmp) / "results_pseudo", Path(tmp) / "ledgers"
    n = 0
    for rec in manifest["runs"]:
        if rec["source"] != "phase6c" or rec["arm"] not in PRIMARY:
            continue
        key = (rec["dataset"], rec["arm"], rec["seed"])
        d = res / rec["dataset"] / rec["arm"] / f"seed_{rec['seed']}"
        d.mkdir(parents=True)
        (d / "final_test_result.json").write_text(json.dumps({
            "dataset": rec["dataset"], "arm": rec["arm"], "seed": rec["seed"], "test_rows": 0, "test_benign": 0, "calibration_reference": rec["calibration_reference"],
            "best": {"primary": block("best", key)}, "last": {"primary": block("last", key)}, "overlap_controlled": {}}), encoding="utf-8")
        n += 1
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "final_test" / "analyze_final_test.py"), "--results", str(res), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    got = pd.read_csv(out / "ledger_final_test_paired_contrasts.csv")
    ref = pd.read_csv(ROOT / "Phase9_Manuscript_Revision" / "ledger" / "ledger_paired_contrasts_phase6c_audited.csv")
    rows, bad = [], 0
    for contrast in ("reference - clean_fedavg", "reference - scenario_fedavg_topk", "corrected - reference", "reference_gaussian - reference"):
        for ds in ("unsw", "ciciot"):
            for ck, metric_got, metric_ref in (("best", "roc_auc", "best_auc_audited"), ("last", "roc_auc", "last_auc_audited"), ("best", "f1", "best_f1_audited")):
                a = got[(got.contrast == contrast) & (got.dataset == ds) & (got.checkpoint == ck) & (got.metric == metric_got)].iloc[0]
                b = ref[(ref.contrast == contrast) & (ref.dataset == ds) & (ref.metric == metric_ref)].iloc[0]
                ok = (abs(a.mean_diff - b.mean_diff) < 1e-4 and abs(a.ci95_lo - b.ci95_lo) < 1e-4 and abs(a.ci95_hi - b.ci95_hi) < 1e-4 and a.n_first_better == b.n_first_better
                      and abs(a.p_exact_signflip - b.p_exact_signflip) < 1e-9)
                bad += not ok
                rows.append({"contrast": contrast, "dataset": ds, "checkpoint": ck, "metric": metric_got, "analysis_mean_diff": round(float(a.mean_diff), 5),
                             "ledger_mean_diff": round(float(b.mean_diff), 5), "wins": int(a.n_first_better), "p_exact": float(a.p_exact_signflip), "match": bool(ok)})
    report = {"purpose": "validation-based dry run of the frozen analysis pipeline (pseudo results built from audited VALIDATION metrics; no test data)", "pseudo_result_files": n,
              "comparisons": len(rows), "mismatches": bad, "rows": rows}
    (ROOT / "Phase9E_PreTest_Signoff" / "evidence" / "analysis_validation_dryrun.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"{n} pseudo results, {len(rows)} comparisons, {bad} mismatches")
    sys.exit(1 if bad else 0)
