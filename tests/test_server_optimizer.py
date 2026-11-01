import torch

from src.model import ANN
from src.server import Server
from src.state import state_l2_norm


def test_server_momentum_changes_second_applied_update():
    server = Server(ANN(input_dim=2, hidden_dims=(2,), dropout=0.0), device="cpu")
    state = server.get_global_state()
    update = {key: torch.ones_like(value) * 0.01 for key, value in state.items()}

    first = server.apply_update(update, learning_rate=0.5, momentum=0.9)
    second = server.apply_update(update, learning_rate=0.5, momentum=0.9)

    assert state_l2_norm(second).item() > state_l2_norm(first).item()
