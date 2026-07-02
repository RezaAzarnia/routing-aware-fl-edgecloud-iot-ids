from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from .privacy import add_gaussian_noise, clip_update
from .state import State, clone_state, subtract_states


@dataclass
class LocalTrainResult:
    update: State
    num_samples: int
    mean_loss: float
    train_seconds: float
    flipped_labels: int


class Client:
    def __init__(self, client_id: int, X: np.ndarray, y: np.ndarray, device: str = "cpu") -> None:
        self.client_id = client_id
        self.X = X
        self.y = y
        self.device = device

    def train_local(
        self,
        model_factory: Callable[[], torch.nn.Module],
        global_state: State,
        epochs: int,
        batch_size: int,
        learning_rate: float,
        weight_decay: float,
        seed: int,
        privacy_mode: str,
        clip_norm: float,
        noise_multiplier: float,
        label_flip_probability: float = 0.0,
    ) -> LocalTrainResult:
        # A fresh model is built for every client. The server model is never passed by reference.
        model = model_factory().to(self.device)
        model.load_state_dict(clone_state(global_state, self.device), strict=True)
        model.train()

        features = torch.from_numpy(self.X).float()
        labels_np = self.y.copy()
        flipped_labels = 0
        if label_flip_probability > 0:
            rng = np.random.default_rng(seed)
            mask = rng.random(len(labels_np)) < label_flip_probability
            labels_np[mask] = 1 - labels_np[mask]
            flipped_labels = int(mask.sum())
        labels = torch.from_numpy(labels_np).long()

        generator = torch.Generator()
        generator.manual_seed(seed)
        loader = DataLoader(
            TensorDataset(features, labels),
            batch_size=batch_size,
            shuffle=True,
            generator=generator,
            num_workers=0,
        )
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        loss_function = torch.nn.CrossEntropyLoss()
        before = clone_state(model.state_dict(), self.device)

        start = time.perf_counter()
        total_loss = 0.0
        total_seen = 0
        for _ in range(epochs):
            for batch_features, batch_labels in loader:
                batch_features = batch_features.to(self.device)
                batch_labels = batch_labels.to(self.device)
                optimizer.zero_grad(set_to_none=True)
                logits = model(batch_features)
                loss = loss_function(logits, batch_labels)
                loss.backward()
                optimizer.step()
                batch_size_actual = len(batch_labels)
                total_loss += float(loss.item()) * batch_size_actual
                total_seen += batch_size_actual
        elapsed = time.perf_counter() - start

        after = clone_state(model.state_dict(), self.device)
        update = subtract_states(after, before)
        update = clone_state(update, "cpu")

        if privacy_mode == "local_update":
            update = clip_update(update, clip_norm)
            noise_generator = torch.Generator(device="cpu")
            noise_generator.manual_seed(seed + 10_000)
            update = add_gaussian_noise(
                update,
                std=noise_multiplier * clip_norm,
                generator=noise_generator,
            )

        mean_loss = total_loss / max(total_seen, 1)
        return LocalTrainResult(
            update=update,
            num_samples=len(self.y),
            mean_loss=mean_loss,
            train_seconds=elapsed,
            flipped_labels=flipped_labels,
        )
