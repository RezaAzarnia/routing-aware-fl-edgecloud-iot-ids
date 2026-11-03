"""Phase 9C: final-test evaluation pathway v2 and the protection of locked test files.
Uses ONLY synthetic fixtures and training/validation artefacts. No locked test file is opened, hashed or inspected by these tests."""
import ast
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_final_test as aft  # noqa: E402
import final_test_v2 as ft  # noqa: E402
import protected_access_guard as guard  # noqa: E402
from test_phase7_guard import make_config, run  # noqa: E402

SCRIPT = ROOT / "scripts" / "final_test" / "final_test_v2.py"


# ------------------------------------------------------------------ guard
def test_guard_is_active_in_the_normal_test_session_and_blocks_locked_files_without_touching_them():
    for path in (ROOT / "data" / "UNSW_NB15_testing-set.csv", ROOT / "data" / "CICIoT2023" / "prepared_verified_v2_filegroup" / "test.csv.gz",
                 ROOT / "data" / "CICIoT2023" / "prepared_verified_v2_filegroup" / "test_provenance.csv.gz"):
        assert guard.is_protected(path)
        with pytest.raises(guard.ProtectedFinalTestAccess):
            open(path, "rb")                       # raises BEFORE any OS call: the file is never opened
        with pytest.raises(guard.ProtectedFinalTestAccess):
            pd.read_csv(path)
        with pytest.raises(guard.ProtectedFinalTestAccess):
            path.read_bytes()
    guard.violations.clear()                       # these violations were provoked on purpose


def test_guard_does_not_block_training_files_or_same_named_files_elsewhere(tmp_path):
    assert not guard.is_protected(ROOT / "data" / "UNSW_NB15_training-set.csv")
    assert not guard.is_protected(ROOT / "data" / "CICIoT2023" / "prepared_verified_v2_filegroup" / "train.csv.gz")
    other = tmp_path / "test.csv.gz"
    other.write_bytes(b"x")
    assert not guard.is_protected(other) and other.read_bytes() == b"x"


def test_guard_authorization_is_explicit_scoped_and_reverts(tmp_path):
    f = tmp_path / "secret.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    guard.install(extra_protected=[f])
    try:
        assert f.exists() and f.stat().st_size > 0        # metadata is allowed
        with pytest.raises(guard.ProtectedFinalTestAccess):
            f.read_text()
        with guard.authorized(f):
            assert f.read_text().startswith("a,b")
        with pytest.raises(guard.ProtectedFinalTestAccess):
            f.read_text()
    finally:
        guard._extra_protected.discard(guard._norm(f))
        guard.violations.clear()


def test_locked_file_tests_are_excluded_from_ordinary_runs():
    ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "authorized_integrity" in ini and 'addopts = -m "not authorized_integrity"' in ini
    for name in ("test_phase5_validation.py", "test_data_integrity_ciciot.py"):
        src = (ROOT / "tests" / name).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            text = ast.get_source_segment(src, fn) or ""
            touches_locked = "UNSW_NB15_testing-set.csv" in text or "test.csv.gz" in text or "test_provenance" in text
            if "authorized(" in text:
                assert any("authorized_integrity" in ast.unparse(d) for d in fn.decorator_list), fn.name
            elif touches_locked and "AUTHORIZED" not in fn.name and fn.name.startswith("test_"):
                pytest.fail(f"{name}::{fn.name} appears to reference a locked test file without the authorised marker")


