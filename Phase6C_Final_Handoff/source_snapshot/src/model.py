from __future__ import annotations

from typing import Iterable

import torch.nn as nn


class ANN(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: Iterable[int] = (128, 96, 64),
        dropout: float = 0.25,
        num_classes: int = 2,
    ) -> None:
        super().__init__()
        layers = []
        previous = input_dim
        hidden_dims = tuple(hidden_dims)
        for index, hidden in enumerate(hidden_dims):
            layers.append(nn.Linear(previous, hidden))
            layers.append(nn.ReLU())
            if dropout > 0 and index == len(hidden_dims) - 1:
                layers.append(nn.Dropout(dropout))
            previous = hidden
        layers.append(nn.Linear(previous, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, inputs):
        return self.network(inputs)
