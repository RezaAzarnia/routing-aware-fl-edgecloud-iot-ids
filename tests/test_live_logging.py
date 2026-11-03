"""Live per-round logging: complete records, zero effect on results, read-only monitor."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
LIVE_DIR = ROOT / "scripts" / "live"
RUN_ONE = ROOT / "scripts" / "phase6c" / "run_one.py"
MONITOR = LIVE_DIR / "live_monitor.py"


def make_config(tmp_path: Path, device: str = "cpu") -> Path:
    from src.config import Config

    rng = np.random.default_rng(5)
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
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 8, 6, 4
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.attack.attack_type, cfg.attack.malicious_fraction = "sign_flip", 0.34
    cfg.attack.assignment = "exposure_controlled"
    cfg.routing.trace_mode = "matched"
    cfg.experiment.output_dir = str(tmp_path / "unused")
    cfg.experiment.create_plots = False
    cfg.experiment.device = device
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg.to_dict()), encoding="utf-8")
    return path


def run(config: Path, out: Path, live: bool):
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.pop("IOTFL_LIVE", None)
    if live:
        env["IOTFL_LIVE"] = "1"
        env["PYTHONPATH"] = str(LIVE_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, str(RUN_ONE), "--config", str(config), "--seed", "7", "--out", str(out)],
                          capture_output=True, text=True, env=env, cwd=str(ROOT))


def test_live_logging_is_complete_and_does_not_change_any_result(tmp_path):
    config = make_config(tmp_path)
    plain, live = tmp_path / "plain", tmp_path / "live"
    r1, r2 = run(config, plain, False), run(config, live, True)
    assert r1.returncode == 0, r1.stderr[-800:]
    assert r2.returncode == 0, r2.stderr[-800:]
    assert not (plain / "live_progress.jsonl").exists() and "[LIVE]" not in r1.stderr
    rows = [json.loads(l) for l in (live / "live_progress.jsonl").read_text().splitlines()]
    assert [r["round"] for r in rows] == [0, 1, 2, 3, 4]
    for key in ("run", "device", "rounds_total", "pct", "train_loss", "val_f1", "val_roc_auc", "val_fpr",
                "round_seconds", "elapsed_s", "eta_s", "t_utc"):
        assert key in rows[-1], key
    assert rows[0]["train_loss"] is None and rows[-1]["train_loss"] is not None
    assert rows[-1]["pct"] == 100.0 and rows[-1]["eta_s"] == 0.0
    assert all(rows[i]["elapsed_s"] <= rows[i + 1]["elapsed_s"] for i in range(4))
    assert r2.stderr.count("[LIVE]") == 5 and "ETA" in r2.stderr
    # logged loss equals the mean local loss recorded by the run itself
    metrics = pd.read_csv(live / "round_metrics.csv")
    for r in rows[1:]:
        assert abs(r["train_loss"] - metrics.loc[metrics["round"] == r["round"], "mean_train_loss"].iloc[0]) < 1e-9
        assert abs(r["val_roc_auc"] - metrics.loc[metrics["round"] == r["round"], "val_roc_auc"].iloc[0]) < 1e-12
    # the hook must not change a single number of the experiment
    a, b = pd.read_csv(plain / "round_metrics.csv"), metrics
    skip = {"round_seconds", "mean_local_train_seconds"}
    cols = [c for c in a.columns if c not in skip and pd.api.types.is_numeric_dtype(a[c])]
    assert len(cols) > 50
    for c in cols:
        assert np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), equal_nan=True, atol=0, rtol=0), c
    assert (plain / "best_model_state.pt").read_bytes() == (live / "best_model_state.pt").read_bytes()


def test_live_hook_is_inactive_without_the_environment_variable(tmp_path):
    config = make_config(tmp_path)
    env = dict(os.environ, PYTHONPATH=str(LIVE_DIR))
    env.pop("IOTFL_LIVE", None)
    r = subprocess.run([sys.executable, str(RUN_ONE), "--config", str(config), "--seed", "7", "--out", str(tmp_path / "o")],
                       capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert r.returncode == 0 and "[LIVE]" not in r.stderr and not (tmp_path / "o" / "live_progress.jsonl").exists()


def test_monitor_is_read_only_and_reports_progress(tmp_path):
    results = tmp_path / "results_phase6c"
    run_dir = results / "unsw" / "reference" / "seed_12"
    run_dir.mkdir(parents=True)
    (results / "_state").mkdir()
    manifest = {"runs": [
        {"run_id": "unsw__reference__seed12", "order": 1, "dataset": "unsw", "arm": "reference", "seed": 12, "out_dir": "results_phase6c/unsw/reference/seed_12"},
        {"run_id": "unsw__corrected__seed12", "order": 2, "dataset": "unsw", "arm": "corrected", "seed": 12, "out_dir": "results_phase6c/unsw/corrected/seed_12"}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (results / "_state" / "active.json").write_text(json.dumps({"run_id": "unsw__reference__seed12", "order": 1}), encoding="utf-8")
    with open(run_dir / "live_progress.jsonl", "w", encoding="utf-8") as handle:
        for r in range(3):
            handle.write(json.dumps({"round": r, "rounds_total": 30, "pct": 10.0 * r, "device": "cpu", "elapsed_s": 20 + r,
                                     "eta_s": 100 - 10 * r, "train_loss": None if r == 0 else 0.5, "val_f1": 0.8 + 0.01 * r,
                                     "val_roc_auc": 0.9, "val_fpr": 0.15, "round_seconds": 3.5}) + "\n")
        handle.write('{"round": 3, "rounds_to')                         # a half-written last line must be tolerated
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    r = subprocess.run([sys.executable, str(MONITOR), "--root", str(tmp_path), "--manifest", str(tmp_path / "manifest.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "unsw__reference__seed12" in r.stdout and "round 2/30" in r.stdout and "ETA" in r.stdout
    assert "0/2 verified complete" in r.stdout
    assert before == sorted(str(p) for p in tmp_path.rglob("*"))        # nothing created or changed


def test_locked_manifest_fingerprint_is_unaffected_by_the_live_tooling(phase6c_tree):
    sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
    from p6c_common import code_fingerprint, load_manifest

    manifest = load_manifest(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json")
    assert code_fingerprint(phase6c_tree) == manifest["code_fingerprint"]
