"""Phase-6A regression tests: validation-only execution, network diagnostics that do
not change the simulator, and corrected privacy / aggregation metadata."""
import builtins
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.config import RoutingConfig
from src.experiment import _privacy_plan, run_experiment
from src.network import DynamicEdgeCloudNetwork


def _tiny_unsw_files(path: Path):
    rng = np.random.default_rng(11)
    n = 600
    y = rng.integers(0, 2, n)
    frame = pd.DataFrame({
        "id": np.arange(1, n + 1),
        "dur": rng.normal(0, 1, n) + 1.5 * y,
        "sbytes": rng.normal(0, 3, n) + 2 * y,
        "proto": rng.choice(["tcp", "udp"], n),
        "service": rng.choice(["-", "http"], n),
        "state": rng.choice(["FIN", "CON"], n),
        "attack_cat": np.where(y == 1, "Generic", "Normal"),
        "label": y,
    })
    frame.to_csv(path / "train.csv", index=False)


def _tiny_cfg(path: Path, test_path: str) -> Config:
    cfg = Config()
    cfg.data.train_csv = str(path / "train.csv")
    cfg.data.test_csv = test_path
    cfg.data.validation_split = "group_disjoint"
    cfg.data.enable_calibrated_evaluation = True  # must be ignored in validation-only mode
    cfg.fl.num_clients = 4
    cfg.fl.clients_per_round = 3
    cfg.fl.rounds = 2
    cfg.fl.local_epochs = 1
    cfg.fl.partition = "iid"
    cfg.fl.min_client_samples = 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.privacy.mode = "central_client"
    cfg.privacy.target_epsilon = 10.0
    cfg.failure.client_failure_probability = 0.4
    cfg.experiment.output_dir = str(path / "out")
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    cfg.experiment.seed = 3
    return cfg


def test_validation_only_never_opens_test_files_and_exports_no_test_outputs(tmp_path, monkeypatch):
    _tiny_unsw_files(tmp_path)
    sentinel = str(tmp_path / "SENTINEL_FINAL_TEST.csv")  # does not exist
    cfg = _tiny_cfg(tmp_path, sentinel)

    touched = []
    real_open = builtins.open
    real_read_csv = pd.read_csv

    def spy_open(file, *args, **kwargs):
        touched.append(str(file))
        return real_open(file, *args, **kwargs)

    def spy_read_csv(path, *args, **kwargs):
        touched.append(str(path))
        return real_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(pd, "read_csv", spy_read_csv)
    run_dir = run_experiment(cfg)
    monkeypatch.undo()

    assert not any("SENTINEL_FINAL_TEST" in t for t in touched)
    names = {p.name for p in Path(run_dir).iterdir()}
    forbidden = {n for n in names if "final_test" in n or "calibrated" in n or "standard_operating" in n
                 or n.startswith("test_predictions") or "per_attack" in n}
    assert not forbidden, forbidden
    final = json.loads((Path(run_dir) / "final_validation_metrics.json").read_text())
    assert final["protocol"] == "validation_only" and final["test_data_loaded"] is False
    summary = json.loads((Path(run_dir) / "dataset_summary.json").read_text())
    assert summary["testing_rows_used_standard_benchmark"] == 0
    meta = json.loads((Path(run_dir) / "run_metadata.json").read_text())
    assert meta["test_data_loaded"] is False and meta["validation_only"] is True
    assert (Path(run_dir) / "confusion_matrix_validation.csv").exists()


def test_run_metadata_records_median_privacy_and_imputation_semantics(tmp_path):
    _tiny_unsw_files(tmp_path)
    cfg = _tiny_cfg(tmp_path, "")
    run_dir = Path(run_experiment(cfg))
    meta = json.loads((run_dir / "run_metadata.json").read_text())
    assert "mean of the two middle order statistics" in meta["median_convention"]
    assert meta["privacy"]["subsampling_amplification_valid"] is False
    assert meta["privacy"]["epsilon_is_certified_guarantee"] is False
    assert meta["privacy"]["selection_mechanism"] == "deterministic_top_k_by_route_score"
    assert meta["privacy"]["release_count"] >= 1
    assert "not" in meta["missing_update_handling"]["terminology"] or "no information" in meta["missing_update_handling"]["terminology"]
    assert "imputation" in meta["missing_update_handling"]["terminology"]
    rounds = pd.read_csv(run_dir / "round_metrics.csv")
    for col in ("imputed_clients", "real_weight_share", "surrogate_weight_share", "mean_update_delivered"):
        assert col in rounds.columns
    agg = pd.read_csv(run_dir / "aggregation_diagnostics.csv")
    assert {"raw_weight", "applied_weight_share"} <= set(agg.columns)
    net = pd.read_csv(run_dir / "network_metrics.csv")
    assert {"expected_pdr", "delivery_draw", "failure_reason", "explicit_failure_draw"} <= set(net.columns)


