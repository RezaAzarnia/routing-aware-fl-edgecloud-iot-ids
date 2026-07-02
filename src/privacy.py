from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import torch

from .state import State, state_l2_norm


def clip_update(update: State, max_norm: float) -> State:
    if max_norm <= 0:
        raise ValueError("max_norm must be positive")
    norm = float(state_l2_norm(update).item())
    scale = min(1.0, max_norm / (norm + 1e-12))
    return {key: value * scale for key, value in update.items()}


def add_gaussian_noise(
    update: State,
    std: float,
    generator: torch.Generator | None = None,
) -> State:
    if std <= 0:
        return {key: value.detach().clone() for key, value in update.items()}
    result = {}
    for key, value in update.items():
        noise = torch.randn(
            value.shape,
            dtype=value.dtype,
            device=value.device,
            generator=generator,
        ) * std
        result[key] = value + noise
    return result


def _log_add(log_x: float, log_y: float) -> float:
    if log_x == -math.inf:
        return log_y
    if log_y == -math.inf:
        return log_x
    maximum = max(log_x, log_y)
    return maximum + math.log(math.exp(log_x - maximum) + math.exp(log_y - maximum))


def _integer_order_sampled_gaussian_rdp(
    sample_rate: float,
    noise_multiplier: float,
    order: int,
) -> float:
    """RDP of the Poisson-sampled Gaussian mechanism for integer orders.

    The finite-sum expression is exact for integer alpha under Poisson sampling.
    In this project it is used as an accounting estimate because routed client
    selection is data-independent but is not exactly Poisson sampling.
    """
    if order < 2:
        raise ValueError("RDP order must be at least 2")
    if noise_multiplier <= 0:
        return float("inf")
    if sample_rate <= 0:
        return 0.0
    if sample_rate >= 1:
        return order / (2.0 * noise_multiplier**2)

    log_a = -math.inf
    log_q = math.log(sample_rate)
    log_one_minus_q = math.log1p(-sample_rate)
    for i in range(order + 1):
        log_combination = (
            math.lgamma(order + 1)
            - math.lgamma(i + 1)
            - math.lgamma(order - i + 1)
        )
        term = log_combination
        if i:
            term += i * log_q
        if order - i:
            term += (order - i) * log_one_minus_q
        term += (i * i - i) / (2.0 * noise_multiplier**2)
        log_a = _log_add(log_a, term)
    return log_a / (order - 1)


def approximate_rdp_epsilon(
    noise_multiplier: float,
    steps: int,
    delta: float,
    sample_rate: float = 1.0,
    orders: Sequence[int] = tuple(range(2, 129)),
) -> float:
    """Return an RDP-based epsilon estimate for repeated sampled Gaussian steps."""
    if steps <= 0:
        return 0.0
    if noise_multiplier <= 0:
        return float("inf")
    if not 0 < delta < 1:
        raise ValueError("delta must be in (0, 1)")
    if not 0 < sample_rate <= 1:
        raise ValueError("sample_rate must be in (0, 1]")

    candidates = []
    for order in orders:
        per_step = _integer_order_sampled_gaussian_rdp(
            sample_rate,
            noise_multiplier,
            int(order),
        )
        rdp = steps * per_step
        epsilon = rdp + math.log(1.0 / delta) / (order - 1)
        candidates.append(epsilon)
    return float(min(candidates))


def calibrate_noise_multiplier(
    target_epsilon: float,
    steps: int,
    delta: float,
    sample_rate: float,
    tolerance: float = 1e-4,
) -> float:
    """Binary-search a multiplier whose estimated epsilon does not exceed target."""
    if target_epsilon <= 0:
        raise ValueError("target_epsilon must be positive")
    if steps <= 0:
        return 0.0

    lower = 1e-3
    upper = 1.0
    while approximate_rdp_epsilon(upper, steps, delta, sample_rate) > target_epsilon:
        upper *= 2.0
        if upper > 1e4:
            raise RuntimeError("Could not calibrate a finite noise multiplier")

    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        epsilon = approximate_rdp_epsilon(midpoint, steps, delta, sample_rate)
        if epsilon > target_epsilon:
            lower = midpoint
        else:
            upper = midpoint
        if upper - lower <= tolerance * max(1.0, upper):
            break
    return float(upper)


def capped_normalized_weights(
    weights: Sequence[float],
    requested_cap: float,
) -> tuple[list[float], float]:
    """Project positive weights onto a simplex with an upper share cap.

    If fewer updates survive than the requested cap permits, the smallest
    mathematically feasible cap (1/n) is used and returned.
    """
    raw = np.asarray(weights, dtype=float)
    if raw.ndim != 1 or len(raw) == 0:
        raise ValueError("weights must be a non-empty one-dimensional sequence")
    if np.any(raw < 0) or raw.sum() <= 0:
        raise ValueError("weights must be non-negative with a positive sum")
    n = len(raw)
    cap = max(float(requested_cap), 1.0 / n)
    cap = min(cap, 1.0)

    result = np.zeros(n, dtype=float)
    active = np.ones(n, dtype=bool)
    remaining_mass = 1.0
    while active.any():
        active_weights = raw[active]
        if active_weights.sum() <= 0:
            result[active] = remaining_mass / active.sum()
            break
        tentative = active_weights / active_weights.sum() * remaining_mass
        over = tentative > cap + 1e-15
        active_indices = np.where(active)[0]
        if not over.any():
            result[active_indices] = tentative
            break
        capped_indices = active_indices[over]
        result[capped_indices] = cap
        active[capped_indices] = False
        remaining_mass = max(0.0, 1.0 - result.sum())

    result /= result.sum()
    return result.tolist(), float(result.max())
