"""Phase 9D: complete the preprocessor-equivalence coverage to ALL 15 distinct (dataset, seed) combinations of the frozen 280-run manifest
and prove that every one of the 280 saved preprocessors equals the preprocessor of its (dataset, seed) pair.

Why 12 pairs earlier: `final_test_v2.py preproc-equiv` deliberately refits CICIoT2023 only for seeds 12 and 16 (the CIC training file is seed-independent, so the
refit is redundant), but it refits all 10 UNSW (dataset, seed) pairs (the group-disjoint split depends on the seed): 10 + 2 = 12 of 15. This script closes the
remaining CIC seeds 13, 14, 15 by refitting from TRAINING data only (load_dataset(load_test=False)) and then compares every run's saved preprocessor with its pair.
Reads training/validation data only; the protected-access guard is installed and any violation is reported.   python Phase9D_Final_Freeze/scripts/preproc_coverage_15_pairs.py"""
import collections
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
import joblib  # noqa: E402

import final_test_v2 as ft  # noqa: E402
import protected_access_guard as guard  # noqa: E402
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402

guard.install()
manifest = ft.load_manifest(ft.MANIFEST_PATH)
prev = json.loads((ROOT / "Phase9C_Submission_Readiness" / "evidence" / "preprocessor_equivalence.json").read_text(encoding="utf-8"))
already = {(r["dataset"], r["seed"]): r for r in prev["rows"]}
pairs = collections.OrderedDict()
for rec in manifest["runs"]:
    pairs.setdefault((rec["dataset"], rec["seed"]), []).append(rec)
assert len(pairs) == 15 and sum(len(v) for v in pairs.values()) == 280

rows = []
for (ds, seed), recs in pairs.items():
    first = recs[0]
    d = ROOT / first["run_dir"]
    saved_ref = ft._prep_params(joblib.load(d / "preprocessor.joblib"))
    if (ds, seed) in already:
        refit_identical, how = already[(ds, seed)]["identical"], "refit (Phase 9C evidence)"
    else:
        cfg = Config.from_yaml(d / "resolved_config.yaml")
        cfg.data.test_csv = ""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "refit.joblib"
            load_dataset(cfg.data, seed=seed, preprocessor_output=out, load_test=False)
            refit = ft._prep_params(joblib.load(out))
        refit_identical = all(ft._same(saved_ref.get(k), refit.get(k)) for k in set(saved_ref) | set(refit))
        how = "refit (Phase 9D, training data only)"
    # every run of the pair must carry the same preprocessor (same training data => same fit)
    mismatches = []
    for rec in recs:
        prm = ft._prep_params(joblib.load(ROOT / rec["run_dir"] / "preprocessor.joblib"))
        if not all(ft._same(saved_ref.get(k), prm.get(k)) for k in set(saved_ref) | set(prm)):
            mismatches.append(rec["run_id"])
    rows.append({"dataset": ds, "seed": seed, "sources": sorted({r["source"] for r in recs}), "runs": len(recs), "n_features_out": len(saved_ref["features_out"]),
                 "saved_equals_training_only_refit": bool(refit_identical), "refit_evidence": how, "runs_with_different_preprocessor": mismatches})
    print(ds, seed, len(recs), "refit-identical" if refit_identical else "REFIT DIFFERS", "mismatching runs:", len(mismatches), flush=True)

result = {"manifest_sha256": manifest["manifest_sha256"], "distinct_dataset_seed_pairs": len(rows), "runs_covered": sum(r["runs"] for r in rows),
          "all_pairs_identical_to_training_only_refit": all(r["saved_equals_training_only_refit"] for r in rows),
          "all_runs_share_their_pair_preprocessor": all(not r["runs_with_different_preprocessor"] for r in rows), "locked_test_opened": guard.violations, "rows": rows}
(ROOT / "Phase9D_Final_Freeze" / "evidence" / "preprocessor_coverage_15_pairs.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
sys.exit(0 if result["all_pairs_identical_to_training_only_refit"] and result["all_runs_share_their_pair_preprocessor"] and not guard.violations else 1)
