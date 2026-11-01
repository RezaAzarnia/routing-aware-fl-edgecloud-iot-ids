from __future__ import annotations

from typing import List

from .config import Config


def _named(cfg: Config, name: str) -> Config:
    variant = cfg.clone()
    variant.experiment.method_name = name
    return variant


def _disable_privacy(cfg: Config) -> None:
    cfg.privacy.mode = "none"
    cfg.privacy.auto_calibrate_noise = False
    cfg.privacy.target_epsilon = None


def _clean_variant(base: Config, name: str) -> Config:
    clean = _named(base, name)
    clean.routing.enabled = False
    clean.failure.enabled = False
    clean.failure.recovery_enabled = False
    clean.attack.attack_type = "none"
    clean.attack.malicious_fraction = 0.0
    _disable_privacy(clean)
    clean.aggregation.method = "fedavg"
    return clean


def _scenario_no_dp_variant(base: Config, name: str) -> Config:
    scenario = _named(base, name)
    _disable_privacy(scenario)
    return scenario


def _dp_variant(base: Config, name: str, epsilon: float) -> Config:
    variant = _named(base, name)
    variant.privacy.mode = "central_client"
    variant.privacy.target_epsilon = float(epsilon)
    variant.privacy.auto_calibrate_noise = True
    return variant


def _baseline_variants(base: Config) -> List[Config]:
    variants: List[Config] = []

    centralized = _clean_variant(base, "centralized_clean")
    centralized.fl.num_clients = 1
    centralized.fl.clients_per_round = 1
    centralized.fl.partition = "iid"
    centralized.fl.server_momentum = 0.0
    variants.append(centralized)

    variants.append(_clean_variant(base, "fedavg_clean"))

    fedavg_scenario = _scenario_no_dp_variant(base, "fedavg_scenario")
    fedavg_scenario.routing.enabled = False
    fedavg_scenario.failure.recovery_enabled = False
    fedavg_scenario.aggregation.method = "fedavg"
    variants.append(fedavg_scenario)

    fedavg_dp = _named(base, "fedavg_dp_scenario")
    fedavg_dp.routing.enabled = False
    fedavg_dp.failure.recovery_enabled = False
    fedavg_dp.aggregation.method = "fedavg"
    variants.append(fedavg_dp)

    robust = _scenario_no_dp_variant(base, "robust_no_dp_scenario")
    robust.routing.enabled = False
    robust.failure.recovery_enabled = False
    robust.aggregation.method = "distance_filter"
    variants.append(robust)

    variants.append(_named(base, "proposed_full"))
    return variants


def _ablation_variants(base: Config) -> List[Config]:
    no_dp = _scenario_no_dp_variant(base, "ablation_no_dp")

    no_routing = _named(base, "ablation_no_routing")
    no_routing.routing.enabled = False

    no_robust = _named(base, "ablation_no_robust")
    no_robust.aggregation.method = "fedavg"

    no_recovery = _named(base, "ablation_no_recovery")
    no_recovery.failure.recovery_enabled = False

    no_momentum = _named(base, "ablation_no_server_momentum")
    no_momentum.fl.server_momentum = 0.0
    no_momentum.fl.server_learning_rate = 1.0

    return [no_dp, no_routing, no_robust, no_recovery, no_momentum]


def _attack_fraction_variants(base: Config) -> List[Config]:
    attack_type = base.attack.attack_type if base.attack.attack_type != "none" else "sign_flip"
    variants = []
    for fraction in [0.0, 0.1, 0.2, 0.3]:
        variant = _named(base, f"attack_{attack_type}_{int(fraction * 100)}pct")
        variant.attack.attack_type = attack_type
        variant.attack.malicious_fraction = fraction
        variants.append(variant)
    return variants


def _attack_type_variants(base: Config) -> List[Config]:
    variants = []
    fraction = base.attack.malicious_fraction or 0.2
    for attack_type in ["sign_flip", "gaussian", "model_replacement"]:
        variant = _named(base, f"attack_type_{attack_type}_{int(fraction * 100)}pct")
        variant.attack.attack_type = attack_type
        variant.attack.malicious_fraction = fraction
        variants.append(variant)
    return variants


