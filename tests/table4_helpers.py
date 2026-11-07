"""Shared helpers for the Table 4 v2 backward-compatibility fixtures (no test data; synthetic only)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUN_ONE = ROOT / "scripts" / "phase6c" / "run_one.py"
TIMING_COLUMNS = {"mean_local_train_seconds", "round_seconds"}


def network_golden() -> dict:
    """Deterministic fixture: route decisions, selection and one transfer per round for the historical
    configurations (routing enabled/disabled x sequential/matched traces)."""
    from src.config import Config
    from src.network import DynamicEdgeCloudNetwork

    out = {}
    for trace in ("sequential", "matched"):
        for enabled in (True, False):
            cfg = Config()
            cfg.routing.trace_mode = trace
            net = DynamicEdgeCloudNetwork(20, cfg.routing, seed=5)
            rounds = []
            for _ in range(4):
                dec = net.update_round(enabled)
                sel = net.select_clients(5) if enabled else list(range(5))
                tr = [net.simulate_transfer(c, 1000) for c in sel[:3]]
                rounds.append({
                    "edges": [dec[c].edge_id for c in range(20)],
                    "scores": [round(dec[c].score, 12) for c in range(20)],
                    "stability": [round(dec[c].stability, 12) for c in range(20)],
                    "selected": [int(c) for c in sel],
                    "delay": [round(float(t["end_to_end_delay_ms"]), 9) for t in tr],
                    "pdr": [round(float(t["pdr"]), 12) for t in tr],
                    "delivered": [bool(t["update_delivered"]) for t in tr],
                })
            out[f"{trace}|routing_enabled={enabled}"] = rounds
    return out


def make_config(tmp_path: Path, routing: dict | None = None, **extra) -> Path:
    from src.config import Config

    rng = np.random.default_rng(11)
    n = 1800
    y = rng.integers(0, 2, n)
    train = tmp_path / "train.csv"
    if not train.exists():
        pd.DataFrame({
            "id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y,
            "proto": rng.choice(["tcp", "udp"], n), "service": rng.choice(["-", "http"], n),
            "state": rng.choice(["FIN", "CON"], n), "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y,
        }).to_csv(train, index=False)
    cfg = Config()
    cfg.data.train_csv, cfg.data.test_csv = str(train), ""
    cfg.data.validation_split, cfg.data.validation_three_way = "group_disjoint", True
    cfg.data.enable_calibrated_evaluation = False
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 10, 8, 5
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "fedavg"
    cfg.attack.attack_type, cfg.attack.malicious_fraction = "sign_flip", 0.25
    cfg.attack.assignment = "exposure_controlled"
    cfg.routing.trace_mode = "matched"
    cfg.failure.enabled, cfg.failure.recovery_enabled, cfg.failure.client_failure_probability = True, False, 0.3
    cfg.experiment.output_dir = str(tmp_path / "unused")
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    raw = cfg.to_dict()
    raw["routing"].update(routing or {})
    for k, v in extra.items():
        raw[k].update(v)
    path = tmp_path / f"cfg_{abs(hash(json.dumps([routing, extra], sort_keys=True)))}.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def run_tiny(config: Path, out: Path, seed: int = 7) -> pd.DataFrame:
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.pop("IOTFL_LIVE", None)
    r = subprocess.run([sys.executable, str(RUN_ONE), "--config", str(config), "--seed", str(seed), "--out", str(out)],
                       capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-1500:]
    return pd.read_csv(out / "round_metrics.csv")


def e2e_signature(df: pd.DataFrame) -> dict:
    keep = [c for c in df.columns if c not in TIMING_COLUMNS and df[c].dtype.kind in "fi"]
    return {c: [None if pd.isna(v) else round(float(v), 10) for v in df[c]] for c in keep}


E2E_CASES = {
    "routing_enabled_topk": {},
    "routing_enabled_uniform_random": {"selection_policy": "uniform_random"},
    "routing_disabled_historical": {"enabled": False},
}
