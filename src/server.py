from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from .metrics import binary_classification_metrics
from .state import State, add_states, clone_state, scale_state


class Server:
    def __init__(self, model: torch.nn.Module, device: str = "cpu") -> None:
        self.model = model.to(device)
        self.device = device
        self._velocity: State | None = None

    def get_global_state(self) -> State:
        return clone_state(self.model.state_dict(), "cpu")

    def load_global_state(self, state: State, reset_optimizer_state: bool = False) -> None:
        self.model.load_state_dict(clone_state(state, self.device), strict=True)
        if reset_optimizer_state:
            self._velocity = None

    def apply_update(
        self,
        update: State,
        learning_rate: float = 1.0,
        momentum: float = 0.0,
    ) -> State:
        """Apply a FedAvg or FedAvgM server update and return the applied delta.

        Momentum and scaling are deterministic post-processing of the already
        aggregated update, so they do not consume additional privacy budget.
        """
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if not 0 <= momentum < 1:
            raise ValueError("momentum must be in [0, 1)")

        moved = clone_state(update, self.device)
        if self._velocity is None:
            self._velocity = OrderedDict(
                (key, torch.zeros_like(value, device=self.device))
                for key, value in moved.items()
            )
        self._velocity = OrderedDict(
            (key, momentum * self._velocity[key] + moved[key])
            for key in moved
        )
        applied = scale_state(self._velocity, learning_rate)
        current = clone_state(self.model.state_dict(), self.device)
        self.model.load_state_dict(add_states(current, applied), strict=True)
        return clone_state(applied, "cpu")

    @torch.no_grad()
    def predict_probabilities(
        self,
        X: np.ndarray,
        batch_size: int = 4096,
    ) -> np.ndarray:
        self.model.eval()
        loader = DataLoader(
            TensorDataset(torch.from_numpy(X).float()),
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
        )
        probabilities = []
        for (features,) in loader:
            logits = self.model(features.to(self.device))
            batch_probabilities = torch.softmax(logits, dim=1)[:, 1]
            probabilities.append(batch_probabilities.cpu().numpy())
        return np.concatenate(probabilities)

    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        batch_size: int = 4096,
        threshold: float = 0.5,
    ) -> Tuple[Dict[str, float], np.ndarray]:
        probabilities = self.predict_probabilities(X, batch_size=batch_size)
        return binary_classification_metrics(y, probabilities, threshold), probabilities
