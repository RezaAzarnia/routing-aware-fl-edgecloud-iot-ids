from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np
import torch

from .state import State, state_to_vector, vector_to_state


@dataclass
class AggregationResult:
    update: State
    kept_indices: List[int]
    rejected_indices: List[int]
    distances: List[float]


def _stack(updates: Sequence[State]) -> torch.Tensor:
    if not updates:
        raise ValueError("At least one update is required")
    return torch.stack([state_to_vector(update) for update in updates], dim=0)


def fedavg(updates: Sequence[State], weights: Sequence[float]) -> State:
    if len(updates) != len(weights) or not updates:
        raise ValueError("updates and weights must have equal non-zero length")
    vector_matrix = _stack(updates)
    weight_tensor = torch.tensor(weights, dtype=vector_matrix.dtype)
    weight_tensor = weight_tensor / weight_tensor.sum().clamp_min(1e-12)
    vector = torch.sum(vector_matrix * weight_tensor[:, None], dim=0)
    return vector_to_state(vector, updates[0])


def coordinate_median(updates: Sequence[State]) -> State:
    vectors = _stack(updates)
    vector = torch.median(vectors, dim=0).values
    return vector_to_state(vector, updates[0])


def trimmed_mean(updates: Sequence[State], trim_ratio: float) -> State:
    if not 0 <= trim_ratio < 0.5:
        raise ValueError("trim_ratio must be in [0, 0.5)")
    vectors = _stack(updates)
    n = vectors.shape[0]
    trim = int(np.floor(n * trim_ratio))
    if trim == 0:
        vector = vectors.mean(dim=0)
    else:
        sorted_values = torch.sort(vectors, dim=0).values
        vector = sorted_values[trim : n - trim].mean(dim=0)
    return vector_to_state(vector, updates[0])


def distance_filter_indices(updates: Sequence[State], k: float) -> tuple[List[int], List[float]]:
    vectors = _stack(updates)
    center = torch.median(vectors, dim=0).values
    distances = torch.linalg.vector_norm(vectors - center, dim=1)
    median_distance = torch.median(distances)
    mad = torch.median(torch.abs(distances - median_distance))
    robust_sigma = 1.4826 * mad + 1e-12
    threshold = median_distance + k * robust_sigma
    keep = torch.where(distances <= threshold)[0].tolist()
    if not keep:
        keep = [int(torch.argmin(distances).item())]
    return keep, distances.tolist()


def multi_krum_indices(updates: Sequence[State], f: int) -> tuple[List[int], List[float]]:
    vectors = _stack(updates)
    n = len(updates)
    if f < 0:
        raise ValueError("f must be non-negative")
    if n < 2 * f + 3:
        raise ValueError(f"Multi-Krum requires n >= 2f + 3; received n={n}, f={f}")
    pairwise = torch.cdist(vectors, vectors, p=2) ** 2
    neighbor_count = n - f - 2
    scores = []
    for index in range(n):
        row = torch.cat((pairwise[index, :index], pairwise[index, index + 1 :]))
        nearest = torch.topk(row, k=neighbor_count, largest=False).values
        scores.append(float(nearest.sum().item()))
    selected_count = max(1, n - f)
    keep = np.argsort(scores)[:selected_count].tolist()
    return keep, scores


def aggregate_updates(
    updates: Sequence[State],
    weights: Sequence[float],
    method: str,
    trim_ratio: float = 0.2,
    distance_k: float = 2.5,
    byzantine_assumption: int = 1,
) -> AggregationResult:
    n = len(updates)
    if n == 0:
        raise ValueError("Cannot aggregate an empty update list")
    all_indices = list(range(n))
    distances: List[float] = []

    if method == "fedavg":
        keep = all_indices
        aggregate = fedavg(updates, weights)
    elif method == "median":
        keep = all_indices
        aggregate = coordinate_median(updates)
    elif method == "trimmed_mean":
        keep = all_indices
        aggregate = trimmed_mean(updates, trim_ratio)
    elif method == "distance_filter":
        keep, distances = distance_filter_indices(updates, distance_k)
        aggregate = fedavg([updates[i] for i in keep], [weights[i] for i in keep])
    elif method == "multi_krum":
        keep, distances = multi_krum_indices(updates, byzantine_assumption)
        aggregate = fedavg([updates[i] for i in keep], [weights[i] for i in keep])
    else:
        raise ValueError(f"Unknown aggregation method: {method}")

    rejected = [index for index in all_indices if index not in keep]
    return AggregationResult(aggregate, keep, rejected, distances)
