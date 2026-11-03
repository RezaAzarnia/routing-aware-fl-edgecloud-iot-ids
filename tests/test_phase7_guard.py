"""Phase 7 minimum-real-update guard: default-off identity, abstention semantics, determinism, Phase 6C lock intact."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN_ONE = ROOT / "scripts" / "phase6c" / "run_one.py"


def make_config(tmp_path: Path, **aggregation) -> Path:
    from src.config import Config

    rng = np.random.default_rng(11)
    n = 1800
    y = rng.integers(0, 2, n)
    pd.DataFrame({
        "id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y,
        "proto": rng.choice(["tcp", "udp"], n), "service": rng.choice(["-", "http"], n),
        "state": rng.choice(["FIN", "CON"], n), "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y,
    }).to_csv(tmp_path / "train.csv", index=False)
    cfg = Config()
    cfg.data.train_csv, cfg.data.test_csv = str(tmp_path / "train.csv"), ""
    cfg.data.validation_split, cfg.data.validation_three_way = "group_disjoint", True
    cfg.data.enable_calibrated_evaluation = False
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 10, 8, 6
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.attack.attack_type, cfg.attack.malicious_fraction = "sign_flip", 0.25
    cfg.attack.assignment = "exposure_controlled"
    cfg.routing.trace_mode = "matched"
    cfg.failure.enabled, cfg.failure.recovery_enabled, cfg.failure.client_failure_probability = True, True, 0.6
    cfg.experiment.output_dir = str(tmp_path / "unused")
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    raw = cfg.to_dict()
    raw["aggregation"].update(aggregation)
    path = tmp_path / f"cfg_{abs(hash(json.dumps(aggregation, sort_keys=True)))}.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def run(config: Path, out: Path):
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.pop("IOTFL_LIVE", None)
    r = subprocess.run([sys.executable, str(RUN_ONE), "--config", str(config), "--seed", "7", "--out", str(out)],
                       capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1200:]
    return pd.read_csv(out / "round_metrics.csv")


def numeric_equal(a: pd.DataFrame, b: pd.DataFrame, skip=("round_seconds", "mean_local_train_seconds")):
    cols = [c for c in a.columns if c in b.columns and c not in skip and pd.api.types.is_numeric_dtype(a[c])]
    assert len(cols) > 50
    for c in cols:
        assert np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), equal_nan=True, atol=0, rtol=0), c


def test_guard_is_inactive_by_default_and_when_never_binding(tmp_path):
    base = run(make_config(tmp_path, min_real_updates=0), tmp_path / "a")
    never = run(make_config(tmp_path, min_real_updates=1), tmp_path / "b")        # >=1 real update always satisfies it
    assert (base.loc[base["round"] >= 1, "aggregation_skipped"] == 0).all()
    assert (never.loc[never["round"] >= 1, "aggregation_skipped"] == 0).all()
    numeric_equal(base, never)
    assert (tmp_path / "a" / "best_model_state.pt").read_bytes() == (tmp_path / "b" / "best_model_state.pt").read_bytes()
    assert (tmp_path / "a" / "last_model_state.pt").read_bytes() == (tmp_path / "b" / "last_model_state.pt").read_bytes()


def test_guard_abstains_exactly_when_too_few_real_updates(tmp_path):
    m = run(make_config(tmp_path, min_real_updates=5), tmp_path / "g")
    m = m[m["round"] >= 1].reset_index(drop=True)                                 # round 0 is the initial evaluation
    low = (m["received_updates"] > 0) & (m["received_updates"] < 5)
    assert low.any() and (~low).any(), "test config must exercise both branches"
    assert (m.loc[low, "aggregation_skipped"] == 1).all() and (m.loc[~low, "aggregation_skipped"] == 0).all()
    assert (m.loc[low, "kept_updates"] == 0).all() and (m.loc[low, "recovered_clients"] == 0).all()
    assert (m.loc[low, "server_applied_update_l2_norm"] == 0).all()
    assert (m.loc[~low & (m["received_updates"] > 0), "kept_updates"] > 0).all()


def test_abstaining_every_round_never_changes_the_global_model(tmp_path):
    m = run(make_config(tmp_path, min_real_updates=99), tmp_path / "all")
    assert (m.loc[m["received_updates"] > 0, "aggregation_skipped"] == 1).all()
    assert m["val_roc_auc"].nunique() == 1                                       # model frozen at its initial weights (incl. round 0)
    m = m[m["round"] >= 1]
    assert (m["server_applied_update_l2_norm"].fillna(0) == 0).all()


def test_guarded_run_is_deterministic(tmp_path):
    cfg = make_config(tmp_path, min_real_updates=3)
    a, b = run(cfg, tmp_path / "r1"), run(cfg, tmp_path / "r2")
    numeric_equal(a, b)
    assert (tmp_path / "r1" / "last_model_state.pt").read_bytes() == (tmp_path / "r2" / "last_model_state.pt").read_bytes()


def test_negative_guard_is_rejected(tmp_path):
    from src.config import Config

    cfg = Config()
    cfg.aggregation.min_real_updates = -1
    with pytest.raises(ValueError):
        cfg.validate()


def test_phase6c_lock_is_reproducible_from_the_tagged_commit(tmp_path):
    """The locked Phase 6C fingerprint must still be reproducible from git tag phase6c-final-results."""
    tag = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "phase6c-final-results"], capture_output=True, text=True, cwd=ROOT)
    if tag.returncode != 0:
        pytest.skip("tag phase6c-final-results not present in this clone")
    archive = tmp_path / "p6c.tar"
    subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), "phase6c-final-results"], check=True, cwd=ROOT)
    dest = tmp_path / "p6c"
    dest.mkdir()
    shutil.unpack_archive(str(archive), str(dest))
    sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
    from p6c_common import code_fingerprint, load_manifest

    manifest = load_manifest(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json")
    assert code_fingerprint(dest) == manifest["code_fingerprint"]
