"""Locked final-test operation: authorization, manifest/hash locks, completeness, one-time evaluation."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from orchestrator import finalize_run  # noqa: E402
from p6c_common import code_fingerprint, manifest_hash, sha256_file, verify_run_dir  # noqa: E402
from src.config import Config  # noqa: E402
from src.experiment import run_experiment  # noqa: E402

FINAL = ROOT / "scripts" / "phase6c" / "final_test_evaluate.py"
STATEMENT = "I authorize one-time final-test evaluation of the frozen configurations"
ARTIFACTS = ["resolved_config.yaml", "round_metrics.csv", "network_metrics.csv", "aggregation_diagnostics.csv",
             "final_validation_metrics.json", "threshold_diagnostics.json", "run_metadata.json",
             "metric_accounting.json", "best_model_state.pt", "last_model_state.pt"]


def _frame(n, seed):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    return pd.DataFrame({
        "id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y,
        "proto": rng.choice(["tcp", "udp"], n), "service": rng.choice(["-", "http"], n),
        "state": rng.choice(["FIN", "CON"], n), "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y,
    })


@pytest.fixture()
def frozen(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "configs" / "phase6c").mkdir(parents=True)
    _frame(1500, 31).to_csv(tmp_path / "data" / "train.csv", index=False)
    _frame(300, 77).to_csv(tmp_path / "data" / "test.csv", index=False)
    out = tmp_path / "results_phase6c" / "unsw" / "arm" / "seed_12"
    cfg = Config()
    cfg.data.train_csv = str(tmp_path / "data" / "train.csv")
    cfg.data.test_csv = ""
    cfg.data.validation_split = "group_disjoint"
    cfg.data.validation_three_way = True
    cfg.data.enable_calibrated_evaluation = False
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 8, 6, 2
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.privacy.mode = "none"
    cfg.routing.trace_mode = "matched"
    cfg.experiment.output_dir = str(tmp_path / "out")
    cfg.experiment.exact_output_dir = str(out)
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    cfg.experiment.seed = 12
    run_experiment(cfg)
    test_csv = tmp_path / "data" / "test.csv"
    run = {"run_id": "unsw__arm__seed12", "order": 1, "dataset": "unsw", "arm": "arm", "seed": 12,
           "config": "configs/phase6c/unsw_arm.yaml", "config_sha256": "c" * 64, "out_dir": "results_phase6c/unsw/arm/seed_12"}
    (tmp_path / "configs" / "phase6c" / "unsw_arm.yaml").write_text("x: 1\n", encoding="utf-8")
    manifest = {
        "schema": 1, "code_fingerprint": code_fingerprint(tmp_path), "seeds": [12], "rounds": 2,
        "datasets": {}, "arms": [{"arm": "arm", "group": "main", "description": "", "algorithm_version": "v", "compare_with": None}],
        "primary_contrasts": [], "n_runs": 1, "runs": [run], "required_artifacts": ARTIFACTS,
        "locked_test": {"unsw": {"path": "data/test.csv", "kind": "csv", "sha256": sha256_file(test_csv), "bytes": test_csv.stat().st_size}},
        "command": [], "verify_training_semantics": True,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    assert finalize_run(out, run, manifest, 1.0) == []
    return tmp_path, mpath, manifest, run, out


def call(tmp_path, mpath, *args):
    return subprocess.run([sys.executable, str(FINAL), "--manifest", str(mpath), "--root", str(tmp_path), *args],
                          capture_output=True, text=True, cwd=str(tmp_path))


def sign(tmp_path, manifest, **over):
    auth = {"manifest_sha256": manifest["manifest_sha256"], "authorized": True, "statement": STATEMENT,
            "authorized_by": "tester", "acknowledge_no_retuning_after_test": True}
    auth.update(over)
    path = tmp_path / "auth.json"
    path.write_text(json.dumps(auth), encoding="utf-8")
    return path


def test_training_run_directory_contains_no_test_artifacts_and_no_test_path(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    assert verify_run_dir(out, run, manifest) == []
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["test_data_loaded"] is False
    assert "final_test" not in " ".join(p.name for p in out.iterdir())
    (out / "final_test_metrics.json").write_text("{}", encoding="utf-8")
    assert any("test-evaluation artefacts" in p for p in verify_run_dir(out, run, manifest))


def test_refused_without_or_with_unsigned_authorization(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    assert call(tmp_path, mpath).returncode == 2
    template = tmp_path / "template.json"
    assert call(tmp_path, mpath, "--write-authorization-template", str(template)).returncode == 0
    assert json.loads(template.read_text())["authorized"] is False
    r = call(tmp_path, mpath, "--authorization", str(template))
    assert r.returncode == 2 and "authorization invalid" in r.stdout
    assert not (tmp_path / "results_phase6c" / "_final_test").exists()


@pytest.mark.parametrize("override", [
    {"manifest_sha256": "0" * 64}, {"statement": "yes"}, {"authorized_by": ""},
    {"acknowledge_no_retuning_after_test": False}, {"authorized": "true"},
])
def test_each_authorization_defect_is_refused(frozen, override):
    tmp_path, mpath, manifest, run, out = frozen
    r = call(tmp_path, mpath, "--authorization", str(sign(tmp_path, manifest, **override)))
    assert r.returncode == 2 and "REFUSED" in r.stdout
    assert not (tmp_path / "results_phase6c" / "_final_test").exists()


def test_refused_if_any_run_is_not_complete_and_verified(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    (out / "COMPLETE.json").unlink()
    r = call(tmp_path, mpath, "--authorization", str(sign(tmp_path, manifest)))
    assert r.returncode == 2 and "not complete and verified" in r.stdout


def test_refused_if_code_or_config_changed_after_locking(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    (tmp_path / "configs" / "phase6c" / "unsw_arm.yaml").write_text("x: 2\n", encoding="utf-8")
    r = call(tmp_path, mpath, "--authorization", str(sign(tmp_path, manifest)))
    assert r.returncode == 2 and "fingerprint" in r.stdout


def test_dry_run_checks_everything_without_reading_the_test_file(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    (tmp_path / "data" / "test.csv").unlink()           # a dry run must not need (or read) the test data
    r = call(tmp_path, mpath, "--authorization", str(sign(tmp_path, manifest)), "--dry-run")
    assert r.returncode == 0 and "No test data was read" in r.stdout
    assert not (tmp_path / "results_phase6c" / "_final_test").exists()


def test_refused_if_test_file_hash_differs_from_the_lock(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    with open(tmp_path / "data" / "test.csv", "a", encoding="utf-8") as handle:
        handle.write("0,0,0,tcp,-,FIN,Normal,0\n")
    r = call(tmp_path, mpath, "--authorization", str(sign(tmp_path, manifest)))
    assert r.returncode == 2 and "hash differs" in r.stdout
    assert not (tmp_path / "results_phase6c" / "_final_test").exists()


def test_authorized_evaluation_is_recorded_once_and_never_repeated(frozen):
    tmp_path, mpath, manifest, run, out = frozen
    auth = str(sign(tmp_path, manifest))
    r1 = call(tmp_path, mpath, "--authorization", auth)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    result_path = tmp_path / "results_phase6c" / "_final_test" / "unsw" / "arm" / "seed_12" / "final_test_result.json"
    result = json.loads(result_path.read_text())
    assert result["manifest_sha256"] == manifest["manifest_sha256"]
    assert result["test_file_hash"] == manifest["locked_test"]["unsw"]["sha256"]
    assert result["test_rows"] == 300
    assert set(result["checkpoint_sha256"]) == {"best", "last"}
    assert result["best_checkpoint"]["primary_threshold"]["roc_auc"] > 0.5
    assert set(result["best_checkpoint"]["targets"]) == {"1pct", "5pct", "15pct"}
    assert result["duplicate_controlled"]["rows"] + result["duplicate_controlled"]["excluded_rows"] == 300
    # thresholds were those chosen on the calibration partition during training, not on the test set
    fin = json.loads((out / "final_validation_metrics.json").read_text())
    assert result["thresholds_from_calibration_partition"]["best_primary"] == fin["selected_operating_point"]["threshold"]
    ledger = (tmp_path / "results_phase6c" / "_final_test" / "ledger.jsonl").read_text().splitlines()
    assert len(ledger) == 1 and json.loads(ledger[0])["run_id"] == run["run_id"]
    before = sha256_file(result_path)
    r2 = call(tmp_path, mpath, "--authorization", auth)
    assert r2.returncode == 0 and "0 newly evaluated, 1 already" in r2.stdout
    assert sha256_file(result_path) == before
    assert len((tmp_path / "results_phase6c" / "_final_test" / "ledger.jsonl").read_text().splitlines()) == 1


def test_training_orchestrator_never_calls_the_final_test_operation():
    text = (ROOT / "scripts" / "phase6c" / "orchestrator.py").read_text(encoding="utf-8")
    assert "final_test_evaluate" not in text.replace("(see final_test_evaluate.py, a separate operation)", "")
    ps = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "scripts" / "phase6c").glob("*.ps1"))
    assert "final_test_evaluate" not in ps