def _failure_variants(base: Config) -> List[Config]:
    variants = []
    for probability in [0.0, 0.05, 0.1, 0.2, 0.3]:
        variant = _named(base, f"failure_{int(probability * 100)}pct")
        variant.failure.client_failure_probability = probability
        variants.append(variant)
    return variants


def _heterogeneity_variants(base: Config) -> List[Config]:
    iid = _named(base, "heterogeneity_iid")
    iid.fl.partition = "iid"
    variants = [iid]
    for alpha in [1.0, 0.5, 0.1]:
        variant = _named(base, f"heterogeneity_dirichlet_{str(alpha).replace('.', '_')}")
        variant.fl.partition = "dirichlet"
        variant.fl.dirichlet_alpha = alpha
        variants.append(variant)
    return variants


def _privacy_variants(base: Config) -> List[Config]:
    variants = [_scenario_no_dp_variant(base, "privacy_none")]
    for epsilon in [20.0, 10.0, 8.0]:
        variants.append(
            _dp_variant(base, f"privacy_target_epsilon_{int(epsilon)}", epsilon)
        )
    return variants



def _clip_norm_variants(base: Config) -> List[Config]:
    """One-seed DP sensitivity screen before the five-seed core study."""
    variants: List[Config] = []
    for clip_norm in [0.05, 0.10, 0.20]:
        label = str(clip_norm).replace(".", "_")
        variant = _dp_variant(base, f"clip_sweep_eps20_clip_{label}", 20.0)
        variant.privacy.clip_norm = clip_norm
        variants.append(variant)
    return variants

def _smoke_variants(base: Config) -> List[Config]:
    # This suite checks installation and I/O only. It is intentionally too small
    # to decide whether a five-seed paper run is worthwhile.
    return [
        _clean_variant(base, "smoke_clean"),
        _scenario_no_dp_variant(base, "smoke_scenario_no_dp"),
    ]


def _pilot_stage1_variants(base: Config) -> List[Config]:
    return [
        _clean_variant(base, "pilot_clean"),
        _scenario_no_dp_variant(base, "pilot_scenario_no_dp"),
    ]


def _pilot_stage2_variants(base: Config) -> List[Config]:
    return [
        _dp_variant(base, "pilot_proposed_dp_eps20", 20.0),
        _dp_variant(base, "pilot_proposed_dp_eps10", 10.0),
    ]


def build_suite(base: Config, suite: str) -> List[Config]:
    if suite == "single":
        return [base]
    if suite in {"preflight", "smoke"}:
        variants = _smoke_variants(base)
    elif suite == "pilot_stage1":
        variants = _pilot_stage1_variants(base)
    elif suite == "pilot_stage2":
        variants = _pilot_stage2_variants(base)
    elif suite == "pilot":
        variants = _pilot_stage1_variants(base) + _pilot_stage2_variants(base)
    elif suite == "baselines":
        variants = _baseline_variants(base)
    elif suite == "baselines_only":
        variants = [
            variant for variant in _baseline_variants(base)
            if variant.experiment.method_name != "proposed_full"
        ]
    elif suite == "ablation":
        variants = _ablation_variants(base)
    elif suite == "core":
        variants = _baseline_variants(base) + _ablation_variants(base)
    elif suite == "attack_sweep":
        variants = _attack_fraction_variants(base)
    elif suite == "attack_type_sweep":
        variants = _attack_type_variants(base)
    elif suite == "failure_sweep":
        variants = _failure_variants(base)
    elif suite == "heterogeneity_sweep":
        variants = _heterogeneity_variants(base)
    elif suite == "privacy_sweep":
        variants = _privacy_variants(base)
    elif suite == "clip_sweep":
        variants = _clip_norm_variants(base)
    elif suite == "full":
        variants = (
            _baseline_variants(base)
            + _ablation_variants(base)
            + _attack_fraction_variants(base)
            + _attack_type_variants(base)
            + _failure_variants(base)
            + _heterogeneity_variants(base)
            + _privacy_variants(base)
        )
    else:
        raise ValueError(f"Unknown suite: {suite}")

    unique = []
    seen = set()
    for variant in variants:
        if variant.experiment.method_name not in seen:
            variant.validate()
            unique.append(variant)
            seen.add(variant.experiment.method_name)
    return unique