# ------------------------------------------------------------------ static properties of the evaluation script
def test_evaluation_script_has_no_fit_no_threshold_search_no_optimisation():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    banned_calls = {"fit", "fit_transform", "partial_fit", "fit_predict", "minimize", "optimize", "select_decision_threshold", "train_test_split"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            assert name not in banned_calls, f"banned call {name} in final_test_v2.py"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            assert "select_decision_threshold" not in names
    src = SCRIPT.read_text(encoding="utf-8")
    assert "preprocessor_output" in src and src.count("load_test=False") >= 1      # equivalence check refits from TRAINING data only
    assert "load_test=True" not in src                                             # the evaluation never uses the training-time loader for test data


def test_locked_files_are_opened_only_inside_authorized_blocks():
    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    funcs = {n.name: ast.get_source_segment(src, n) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "guard.authorized" in funcs["read_locked"] and "read_bytes" in funcs["read_locked"]
    for name, text in funcs.items():
        if name != "read_locked":
            assert ".read_bytes(" not in text, name


# ------------------------------------------------------------------ synthetic end-to-end
def _synthetic_test_frame(n=900, seed=5):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    return pd.DataFrame({
        "id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y,
        "proto": rng.choice(["tcp", "udp", "icmp"], n), "service": rng.choice(["-", "http"], n), "state": rng.choice(["FIN", "CON"], n),
        "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y})


@pytest.fixture(scope="module")
def synthetic_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ft_v2")
    cfg = make_config(tmp, min_real_updates=0)
    out = tmp / "run"
    run(cfg, out)
    fin = json.loads((out / "final_validation_metrics.json").read_text(encoding="utf-8"))
    sel = fin["selected_operating_point"]
    rec = {"run_id": "unsw__synthetic__seed7", "source": "synthetic", "dataset": "unsw", "arm": "synthetic", "seed": 7, "run_dir": "run",
           "best_checkpoint_sha256": ft.sha256_file(out / "best_model_state.pt"), "last_checkpoint_sha256": ft.sha256_file(out / "last_model_state.pt"),
           "preprocessor_sha256": ft.sha256_file(out / "preprocessor.joblib"), "best_round": fin["best_round"],
           "thresholds": {"best_primary": sel["threshold"], "last_primary": fin["last_round_selection_partition"]["threshold"],
                          "targets": {k: v["calibration_partition"]["threshold"] for k, v in fin["threshold_diagnostics"].items()}},
           "calibration_reference": {"fpr": sel.get("calibration_fpr"), "recall": sel.get("calibration_recall_adr"), "constraint_feasible": sel.get("constraint_feasible")}}
    return tmp, out, rec, fin


def test_saved_preprocessor_path_equals_the_training_pipeline_without_refitting(synthetic_run, monkeypatch):
    import joblib
    from sklearn.compose import ColumnTransformer

    from src.config import Config
    from src.data import load_dataset

    tmp, out, rec, fin = synthetic_run
    test_frame = _synthetic_test_frame()
    test_path = tmp / "synthetic_test.csv"
    test_frame.to_csv(test_path, index=False)
    cfg = Config.from_yaml(out / "resolved_config.yaml")
    ref_cfg = Config.from_yaml(out / "resolved_config.yaml")
    ref_cfg.data.test_csv = str(test_path)
    bundle = load_dataset(ref_cfg.data, seed=7, load_test=True)            # reference: the training-time loader (refits on TRAIN only)
    prep = joblib.load(out / "preprocessor.joblib")

    def boom(*a, **k):
        raise AssertionError("the evaluation path must never fit a preprocessor")

    monkeypatch.setattr(ColumnTransformer, "fit", boom)
    monkeypatch.setattr(ColumnTransformer, "fit_transform", boom)
    X, y = ft.prepare_test_matrix(test_frame, cfg.data, prep)
    assert X.dtype == np.float32 and X.shape == bundle.X_test.shape
    assert np.array_equal(X, bundle.X_test) and np.array_equal(y, bundle.y_test)


def test_schema_mismatch_aborts_before_any_prediction(synthetic_run):
    import joblib

    from src.config import Config

    tmp, out, rec, fin = synthetic_run
    cfg = Config.from_yaml(out / "resolved_config.yaml")
    prep = joblib.load(out / "preprocessor.joblib")
    bad = _synthetic_test_frame().drop(columns=["dur"])
    with pytest.raises(ValueError, match="schema"):
        ft.prepare_test_matrix(bad, cfg.data, prep)
    extra = _synthetic_test_frame().assign(surprise=1.0)
    with pytest.raises(ValueError, match="schema"):
        ft.prepare_test_matrix(extra, cfg.data, prep)


def test_evaluate_one_uses_frozen_thresholds_exclusive_output_and_independent_metrics(synthetic_run):
    from sklearn.metrics import roc_auc_score

    from src.config import Config

    tmp, out, rec, fin = synthetic_run
    frame = _synthetic_test_frame()
    cfg = Config.from_yaml(out / "resolved_config.yaml")
    masks = ft.overlap_masks(frame, [pd.read_csv(tmp / "train.csv")], cfg.data)
    out_root = tmp / "results_final_test_synthetic"
    path = ft.evaluate_one(rec, tmp, frame, masks, out_root, manifest_sha="x" * 64)
    res = json.loads(path.read_text(encoding="utf-8"))
    assert res["schema"] == "final_test_result_v2" and res["test_rows"] == len(frame)
    assert res["best"]["primary"]["threshold"] == rec["thresholds"]["best_primary"]           # threshold exactly the recorded one
    assert res["last"]["primary"]["threshold"] == rec["thresholds"]["last_primary"]
    for k, t in rec["thresholds"]["targets"].items():
        assert res["best"]["targets"][k]["threshold"] == t
    probs = np.load(path.parent / "test_probabilities.npz")
    p, y = probs["best"].astype(float), frame["label"].to_numpy()
    m = res["best"]["primary"]
    pred = p >= rec["thresholds"]["best_primary"]
    assert m["tp"] == int((pred & (y == 1)).sum()) and m["fp"] == int((pred & (y == 0)).sum())      # single decision rule score >= threshold
    assert m["roc_auc"] == pytest.approx(roc_auc_score(y, p), abs=1e-6)
    assert (out_root / "ledger.jsonl").exists()
    with pytest.raises(FileExistsError):                    # exclusive create: a second evaluation can never overwrite
        ft.evaluate_one(rec, tmp, frame, masks, out_root, manifest_sha="x" * 64)


def test_tampered_checkpoint_or_preprocessor_is_refused(synthetic_run):
    tmp, out, rec, fin = synthetic_run
    bad = dict(rec, best_checkpoint_sha256="0" * 64)
    with pytest.raises(AssertionError):
        ft.evaluate_one(bad, tmp, _synthetic_test_frame(), {}, tmp / "r_bad", manifest_sha="x")
    bad = dict(rec, preprocessor_sha256="0" * 64)
    with pytest.raises(AssertionError):
        ft.evaluate_one(bad, tmp, _synthetic_test_frame(), {}, tmp / "r_bad2", manifest_sha="x")


# ------------------------------------------------------------------ gating
def _manifest(tmp_path, locked=None):
    m = {"schema": ft.SCHEMA, "plan": ft.PLAN, "sources": {}, "runs": [], "n_runs": 0, "locked_test": locked or {}, "protected_reference_files": {},
         "evaluation_code": {"globs": ft.EVAL_GLOBS, "fingerprint": ft.code_fingerprint(ROOT, ft.EVAL_GLOBS)}}
    m["manifest_sha256"] = ft.manifest_hash(m)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(m), encoding="utf-8")
    return m, path


def _auth(m, **over):
    a = {"manifest_sha256": m["manifest_sha256"], "plan": ft.PLAN, "authorized": True, "statement": ft.AUTH_STATEMENT, "authorized_by": "pytest",
         "acknowledge_no_retuning_after_test": True, "acknowledge_prior_integrity_reads_disclosed": True}
    a.update(over)
    return a


def test_refuses_without_valid_authorization(tmp_path):
    m, path = _manifest(tmp_path)
    assert "no authorization file" in ft.refusal_reasons(m, None, tmp_path / "out", ROOT, verify_history=False)
    for key, val in (("authorized", False), ("statement", "yes"), ("authorized_by", ""), ("acknowledge_no_retuning_after_test", False),
                     ("acknowledge_prior_integrity_reads_disclosed", False), ("manifest_sha256", "0" * 64), ("plan", "other")):
        assert ft.refusal_reasons(m, _auth(m, **{key: val}), tmp_path / "out", ROOT, verify_history=False), key
    assert ft.refusal_reasons(m, _auth(m), tmp_path / "out", ROOT, verify_history=False) == []


def test_refuses_modified_manifest_changed_evaluation_code_and_unsafe_output_dirs(tmp_path):
    m, path = _manifest(tmp_path)
    tampered = dict(m, n_runs=5)
    assert any("modified" in r for r in ft.refusal_reasons(tampered, _auth(m), tmp_path / "out", ROOT, verify_history=False))
    moved = json.loads(json.dumps(m))
    moved["evaluation_code"]["fingerprint"] = "0" * 64
    moved["manifest_sha256"] = ft.manifest_hash(moved)
    assert any("evaluation-code" in r for r in ft.refusal_reasons(moved, _auth(moved), tmp_path / "out", ROOT, verify_history=False))
    assert any("historical" in r for r in ft.refusal_reasons(m, _auth(m), ROOT / "results_phase6c" / "_final_test", ROOT, verify_history=False))
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "x").write_text("1")
    assert any("not empty" in r for r in ft.refusal_reasons(m, _auth(m), busy, ROOT, verify_history=False))


def test_dry_run_reads_no_test_data(tmp_path):
    locked = {"unsw": {"path": "data/UNSW_NB15_testing-set.csv", "kind": "csv", "sha256": "0" * 64},
              "ciciot": {"path": "data/CICIoT2023/prepared_verified_v2_filegroup/test.csv.gz", "kind": "gzip_csv", "content_sha256": "0" * 64}}
    m, path = _manifest(tmp_path, locked)
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps(_auth(m)), encoding="utf-8")
    before = len(guard.violations)
    assert ft.evaluate(path, auth, tmp_path / "out", dry_run=True, verify_history=False) == 0
    assert len(guard.violations) == before and not (tmp_path / "out").exists()
    assert ft.evaluate(path, None, tmp_path / "out", dry_run=True, verify_history=False) == 2


def test_preflight_checks_everything_except_the_signature_and_reads_no_test_data(tmp_path, capsys):
    locked = {"unsw": {"path": "data/UNSW_NB15_testing-set.csv", "kind": "csv", "sha256": "0" * 64}}
    m, path = _manifest(tmp_path, locked)
    before = len(guard.violations)
    assert ft.evaluate(path, None, tmp_path / "out", dry_run=False, verify_history=False, preflight=True) == 0
    assert "NOT SIGNED" in capsys.readouterr().out and len(guard.violations) == before and not (tmp_path / "out").exists()
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["n_runs"] = 3
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="modified after it was locked"):          # load_manifest refuses a tampered manifest outright
        ft.evaluate(path, None, tmp_path / "out", dry_run=False, verify_history=False, preflight=True)


