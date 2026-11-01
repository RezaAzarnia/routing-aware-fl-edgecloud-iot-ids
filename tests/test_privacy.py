import torch

from src.privacy import approximate_rdp_epsilon, clip_update
from src.state import state_l2_norm


def test_clipping_bounds_update_norm():
    update = {"w": torch.tensor([3.0, 4.0])}
    clipped = clip_update(update, 1.0)
    assert state_l2_norm(clipped).item() <= 1.000001


def test_epsilon_increases_with_steps():
    first = approximate_rdp_epsilon(1.0, 1, 1e-5)
    second = approximate_rdp_epsilon(1.0, 10, 1e-5)
    assert second > first
