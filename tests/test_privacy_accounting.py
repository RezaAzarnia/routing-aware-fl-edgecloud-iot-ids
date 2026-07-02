from src.privacy import (
    approximate_rdp_epsilon,
    calibrate_noise_multiplier,
    capped_normalized_weights,
)


def test_noise_calibration_hits_target_from_below():
    target = 10.0
    sigma = calibrate_noise_multiplier(
        target_epsilon=target,
        steps=20,
        delta=1e-5,
        sample_rate=0.2,
    )
    epsilon = approximate_rdp_epsilon(sigma, 20, 1e-5, sample_rate=0.2)
    assert epsilon <= target * 1.001
    assert epsilon > target * 0.95


def test_capped_weights_sum_to_one_and_obey_cap():
    normalized, actual_cap = capped_normalized_weights([100, 1, 1, 1, 1], 0.30)
    assert abs(sum(normalized) - 1.0) < 1e-12
    assert max(normalized) <= actual_cap + 1e-12
    assert actual_cap <= 0.3000001