# ------------------------------------------------------------------ overlap coverage for both datasets
def test_overlap_masks_cover_both_dataset_types():
    from src.config import Config

    data_cfg = Config().data
    rng = np.random.default_rng(1)
    test = pd.DataFrame({"id": range(8), "a": [1.0, 1.0, 2.0, 3.0, 4.0, 4.0, 5.0, 6.0], "b": ["x", "x", "y", "y", "z", "z", "w", "w"], "attack_cat": ["n"] * 8,
                         "label": [0, 0, 1, 1, 0, 0, 1, 1]})
    train = pd.DataFrame({"id": range(3), "a": [2.0, 5.0, 9.0], "b": ["y", "w", "q"], "attack_cat": ["n"] * 3, "label": [1, 1, 0]})
    masks = ft.overlap_masks(test, [train], data_cfg)
    assert masks["not_in_reference"].tolist() == [True, True, False, True, True, True, False, True]
    assert masks["unique_within_test"].tolist() == [True, False, True, True, True, False, True, True]
    assert masks["not_in_reference_and_unique"].sum() == 4
    # purely numeric CIC-style frame
    cic = pd.DataFrame({"f1": [1.0, 1.0, 2.0], "f2": [0.0, 0.0, 1.0], "label": [1, 1, 0]})
    m2 = ft.overlap_masks(cic, [pd.DataFrame({"f1": [2.0], "f2": [1.0], "label": [0]})], data_cfg)
    assert m2["unique_within_test"].tolist() == [True, False, True] and m2["not_in_reference"].tolist() == [True, True, False]


