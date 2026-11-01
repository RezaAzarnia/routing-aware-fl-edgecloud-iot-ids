"""Regression tests for defects verified on the 7c75b2d source tree."""
import pytest
import torch

from src.aggregation import coordinate_median, distance_filter_indices, true_median
from src.config import Config
from src.experiment import _privacy_plan
from src.recovery import recover_failed_update


def _states(values):
    return [{"w": torch.tensor([float(v)])} for v in values]


def test_true_median_averages_middle_values_for_even_counts():
    assert true_median(torch.tensor([0.0, 10.0]), dim=0).item() == 5.0
    assert true_median(torch.tensor([1.0, 2.0, 3.0, 100.0]), dim=0).item() == 2.5
    assert true_median(torch.tensor([3.0, 1.0, 2.0]), dim=0).item() == 2.0


def test_coordinate_median_is_unbiased_for_even_number_of_updates():
    assert coordinate_median(_states([0, 10]))["w"].item() == 5.0


def test_failed_update_recovery_uses_true_median():
    result = recover_failed_update(_states([0, 10]), 0.0, 0.0, 0.0)
    assert result.update["w"].item() == 5.0


def test_distance_filter_uses_true_median_center():
    # Lower-median centre of [0,0,10,10] would be 0 and make distances asymmetric.
    keep, distances = distance_filter_indices(_states([0, 0, 10, 10]), k=2.5)
    assert distances[0] == pytest.approx(distances[3])
    assert sorted(keep) == [0, 1, 2, 3]


@pytest.mark.parametrize("method", ["median", "trimmed_mean"])
def test_central_dp_rejects_robust_methods_it_would_discard(method):
    cfg = Config()
    cfg.privacy.mode = "central_client"
    cfg.aggregation.method = method
    with pytest.raises(ValueError, match="incompatible"):
        cfg.validate()


def test_privacy_plan_flags_invalid_amplification_under_routed_selection():
    cfg = Config()
    cfg.privacy.mode = "central_client"
    cfg.routing.enabled = True
    plan = _privacy_plan(cfg)
    assert plan["subsampling_amplification_valid"] is False
    cfg.routing.enabled = False
    # Phase 6A: fixed-size uniform selection is not Poisson subsampling either, so no
    # amplification claim is made for any selection scheme.
    assert _privacy_plan(cfg)["subsampling_amplification_valid"] is False
    assert _privacy_plan(cfg)["client_selection_is_random"] is True
