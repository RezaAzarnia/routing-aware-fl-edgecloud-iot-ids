from __future__ import annotations

from typing import List

import numpy as np


def group_holdout_mask(y, groups, fraction: float, seed: int):
    """Phase 10 (amendment 1): boolean mask of GLOBAL held-out training rows, chosen at the level of predictor-vector groups.

    Every row of a chosen group is held out, so no held-out row shares its predictor vector with any training row of any client (the same grouping policy as the
    dataset's train/validation split). Groups are taken in a seeded random order until ``fraction`` of the rows is reached. The mask depends only on
    (labels-free groups, fraction, seed): it is identical for every routing policy and network scenario of a seed. fraction <= 0 returns an all-False mask."""
    n = len(y)
    mask = np.zeros(n, dtype=bool)
    if fraction <= 0:
        return mask
    groups = np.asarray(groups)
    uniq, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    order = np.random.default_rng([seed, 8000]).permutation(len(uniq))
    target, taken = fraction * n, 0
    chosen = np.zeros(len(uniq), dtype=bool)
    for g in order:
        if taken >= target:
            break
        chosen[g] = True
        taken += counts[g]
    return chosen[inverse]


def split_client_holdout_by_mask(partitions, holdout_mask):
    """Per client: (training indices, held-out indices) given the global held-out row mask. Every client must keep at least one training row."""
    holdout_mask = np.asarray(holdout_mask, dtype=bool)
    train, hold = [], []
    for p in partitions:
        p = np.asarray(p, dtype=np.int64)
        m = holdout_mask[p]
        train.append(p[~m])
        hold.append(p[m])
        if len(train[-1]) == 0:
            raise ValueError("a client has no training rows after the holdout split")
    return train, hold


def partition_iid(y: np.ndarray, num_clients: int, seed: int) -> List[np.ndarray]:
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(y))
    return [np.asarray(part, dtype=np.int64) for part in np.array_split(indices, num_clients)]


def partition_dirichlet(
    y: np.ndarray,
    num_clients: int,
    alpha: float,
    min_client_samples: int,
    seed: int,
    max_attempts: int = 200,
) -> List[np.ndarray]:
    if alpha <= 0:
        raise ValueError("Dirichlet alpha must be positive")
    rng = np.random.default_rng(seed)
    classes = np.unique(y)

    for _ in range(max_attempts):
        client_indices = [[] for _ in range(num_clients)]
        for label in classes:
            label_indices = np.where(y == label)[0]
            rng.shuffle(label_indices)
            proportions = rng.dirichlet(np.full(num_clients, alpha))
            split_points = (np.cumsum(proportions)[:-1] * len(label_indices)).astype(int)
            pieces = np.split(label_indices, split_points)
            for client_id, piece in enumerate(pieces):
                client_indices[client_id].extend(piece.tolist())

        if len(y) < num_clients * min_client_samples:
            raise ValueError(
                "The dataset is too small for num_clients * min_client_samples"
            )

        # Rebalance only when a random Dirichlet draw creates very small clients.
        # This preserves non-IID label skew while guaranteeing a runnable experiment.
        while min(map(len, client_indices)) < min_client_samples:
            receiver = int(np.argmin([len(indices) for indices in client_indices]))
            donor = int(np.argmax([len(indices) for indices in client_indices]))
            if len(client_indices[donor]) <= min_client_samples:
                break
            move_count = min(
                min_client_samples - len(client_indices[receiver]),
                len(client_indices[donor]) - min_client_samples,
            )
            moved = client_indices[donor][-move_count:]
            del client_indices[donor][-move_count:]
            client_indices[receiver].extend(moved)

        sizes = [len(indices) for indices in client_indices]
        if min(sizes) >= min_client_samples:
            result = []
            for indices in client_indices:
                array = np.asarray(indices, dtype=np.int64)
                rng.shuffle(array)
                result.append(array)
            return result

    raise RuntimeError(
        "Could not generate a valid Dirichlet partition. Check the requested parameters."
    )


def make_partitions(
    y: np.ndarray,
    num_clients: int,
    strategy: str,
    seed: int,
    dirichlet_alpha: float = 0.5,
    min_client_samples: int = 1,
) -> List[np.ndarray]:
    if strategy == "iid":
        partitions = partition_iid(y, num_clients, seed)
    elif strategy == "dirichlet":
        partitions = partition_dirichlet(
            y,
            num_clients,
            dirichlet_alpha,
            min_client_samples,
            seed,
        )
    else:
        raise ValueError(f"Unknown partition strategy: {strategy}")
    if any(len(part) == 0 for part in partitions):
        raise RuntimeError("At least one client received no samples")
    return partitions
