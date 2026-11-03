"""Phase 8: collective surrogate-weight cap preserved in the central-DP path (new, default-off variant)."""
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_phase7_guard import make_config, run  # noqa: E402

from src.config import Config
from src.privacy import capped_normalized_weights, group_capped_normalized_weights


def test_flag_is_off_by_default():
    assert Config().privacy.preserve_surrogate_cap is False


def test_old_projection_discards_the_surrogate_cap_when_the_client_cap_is_infeasible():
    """Documents the Phase 6C behaviour: 4 real + 4 surrogate updates, per-client cap 0.10 (infeasible for n=8) -> uniform."""
    raw = [10.0] * 4 + [1.0] * 4                         # surrogate weights already scaled down
    w, _ = capped_normalized_weights(raw, 0.10)
    assert sum(w[4:]) == pytest.approx(0.5)               # surrogates hold half of the mass


def test_group_cap_enforces_the_collective_surrogate_share():
    raw = [10.0] * 4 + [1.0] * 4
    flags = [False] * 4 + [True] * 4
    w, mx = group_capped_normalized_weights(raw, flags, 0.10, 0.10)
    assert sum(w) == pytest.approx(1.0) and min(w) >= 0
    assert sum(w[4:]) <= 0.10 + 1e-12
    assert mx == pytest.approx(max(w))


def test_group_cap_does_not_inflate_a_smaller_surrogate_share():
    raw = [10.0] * 6 + [0.1] * 2
    flags = [False] * 6 + [True] * 2
    w, _ = group_capped_normalized_weights(raw, flags, 0.10, 0.10)
    assert sum(w[6:]) == pytest.approx(0.2 / 60.2)        # raw share, below the cap, preserved


def test_group_cap_reduces_to_the_old_function_without_a_mixed_population():
    raw = [3.0, 1.0, 2.0, 5.0]
    for flags in ([False] * 4, [True] * 4):
        a, am = group_capped_normalized_weights(raw, flags, 0.10, 0.4)
        b, bm = capped_normalized_weights(raw, 0.4)
        assert np.allclose(a, b) and am == pytest.approx(bm)


def test_group_cap_edge_cases():
    w, mx = group_capped_normalized_weights([5.0, 1.0], [False, True], 0.10, 0.10)   # 1 real + 1 surrogate
    assert w[1] == pytest.approx(0.10) and w[0] == pytest.approx(0.90) and mx == pytest.approx(0.90)
    with pytest.raises(ValueError):
        group_capped_normalized_weights([1.0, 1.0], [False, True], 1.0, 0.1)
    with pytest.raises(ValueError):
        group_capped_normalized_weights([1.0, 1.0], [False], 0.1, 0.1)
    with pytest.raises(ValueError):
        group_capped_normalized_weights([0.0, 0.0], [False, True], 0.1, 0.1)


def _dp_config(tmp_path, preserve):
    path = make_config(tmp_path, surrogate_handling="post_filter_real_only")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["failure"]["surrogate_total_weight_cap"] = 0.1
    raw["privacy"].update(mode="central_client", clip_norm=0.1, target_epsilon=10.0, auto_calibrate_noise=True)
    if preserve is not None:
        raw["privacy"]["preserve_surrogate_cap"] = preserve
    out = tmp_path / f"dp_{preserve}.yaml"
    out.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return out


def test_end_to_end_default_off_is_bitwise_identical_and_flag_on_enforces_the_cap(tmp_path):
    omitted = run(_dp_config(tmp_path, None), tmp_path / "omitted")
    off = run(_dp_config(tmp_path, False), tmp_path / "off")
    on = run(_dp_config(tmp_path, True), tmp_path / "on")
    skip = {"round_seconds", "mean_local_train_seconds"}
    for c in omitted.columns:
        if c in skip or not np.issubdtype(omitted[c].dtype, np.number):
            continue
        assert np.allclose(omitted[c].to_numpy(float), off[c].to_numpy(float), equal_nan=True, atol=0, rtol=0), c
    mixed_off = off[(off.imputed_clients > 0) & (off.real_weight_share > 0)]
    mixed_on = on[(on.imputed_clients > 0) & (on.real_weight_share > 0)]
    assert len(mixed_off) > 0 and len(mixed_on) > 0
    assert mixed_on.surrogate_weight_share.max() <= 0.10 + 1e-9          # collective cap now binds
    assert mixed_off.surrogate_weight_share.max() > 0.10 + 1e-6          # historical path exceeds it (the defect)
