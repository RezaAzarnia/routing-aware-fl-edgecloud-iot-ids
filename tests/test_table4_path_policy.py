"""Table 4 v2: independent path-assignment control. Default behaviour must be bit-identical to the pre-change code (golden fixtures
generated from the unmodified implementation), and the new switch must change ONLY the path assignment."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import table4_helpers as h  # noqa: E402
from src.config import Config  # noqa: E402
from src.network import DynamicEdgeCloudNetwork  # noqa: E402

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "path_policy_golden.json").read_text(encoding="utf-8"))


def test_default_config_value_is_historical():
    cfg = Config()
    assert cfg.routing.path_policy == "default"
    cfg.validate()


def test_network_decisions_match_pre_change_golden():
    assert json.loads(json.dumps(h.network_golden())) == GOLDEN["network"]


@pytest.mark.parametrize("case", list(h.E2E_CASES))
def test_end_to_end_signature_matches_pre_change_golden(tmp_path, case):
    cfg = h.make_config(tmp_path, routing=h.E2E_CASES[case])
    df = h.run_tiny(cfg, tmp_path / "run")
    assert h.e2e_signature(df) == GOLDEN["e2e"][case]


def test_explicit_routed_equals_default_when_routing_enabled():
    cfg = Config()
    cfg.routing.trace_mode = "matched"
    a = DynamicEdgeCloudNetwork(20, cfg.routing, seed=3)
    b = DynamicEdgeCloudNetwork(20, cfg.routing, seed=3)
    for _ in range(4):
        da, db = a.update_round(True), b.update_round(True, path_policy="routed")
        assert [d.edge_id for d in da.values()] == [d.edge_id for d in db.values()]
        assert [d.score for d in da.values()] == [d.score for d in db.values()]


def test_random_path_changes_only_edges_and_not_shared_generator():
    cfg = Config()
    cfg.routing.trace_mode = "matched"
    routed = DynamicEdgeCloudNetwork(20, cfg.routing, seed=3)
    rand = DynamicEdgeCloudNetwork(20, cfg.routing, seed=3)
    differs = False
    for _ in range(5):
        dr, dx = routed.update_round(True, "routed"), rand.update_round(True, "random")
        differs |= [d.edge_id for d in dr.values()] != [d.edge_id for d in dx.values()]
        # exogenous link state evolves identically: the random path stream never touches the shared generator
        for name in ("client_edge_latency", "client_edge_stability", "client_edge_security", "client_edge_bandwidth"):
            assert np.array_equal(getattr(routed, name), getattr(rand, name))
    assert differs
    # historical random paths DO perturb the exogenous evolution (shared generator) - documented reason for the new switch
    hist = DynamicEdgeCloudNetwork(20, cfg.routing, seed=3)
    base = DynamicEdgeCloudNetwork(20, cfg.routing, seed=3)
    for _ in range(3):
        hist.update_round(False), base.update_round(True)
    assert not np.array_equal(hist.client_edge_latency, base.client_edge_latency)


def test_random_path_is_deterministic_and_matched_draws_equal():
    cfg = Config()
    cfg.routing.trace_mode = "matched"
    a = DynamicEdgeCloudNetwork(20, cfg.routing, seed=9)
    b = DynamicEdgeCloudNetwork(20, cfg.routing, seed=9)
    c = DynamicEdgeCloudNetwork(20, cfg.routing, seed=9)
    for _ in range(3):
        da, db, dc = a.update_round(True, "random"), b.update_round(True, "random"), c.update_round(True, "routed")
        assert [d.edge_id for d in da.values()] == [d.edge_id for d in db.values()]
        ta, tc = a.simulate_transfer(4, 1000), c.simulate_transfer(4, 1000)
        assert ta["delivery_draw"] == tc["delivery_draw"]      # same exogenous draw for the same (round, client)


def test_invalid_path_policy_rejected():
    cfg = Config()
    cfg.routing.path_policy = "bogus"
    with pytest.raises(ValueError):
        cfg.validate()
    cfg = Config()
    cfg.routing.enabled = False
    cfg.routing.path_policy = "random"
    with pytest.raises(ValueError):
        cfg.validate()
    net = DynamicEdgeCloudNetwork(5, Config().routing, seed=1)
    with pytest.raises(ValueError):
        net.update_round(True, "nonsense")


def test_end_to_end_path_policy_is_single_factor(tmp_path):
    """uniform-random selection with routed vs random paths: identical selected clients, attackers and failure draws; different network metrics."""
    routed = h.make_config(tmp_path, routing={"selection_policy": "uniform_random", "path_policy": "routed"})
    rand = h.make_config(tmp_path, routing={"selection_policy": "uniform_random", "path_policy": "random"})
    h.run_tiny(routed, tmp_path / "a")
    h.run_tiny(rand, tmp_path / "b")
    na, nb = pd.read_csv(tmp_path / "a" / "network_metrics.csv"), pd.read_csv(tmp_path / "b" / "network_metrics.csv")
    key = ["round", "client_id"]
    assert na[key].equals(nb[key])
    for col in ("malicious", "explicit_client_failure", "explicit_failure_draw"):
        assert na[col].equals(nb[col]), col
    assert not np.allclose(na["end_to_end_delay_ms"], nb["end_to_end_delay_ms"])
    assert set(na["edge_id"]) <= {0, 1, 2}
    # routed paths are never worse in route score than random ones on average
    assert na["route_score"].mean() >= nb["route_score"].mean()
