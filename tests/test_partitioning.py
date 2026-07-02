import numpy as np

from src.partitioning import make_partitions


def test_iid_partition_covers_all_samples_once():
    y = np.array([0, 1] * 50)
    parts = make_partitions(y, 5, "iid", seed=1)
    combined = np.concatenate(parts)
    assert len(combined) == len(y)
    assert len(np.unique(combined)) == len(y)


def test_dirichlet_partition_has_minimum_size():
    y = np.array([0] * 500 + [1] * 500)
    parts = make_partitions(
        y,
        10,
        "dirichlet",
        seed=1,
        dirichlet_alpha=0.5,
        min_client_samples=10,
    )
    assert min(map(len, parts)) >= 10