# ------------------------------------------------------------------ frozen analysis on synthetic results
def test_analysis_script_produces_the_frozen_tables(tmp_path):
    res = tmp_path / "res"
    rng = np.random.default_rng(0)
    for ds in ("unsw", "ciciot"):
        for arm, base in (("reference", 0.95), ("corrected", 0.93), ("clean_fedavg", 0.95), ("scenario_fedavg_topk", 0.6), ("reference_gaussian", 0.9)):
            for seed in range(12, 17):
                auc = base + rng.normal(0, 0.003)
                cell = lambda a: {"threshold": 0.5, "tp": 5, "fp": 1, "fn": 1, "tn": 5, "roc_auc": a, "pr_auc": a, "f1": a, "recall_adr": a, "precision": a, "fpr": 0.2 if arm == "corrected" else 0.1}
                d = res / ds / arm / f"seed_{seed}"
                d.mkdir(parents=True)
                (d / "final_test_result.json").write_text(json.dumps({
                    "dataset": ds, "arm": arm, "seed": seed, "test_rows": 12, "test_benign": 6, "calibration_reference": {"fpr": 0.15},
                    "best": {"primary": cell(auc)}, "last": {"primary": cell(auc - 0.001)},
                    "overlap_controlled": {"not_in_reference": {"rows": 10, "best_primary": cell(auc), "last_primary": cell(auc)}}}), encoding="utf-8")
    out = tmp_path / "ledgers"
    assert aft.main.__call__ is not None
    sys.argv = ["analyze", "--results", str(res), "--out", str(out)]
    assert aft.main() == 0
    for name in ("per_run", "arm_summary", "paired_contrasts"):
        assert (out / f"ledger_final_test_{name}.csv").exists()
    c = pd.read_csv(out / "ledger_final_test_paired_contrasts.csv")
    row = c[(c.dataset == "unsw") & (c.contrast == "reference - scenario_fedavg_topk") & (c.checkpoint == "best") & (c.metric == "roc_auc")].iloc[0]
    assert row.n == 5 and row.n_first_better == 5 and row.p_exact_signflip == pytest.approx(0.0625)      # minimum exact p at n=5
    fl = pd.read_csv(out / "ledger_fpr_shift.csv")
    assert fl[fl.arm == "corrected"]["operational_flag_fpr_gt_0.25"].eq(False).all()
    assert (out / "ledger_overlap_controlled.csv").exists()


