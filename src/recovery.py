from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .aggregation import coordinate_median
from .state import State, clone_state


@dataclass
class RecoveryResult:
    update: State
    recovery_time_ms: float


def recover_failed_update(
    healthy_updates: Sequence[State],
    detection_delay_ms: float,
    reconstruction_time_ms: float,
    average_route_delay_ms: float,
) -> RecoveryResult:
    if len(healthy_updates) < 2:
        raise ValueError("At least two healthy updates are required for recovery")
    recovered = coordinate_median(healthy_updates)
    total_time = detection_delay_ms + reconstruction_time_ms + average_route_delay_ms
    return RecoveryResult(clone_state(recovered, "cpu"), float(total_time))
