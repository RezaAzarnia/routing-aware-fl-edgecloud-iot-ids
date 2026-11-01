from src.config import Config
from src.suites import build_suite


def test_smoke_has_two_non_dp_sanity_variants():
    names = [cfg.experiment.method_name for cfg in build_suite(Config(), "smoke")]
    assert names == ["smoke_clean", "smoke_scenario_no_dp"]


def test_pilot_is_staged_and_tests_two_privacy_budgets():
    stage1 = [cfg.experiment.method_name for cfg in build_suite(Config(), "pilot_stage1")]
    stage2 = [cfg.experiment.method_name for cfg in build_suite(Config(), "pilot_stage2")]
    assert stage1 == ["pilot_clean", "pilot_scenario_no_dp"]
    assert stage2 == ["pilot_proposed_dp_eps20", "pilot_proposed_dp_eps10"]


def test_full_contains_required_sweeps():
    names = {cfg.experiment.method_name for cfg in build_suite(Config(), "full")}
    assert "proposed_full" in names
    assert "failure_30pct" in names
    assert "attack_sign_flip_30pct" in names
    assert "attack_type_model_replacement_20pct" in names
    assert "heterogeneity_dirichlet_0_1" in names
    assert "privacy_target_epsilon_8" in names
    assert "ablation_no_server_momentum" in names


def test_clip_sweep_tests_three_norms_at_epsilon_20():
    variants = build_suite(Config(), "clip_sweep")
    assert [cfg.privacy.clip_norm for cfg in variants] == [0.05, 0.10, 0.20]
    assert all(cfg.privacy.target_epsilon == 20.0 for cfg in variants)
