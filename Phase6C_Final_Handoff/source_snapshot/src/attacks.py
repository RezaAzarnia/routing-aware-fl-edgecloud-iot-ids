from __future__ import annotations

import torch

from .state import State, state_to_vector


def apply_update_attack(
    update: State,
    attack_type: str,
    scale: float,
    generator: torch.Generator | None = None,
) -> State:
    if attack_type in {"none", "label_flip"}:
        return {key: value.detach().clone() for key, value in update.items()}
    if attack_type == "sign_flip":
        return {key: -scale * value for key, value in update.items()}
    if attack_type == "model_replacement":
        return {key: scale * value for key, value in update.items()}
    if attack_type == "zero":
        return {key: torch.zeros_like(value) for key, value in update.items()}
    if attack_type == "gaussian":
        vector = state_to_vector(update)
        std = max(float(vector.std(unbiased=False).item()), 1e-6) * scale
        attacked = {}
        for key, value in update.items():
            attacked[key] = torch.randn(
                value.shape,
                dtype=value.dtype,
                device=value.device,
                generator=generator,
            ) * std
        return attacked
    raise ValueError(f"Unknown attack type: {attack_type}")
