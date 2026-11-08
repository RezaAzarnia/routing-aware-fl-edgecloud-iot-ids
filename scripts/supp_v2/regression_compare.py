"""V1-to-V2 equivalence gate. For every gate run that has a verified SUPP_V1 counterpart, compare the SUPP_V2 artifacts to the SUPP_V1 artifacts EXACTLY
(no tolerance): round metrics (all deterministic columns), network trace, aggregation diagnostics, recovery events, client distribution, validation-split info,
final validation metrics and the best-checkpoint tensors. Runs without a V1 counterpart (CIC holdout dry run, chi_rec=0 seed 13) get structural checks only.
Read-only on both result trees; writes results_supplementary_v2/_tests/regression_report.json and .csv.
usage: python scripts/supp_v2/regression_compare.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import OUT_ROOT, V1_ROOT, load_manifest, MANIFEST, verify_run_dir  # noqa: E402

TIMING_COLS = {"round_seconds", "mean_local_train_seconds", "local_train_seconds"}   # wall-clock measurements (non-deterministic by nature)
NEW_V2_COLS = {"no_valid_contribution", "noisy_release", "attempted_privacy_rounds_cum", "noise_release_rounds_cum", "privacy_epsilon_attempted_rounds_conservative"}


def frames_equal(a: pd.DataFrame, b: pd.DataFrame, drop=()):
    cols = [c for c in a.columns if c in b.columns and c not in drop]
    if len(a) != len(b):
        return False, f"row count {len(a)} vs {len(b)}"
    bad = []
    for c in cols:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            same = np.array_equal(x.to_numpy(dtype=float), y.to_numpy(dtype=float), equal_nan=True)
        else:
            same = x.astype(str).tolist() == y.astype(str).tolist()
        if not same:
            bad.append(c)
    return not bad, (f"{len(cols)} common columns identical" if not bad else f"differs in {bad[:6]}")


def json_equal(p1: Path, p2: Path, ignore=()):
    a, b = json.loads(p1.read_text(encoding="utf-8")), json.loads(p2.read_text(encoding="utf-8"))
    for k in ignore:
        a.pop(k, None), b.pop(k, None)
    return a == b


def tensors_equal(p1: Path, p2: Path):
    import torch
    a, b = torch.load(p1, map_location="cpu", weights_only=True), torch.load(p2, map_location="cpu", weights_only=True)
    return list(a) == list(b) and all(torch.equal(a[k], b[k]) for k in a)


def main():
    manifest = load_manifest(MANIFEST)
    rows = []
    for r in manifest["runs"]:
        if not r.get("gate"):
            continue
        d2 = ROOT / r["out_dir"]
        d1 = ROOT / V1_ROOT / r["dataset"] / r["arm"] / f"seed_{r['seed']}"
        rec = {"run_id": r["run_id"], "role": r["role"], "v2_verified": not verify_run_dir(d2, r, manifest) if (d2 / "COMPLETE.json").exists() else False, "v1_counterpart": (d1 / "COMPLETE.json").exists()}
        rm2 = pd.read_csv(d2 / "round_metrics.csv") if (d2 / "round_metrics.csv").exists() else None
        rec["v2_abstention_rounds"] = int(rm2["no_valid_contribution"].sum()) if rm2 is not None else None
        checks = {}
        if rm2 is not None and rec["v1_counterpart"]:
            rm1 = pd.read_csv(d1 / "round_metrics.csv")
            checks["round_metrics (all deterministic common columns)"] = frames_equal(rm1, rm2, TIMING_COLS | NEW_V2_COLS)
            for name in ("network_metrics.csv", "aggregation_diagnostics.csv", "recovery_events.csv", "client_distribution.csv"):
                checks[name] = frames_equal(pd.read_csv(d1 / name), pd.read_csv(d2 / name), TIMING_COLS)
            checks["validation_split_info.json"] = (json_equal(d1 / "validation_split_info.json", d2 / "validation_split_info.json"), "")
            checks["final_validation_metrics.json"] = (json_equal(d1 / "final_validation_metrics.json", d2 / "final_validation_metrics.json"), "")
            checks["best_model_state.pt (all tensors bit-identical)"] = (tensors_equal(d1 / "best_model_state.pt", d2 / "best_model_state.pt"), "")
            checks["last_model_state.pt (all tensors bit-identical)"] = (tensors_equal(d1 / "last_model_state.pt", d2 / "last_model_state.pt"), "")
            checks["no abstention round (positive-weight run)"] = (rec["v2_abstention_rounds"] == 0, f"{rec['v2_abstention_rounds']} abstention rounds")
            if rec["v2_abstention_rounds"] == 0:
                checks["epsilon release-based == attempted (no abstention)"] = (bool(np.allclose(rm2["privacy_epsilon_estimate"], rm2["privacy_epsilon_attempted_rounds_conservative"], equal_nan=True)), "")
        elif rm2 is not None:
            a = json.loads((d2 / "client_holdout_audit.json").read_text(encoding="utf-8"))
            checks["no V1 counterpart (V1 did not produce this run): structural checks only"] = (True, "")
            if a.get("enabled"):
                checks["holdout audit: leakage counters zero, preprocessor on non-holdout rows only"] = (a["predictor_groups_straddling_train_holdout"] == 0 and a["encoded_vectors_straddling_train_holdout"] == 0
                                                                                                         and a["preprocessor_fitted_on_non_holdout_rows_only"], f"holdout {a['holdout_rows']} ({a['realized_fraction']:.3f})")
            if r["arm"] == "sens_chi0_dp" and r["seed"] == 13:
                checks["V1 crashed at round 21; V2 completed 30 rounds"] = (len(rm2[rm2['round'] > 0]) == 30, f"{rec['v2_abstention_rounds']} abstention rounds")
                checks["abstention rounds (if any) add no noise"] = (bool((rm2[rm2.no_valid_contribution == 1].privacy_noise_std == 0).all()), "")
        rec["checks"] = {k: {"pass": bool(v[0]), "detail": v[1]} for k, v in checks.items()}
        rec["gate_pass"] = bool(rec["v2_verified"]) and all(v["pass"] for v in rec["checks"].values()) and bool(checks)
        rows.append(rec)
    out = ROOT / OUT_ROOT / "_tests"
    out.mkdir(parents=True, exist_ok=True)
    (out / "regression_report.json").write_text(json.dumps({"gate_pass": all(x["gate_pass"] for x in rows), "runs": rows}, indent=1), encoding="utf-8")
    flat = [{"run_id": x["run_id"], "v1_counterpart": x["v1_counterpart"], "v2_verified": x["v2_verified"], "abstention_rounds": x["v2_abstention_rounds"], "check": k, "pass": v["pass"], "detail": v["detail"]}
            for x in rows for k, v in x["checks"].items()]
    pd.DataFrame(flat).to_csv(out / "regression_report.csv", index=False)
    for x in rows:
        print(("PASS " if x["gate_pass"] else "FAIL ") + x["run_id"], "| v1 counterpart:", x["v1_counterpart"], "| abstentions:", x["v2_abstention_rounds"])
        for k, v in x["checks"].items():
            if not v["pass"] or "--verbose" in sys.argv:
                print("     ", "ok  " if v["pass"] else "FAIL", k, v["detail"])
    print("GATE", "PASS" if all(x["gate_pass"] for x in rows) else "FAIL")
    return 0 if all(x["gate_pass"] for x in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
