import torch

from src.aggregation import aggregate_updates, fedavg


def test_weighted_fedavg():
    updates = [{"w": torch.tensor([1.0])}, {"w": torch.tensor([3.0])}]
    result = fedavg(updates, [1, 3])
    assert torch.allclose(result["w"], torch.tensor([2.5]))


def test_distance_filter_rejects_large_outlier():
    updates = [
        {"w": torch.tensor([0.0, 0.0])},
        {"w": torch.tensor([0.1, -0.1])},
        {"w": torch.tensor([-0.1, 0.1])},
        {"w": torch.tensor([100.0, 100.0])},
    ]
    result = aggregate_updates(updates, [1, 1, 1, 1], "distance_filter", distance_k=2.0)
    assert 3 in result.rejected_indices
