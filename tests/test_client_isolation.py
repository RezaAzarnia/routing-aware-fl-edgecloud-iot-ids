import numpy as np
import torch

from src.client import Client
from src.model import ANN
from src.state import clone_state


def test_local_training_does_not_mutate_global_state():
    X = np.random.default_rng(1).normal(size=(32, 4)).astype(np.float32)
    y = np.random.default_rng(2).integers(0, 2, size=32, dtype=np.int64)
    global_model = ANN(4, hidden_dims=(8,), dropout=0.0)
    before = clone_state(global_model.state_dict(), "cpu")
    client = Client(0, X, y)
    client.train_local(
        model_factory=lambda: ANN(4, hidden_dims=(8,), dropout=0.0),
        global_state=before,
        epochs=1,
        batch_size=8,
        learning_rate=1e-3,
        weight_decay=0.0,
        seed=3,
        privacy_mode="none",
        clip_norm=1.0,
        noise_multiplier=0.0,
    )
    after = global_model.state_dict()
    for key in before:
        assert torch.equal(before[key], after[key])