def test_privacy_plan_never_claims_amplification_or_certification():
    for routing in (True, False):
        for mode in ("central_client", "none"):
            cfg = Config()
            cfg.privacy.mode = mode
            cfg.routing.enabled = routing
            plan = _privacy_plan(cfg)
            assert plan["subsampling_amplification_valid"] is False
            assert plan["poisson_subsampling_assumption_satisfied"] is False
            assert plan["epsilon_is_certified_guarantee"] is False
    cfg = Config()
    cfg.routing.enabled = True
    assert _privacy_plan(cfg)["selection_mechanism"] == "deterministic_top_k_by_route_score"
    cfg.routing.enabled = False
    assert _privacy_plan(cfg)["selection_mechanism"] == "uniform_without_replacement_fixed_size"


def _reference_transfer(net, client_id, update_bytes):
    """Verbatim copy of the ORIGINAL (7c75b2d) simulate_transfer logic."""
    decision = net.decisions[client_id]
    packets_sent = net.cfg.packets_per_update
    packets_received = int(net.rng.binomial(packets_sent, decision.expected_pdr))
    pdr = packets_received / max(packets_sent, 1)
    delivered = bool(net.rng.random() < decision.expected_pdr)
    serialization_ms = update_bytes * 8 / (decision.bandwidth_mbps * 1e6) * 1000
    jitter_ms = abs(float(net.rng.normal(0, max(1.0, decision.latency_ms * 0.05))))
    end_to_end_ms = decision.latency_ms + serialization_ms + jitter_ms
    delivered_bytes = update_bytes if delivered else 0
    efficiency = delivered_bytes * 8 / (end_to_end_ms / 1000) / 1e6 if end_to_end_ms > 0 else 0.0
    path_stability = 0.5 * decision.stability + 0.5 * decision.route_persistence
    return {"end_to_end_delay_ms": end_to_end_ms, "pdr": pdr, "update_delivered": delivered,
            "packets_received": packets_received, "path_stability": path_stability,
            "transfer_efficiency_mbps": efficiency}


def test_network_diagnostics_do_not_change_simulator_behaviour():
    cfg = RoutingConfig()
    new = DynamicEdgeCloudNetwork(12, cfg, seed=77)
    old = DynamicEdgeCloudNetwork(12, cfg, seed=77)
    for _ in range(6):
        new.update_round(True)
        old.update_round(True)
        for client in new.select_clients(8):
            got = new.simulate_transfer(client, 120_000)
            want = _reference_transfer(old, client, 120_000)
            for key, value in want.items():
                assert got[key] == value, key
            # diagnostics: expected pdr and the independent delivery draw are consistent
            assert got["update_delivered"] == (got["delivery_draw"] < got["expected_pdr"])
            assert got["packets_lost"] == cfg.packets_per_update - got["packets_received"]


def test_delivery_is_independent_of_packet_level_pdr():
    """Documents the verified relationship: update_delivered is its own Bernoulli draw and is
    not derived from packets_received/pdr."""
    cfg = RoutingConfig()
    net = DynamicEdgeCloudNetwork(30, cfg, seed=5)
    rows = []
    for _ in range(40):
        net.update_round(True)
        for client in range(30):
            rows.append(net.simulate_transfer(client, 100_000))
    frame = pd.DataFrame(rows)
    delivered = frame["update_delivered"].astype(bool)
    # perfect-PDR transfers that were nevertheless not delivered, and vice versa, both occur
    assert ((frame["pdr"] >= 0.95) & ~delivered).sum() > 0
    assert ((frame["pdr"] <= 0.80) & delivered).sum() > 0
