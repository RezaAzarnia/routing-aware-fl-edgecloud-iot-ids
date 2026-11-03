"""Phase 9E: end-to-end REHEARSAL of the final-test pathway on SYNTHETIC "locked" files in a temporary project root.
Nothing here touches the real locked test files or any historical results directory; the rehearsal authorization is a pytest fixture, not the owner's signature."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import final_test_v2 as ft  # noqa: E402
import protected_access_guard as guard  # noqa: E402
from test_phase7_guard import make_config  # noqa: E402

RUN_ONE = ROOT / "scripts" / "phase6c" / "run_one.py"


def _train_seed(cfg_path: Path, out: Path, seed: int):
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.pop("IOTFL_LIVE", None)
    r = subprocess.run([sys.executable, str(RUN_ONE), "--config", str(cfg_path), "--seed", str(seed), "--out", str(out)], capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-800:]


def _test_frame(n=1000, seed=99):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    return pd.DataFrame({"id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y, "proto": rng.choice(["tcp", "udp"], n),
                         "service": rng.choice(["-", "http"], n), "state": rng.choice(["FIN", "CON"], n), "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y})


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    proj = tmp_path_factory.mktemp("rehearsal_root")
    (proj / "data").mkdir()
    cfg_path = make_config(proj, min_real_updates=0)                       # writes proj/train.csv and the config
    (proj / "data" / "train.csv").write_bytes((proj / "train.csv").read_bytes())
    locked = proj / "data" / "locked_synthetic_test.csv"
    _test_frame().to_csv(locked, index=False)
    runs = []
    for arm, seeds in (("reference", (7, 8)), ("clean_fedavg", (7, 8))):
        for seed in seeds:
            out = proj / "runs" / arm / f"seed_{seed}"
            _train_seed(cfg_path, out, seed)
            fin = json.loads((out / "final_validation_metrics.json").read_text(encoding="utf-8"))
            sel = fin["selected_operating_point"]
            runs.append({"run_id": f"unsw__{arm}__seed{seed}", "source": "synthetic", "dataset": "unsw", "arm": arm, "seed": seed, "run_dir": str(out.relative_to(proj)),
                         "best_checkpoint_sha256": ft.sha256_file(out / "best_model_state.pt"), "last_checkpoint_sha256": ft.sha256_file(out / "last_model_state.pt"),
                         "preprocessor_sha256": ft.sha256_file(out / "preprocessor.joblib"), "best_round": fin["best_round"],
                         "thresholds": {"best_primary": sel["threshold"], "last_primary": fin["last_round_selection_partition"]["threshold"],
                                        "targets": {k: v["calibration_partition"]["threshold"] for k, v in fin["threshold_diagnostics"].items()}},
                         "calibration_reference": {"fpr": sel.get("calibration_fpr"), "recall": sel.get("calibration_recall_adr"), "constraint_feasible": sel.get("constraint_feasible")}})
    m = {"schema": ft.SCHEMA, "plan": ft.PLAN, "sources": {}, "n_runs": len(runs), "runs": runs,
         "locked_test": {"unsw": {"path": "data/locked_synthetic_test.csv", "kind": "csv", "sha256": hashlib.sha256(locked.read_bytes()).hexdigest()}},
         "protected_reference_files": {"unsw": {"train": "data/train.csv"}},
         "evaluation_code": {"globs": ft.EVAL_GLOBS, "fingerprint": ft.code_fingerprint(proj, ft.EVAL_GLOBS)}}
    m["manifest_sha256"] = ft.manifest_hash(m)
    mpath = proj / "manifest.json"
    mpath.write_text(json.dumps(m), encoding="utf-8")
    auth = {"manifest_sha256": m["manifest_sha256"], "plan": ft.PLAN, "authorized": True, "statement": ft.AUTH_STATEMENT, "authorized_by": "REHEARSAL-ONLY (pytest fixture)",
            "acknowledge_no_retuning_after_test": True, "acknowledge_prior_integrity_reads_disclosed": True}
    apath = proj / "rehearsal_authorization.json"
    apath.write_text(json.dumps(auth), encoding="utf-8")
    return proj, mpath, apath, locked, m


def test_full_rehearsal_refusals_preflight_dry_run_execution_write_protection_and_analysis(project, capsys):
    proj, mpath, apath, locked, m = project
    out_root = proj / "results_final_test"
    guard.install(extra_protected=[locked])
    try:
        with pytest.raises(guard.ProtectedFinalTestAccess):               # the synthetic locked file is protected until explicitly authorised
            locked.read_bytes()
        guard.violations.clear()
        # 1. no authorization => refusal; nothing created
        assert ft.evaluate(mpath, None, out_root, dry_run=False, root=proj, verify_history=False) == 2
        assert not out_root.exists()
        # 2. preflight and dry-run read no locked data and create nothing
        assert ft.evaluate(mpath, None, out_root, dry_run=False, root=proj, verify_history=False, preflight=True) == 0
        assert ft.evaluate(mpath, apath, out_root, dry_run=True, root=proj, verify_history=False) == 0
        assert not out_root.exists() and not guard.violations
        # 3. a tampered locked file is refused BEFORE any evaluation
        with guard.authorized(locked):
            saved = locked.read_bytes()
            locked.write_bytes(saved + b"\n999,0,0,tcp,-,FIN,Normal,0\n")
        with pytest.raises(SystemExit, match="REFUSED"):
            ft.evaluate(mpath, apath, out_root, dry_run=False, root=proj, verify_history=False)
        assert not list(out_root.rglob("final_test_result.json")) if out_root.exists() else True
        with guard.authorized(locked):
            locked.write_bytes(saved)
        # 4. the one-time evaluation
        assert ft.evaluate(mpath, apath, out_root, dry_run=False, root=proj, verify_history=False) == 0
        results = sorted(out_root.glob("*/*/seed_*/final_test_result.json"))
        assert len(results) == 4 and (out_root / "ledger.jsonl").exists()
        for p in results:
            r = json.loads(p.read_text(encoding="utf-8"))
            rec = next(x for x in m["runs"] if x["run_id"] == r["run_id"])
            assert r["final_test_manifest_sha256"] == m["manifest_sha256"] and r["checkpoint_sha256"] == {"best": rec["best_checkpoint_sha256"], "last": rec["last_checkpoint_sha256"]}
            assert r["preprocessor_sha256"] == rec["preprocessor_sha256"] and r["thresholds_from_calibration_partition"] == rec["thresholds"]
            assert r["best"]["primary"]["threshold"] == rec["thresholds"]["best_primary"] and set(r["best"]["targets"]) == {"1pct", "5pct", "15pct"}
            assert r["test_rows"] == 1000 and "not_in_reference" in r["overlap_controlled"]
        assert not guard.violations
        # 5. write protection: a second evaluation is refused and cannot overwrite anything
        before = {p: ft.sha256_file(p) for p in results}
        assert ft.evaluate(mpath, apath, out_root, dry_run=False, root=proj, verify_history=False) == 2
        assert before == {p: ft.sha256_file(p) for p in results}
        # 6. the frozen analysis runs on the rehearsal outputs
        led = proj / "ledgers"
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "final_test" / "analyze_final_test.py"), "--results", str(out_root), "--out", str(led)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-500:]
        c = pd.read_csv(led / "ledger_final_test_paired_contrasts.csv")
        assert ((c.contrast == "reference - clean_fedavg") & (c.metric == "roc_auc")).any()
        assert (led / "ledger_fpr_shift.csv").exists() and (led / "ledger_overlap_controlled.csv").exists()
    finally:
        guard._extra_protected.discard(guard._norm(locked))
        guard.violations.clear()
    # 7. nothing was written under the real repository's historical results trees
    assert not (ROOT / "results_final_test").exists()