# ------------------------------------------------------------------ frozen manifest (present after the freeze step)
FROZEN = ROOT / "docs" / "final_test" / "FINAL_TEST_MANIFEST.json"


@pytest.mark.skipif(not FROZEN.exists(), reason="manifest not yet frozen")
def test_frozen_manifest_is_consistent_and_evaluation_code_is_unchanged():
    m = ft.load_manifest(FROZEN)                                        # raises if modified after freezing
    assert m["plan"] == ft.PLAN and m["n_runs"] == len(m["runs"]) == 280
    assert all(info["tag_matches_manifest"] for info in m["sources"].values())
    # The evaluation code is frozen at tag phase9e-frozen (commit 4224778); later branches (e.g. Phase 10) legitimately change src/, so verify the frozen tree.
    import shutil, subprocess, tempfile
    ok = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "phase9e-frozen"], capture_output=True, cwd=ROOT).returncode == 0
    if ok:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "archive", "--format=tar", "-o", str(Path(tmp) / "t.tar"), "phase9e-frozen"], check=True, cwd=ROOT)
            shutil.unpack_archive(str(Path(tmp) / "t.tar"), str(Path(tmp) / "tree"))
            assert ft.code_fingerprint(Path(tmp) / "tree", m["evaluation_code"]["globs"]) == m["evaluation_code"]["fingerprint"]
    else:
        assert ft.code_fingerprint(ROOT, m["evaluation_code"]["globs"]) == m["evaluation_code"]["fingerprint"]
    assert m["policy"]["thresholds"].startswith("recorded calibration-partition thresholds only")
    for rec in m["runs"]:
        assert not rec["run_dir"].startswith("results_final_test")
        thr = rec["thresholds"]
        assert 0.0 <= thr["best_primary"] <= 1.0 and 0.0 <= thr["last_primary"] <= 1.0
