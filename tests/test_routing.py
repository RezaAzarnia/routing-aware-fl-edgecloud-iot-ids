from src.config import RoutingConfig
from src.network import DynamicEdgeCloudNetwork


def test_route_metrics_are_bounded_and_client_selection_works():
    cfg = RoutingConfig()
    network = DynamicEdgeCloudNetwork(10, cfg, seed=1)
    decisions = network.update_round()
    assert len(decisions) == 10
    selected = network.select_clients(4)
    assert len(selected) == 4
    assert len(set(selected)) == 4
    for decision in decisions.values():
        assert 0 <= decision.stability <= 1
        assert 0 <= decision.security <= 1
        assert decision.latency_ms > 0
