"""run_one.py (the single-job entry point used by the runner) with a tiny real workload."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from orchestrator import finalize_run  # noqa: E402
from p6c_common import DEFAULT_REQUIRED_ARTIFACTS, code_fingerprint, manifest_hash, sha256_text_file, verify_run_dir  # noqa: E402
from src.config import Config  # noqa: E402


def test_run_one_creates_every_required_artifact_and_verifies(tmp_path):
    rng = np.random.default_rng(3)
    n = 1500
    y = rng.integers(0, 2, n)
    pd.DataFrame({
        "id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y,
        "proto": rng.choice(["tcp", "udp"], n), "service": rng.choice(["-", "http"], n),
        "state": rng.choice(["FIN", "CON"], n), "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y,
    }).to_csv(tmp_path / "train.csv", index=False)
    cfg = Config()
    cfg.data.train_csv = str(tmp_path / "train.csv")
    cfg.data.test_csv = ""
    cfg.data.validation_split = "group_disjoint"
    cfg.data.validation_three_way = True
    cfg.data.enable_calibrated_evaluation = False
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 8, 6, 2
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.attack.attack_type, cfg.attack.malicious_fraction = "sign_flip", 0.34
    cfg.attack.assignment = "exposure_controlled"
    cfg.routing.trace_mode = "matched"
    cfg.experiment.output_dir = str(tmp_path / "unused")
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    config_path = tmp_path / "configs" / "phase6c" / "unsw_arm.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(yaml.safe_dump(cfg.to_dict()), encoding="utf-8")

    out = tmp_path / "results_phase6c" / "unsw" / "arm" / "seed_12"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "phase6c" / "run_one.py"), "--config", str(config_path),
                        "--seed", "12", "--out", str(out)], capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    run = {"run_id": "unsw__arm__seed12", "order": 1, "dataset": "unsw", "arm": "arm", "seed": 12,
           "config": "configs/phase6c/unsw_arm.yaml", "config_sha256": sha256_text_file(config_path),
           "out_dir": "results_phase6c/unsw/arm/seed_12"}
    manifest = {"schema": 1, "code_fingerprint": code_fingerprint(tmp_path), "rounds": 2,
                "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS, "verify_training_semantics": True}
    manifest["manifest_sha256"] = manifest_hash(manifest)
    for name in DEFAULT_REQUIRED_ARTIFACTS:
        assert (out / name).exists(), name
    diag = json.loads((out / "phase6c_diagnostics.json").read_text())
    assert "diagnostics_error" not in diag, diag.get("diagnostics_error")
    assert "fairness" in diag and "participation" in diag
    record = json.loads((out / "run_record.json").read_text())
    assert record["seed"] == 12 and record["config_sha256"] == run["config_sha256"]
    meta = json.loads((out / "run_metadata.json").read_text())
    assert meta["seed"] == 12 and meta["test_data_loaded"] is False
    assert finalize_run(out, run, manifest, 2.0) == []
    assert verify_run_dir(out, run, manifest) == []
