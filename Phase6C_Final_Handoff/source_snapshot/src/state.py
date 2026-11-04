from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, Tuple

import torch

State = Dict[str, torch.Tensor]


def clone_state(state: State, device: str | None = "cpu") -> State:
    result = OrderedDict()
    for key, value in state.items():
        cloned = value.detach().clone()
        if device is not None:
            cloned = cloned.to(device)
        result[key] = cloned
    return result


def subtract_states(after: State, before: State) -> State:
    return OrderedDict((key, after[key] - before[key]) for key in before)


def add_states(left: State, right: State) -> State:
    return OrderedDict((key, left[key] + right[key]) for key in left)


def scale_state(state: State, scalar: float) -> State:
    return OrderedDict((key, value * scalar) for key, value in state.items())


def state_l2_norm(state: State) -> torch.Tensor:
    squares = [torch.sum(value.detach().float() ** 2) for value in state.values()]
    return torch.sqrt(torch.stack(squares).sum())


def state_num_bytes(state: State) -> int:
    return int(sum(value.numel() * value.element_size() for value in state.values()))


def state_to_vector(state: State) -> torch.Tensor:
    return torch.cat([value.detach().reshape(-1).float().cpu() for value in state.values()])


def vector_to_state(vector: torch.Tensor, template: State) -> State:
    result = OrderedDict()
    offset = 0
    for key, value in template.items():
        count = value.numel()
        shaped = vector[offset : offset + count].reshape(value.shape).to(value.dtype)
        result[key] = shaped
        offset += count
    if offset != vector.numel():
        raise ValueError("Vector length does not match state template")
    return result
