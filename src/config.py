from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


@dataclass
class DataConfig:
    # Supported values: unsw_nb15 | ciciot2023
    dataset_name: str = "unsw_nb15"
    train_csv: str = "data/UNSW_NB15_training-set.csv"
    # CICIoT2023 uses an explicit validation file prepared from the raw shards.
    # UNSW-NB15 leaves this null and creates validation only from official train.
    validation_csv: str | None = None
    test_csv: str = "data/UNSW_NB15_testing-set.csv"
    label_col: str = "label"
    attack_category_col: str = "attack_cat"
    drop_cols: Tuple[str, ...] = ("id", "attack_cat")
    categorical_cols: Tuple[str, ...] = ("proto", "service", "state")
    validation_fraction: float = 0.15
    # Secondary calibrated evaluation protocol: the official test CSV remains
    # intact for the standard benchmark, while a deterministic stratified split
    # is also created for threshold calibration and a held-out final evaluation.
    # This must remain false for CICIoT2023 because it already has an explicit
    # validation split and the test split must remain untouched.
    enable_calibrated_evaluation: bool = True
    calibration_fraction_of_test: float = 0.20
    calibration_stratify_attack_category: bool = True
    max_train_samples: int | None = None
    max_val_samples: int | None = None
    max_test_samples: int | None = None
    # Optional metadata written by prepare_ciciot2023.py. It is copied into the
    # run summary when present, making split/sample details auditable.
    prepared_metadata_json: str | None = None
    # Validation split protocol for UNSW-NB15 (the only dataset whose validation
    # set is carved from the official training file).
    #   random_stratified : historical protocol (identical predictor vectors may
    #                       fall on both sides of the split)
    #   group_disjoint    : rows sharing a canonical predictor fingerprint always
    #                       stay on the same side of the split
    validation_split: str = "random_stratified"
    # Optional training-side sensitivity policy: drop training rows whose
    # predictor vector occurs with both binary labels inside the training
    # partition. Validation/test are never filtered. The exclusion manifest is
    # saved with each run.
    exclude_conflicting_train_groups: bool = False
    # Leakage-safe threshold protocol: when > 0 the validation partition is split
    # (predictor-group disjoint, label stratified) into a threshold-CALIBRATION part
    # and an independent EVALUATION part. Thresholds are selected on the calibration
    # part only; all reported validation metrics and model selection use the
    # evaluation part. 0 reproduces the historical same-observation behaviour.
    threshold_calibration_fraction: float = 0.0
    # Three-way, predictor-group-disjoint split of the validation pool into
    # calibration (thresholds) / selection (checkpoint choice) / report (never used for a choice).
    validation_three_way: bool = False


@dataclass
class ModelConfig:
    hidden_dims: Tuple[int, ...] = (128, 96, 64)
    dropout: float = 0.20


@dataclass
class FLConfig:
    num_clients: int = 50
    clients_per_round: int = 10
    rounds: int = 30
    local_epochs: int = 2
    batch_size: int = 256
    learning_rate: float = 3e-4
    weight_decay: float = 0.0
    # FedAvgM-style server-side post-processing. Momentum is especially useful
    # in the noisy DP variants because independent Gaussian perturbations are
    # partially averaged over rounds without changing the privacy guarantee.
    server_learning_rate: float = 0.5
    server_momentum: float = 0.9
    partition: str = "dirichlet"  # iid | dirichlet
    dirichlet_alpha: float = 0.5
    min_client_samples: int = 100
    # sample_proportional (historical) | uniform (every retained real update has weight 1;
    # a surrogate update has weight recovery_weight_factor)
    weighting: str = "sample_proportional"


@dataclass
class PrivacyConfig:
    mode: str = "central_client"  # none | local_update | central_client
    # The earlier value 0.25 was much larger than the observed benign update
    # norms. A tighter bound lowers sensitivity and therefore the amount of
    # noise needed for the same target epsilon.
    clip_norm: float = 0.05
    noise_multiplier: float = 1.0
    delta: float = 1e-5
    target_epsilon: float | None = 10.0
    auto_calibrate_noise: bool = True
    # None means clients_per_round / num_clients. This remains an RDP estimate
    # because routed selection is not exactly Poisson sampling.
    accountant_sample_rate: float | None = None
    # With ten surviving clients, 0.10 corresponds to equal weighting. If fewer
    # survive, the implementation uses the smallest feasible cap 1/n and logs it.
    max_client_weight_share: float = 0.10
    adjacency_factor: float = 1.0  # 1.0 add/remove; 2.0 replace-one


@dataclass
class ThresholdConfig:
    enabled: bool = True
    objective: str = "fpr_cap"  # fpr_cap | max_f1 | max_balanced_accuracy | youden
    max_fpr: float = 0.15
    min_recall: float = 0.60
    grid_size: int = 1001
    # Report deployable operating points selected on a reference set and applied
    # unchanged to an evaluation set. These are not oracle test thresholds.
    operating_fpr_caps: Tuple[float, ...] = (0.05, 0.10, 0.15, 0.20)
    # A threshold-independent metric prevents model selection from being driven
    # by an unstable operating threshold during early rounds.
    model_selection_metric: str = "roc_auc"


@dataclass
class AggregationConfig:
    method: str = "distance_filter"  # fedavg | median | trimmed_mean | distance_filter | multi_krum
    trim_ratio: float = 0.2
    distance_k: float = 2.5
    byzantine_assumption: int = 2
    # reference (historical): surrogate (imputed) updates take part in the robust filter's
    #   centre/scale estimation, so identical surrogates can dominate the MAD.
    # post_filter_real_only (corrected): the filter statistics use REAL updates only; surrogates
    #   are generated afterwards from the retained real updates.
    surrogate_handling: str = "reference"
    # Phase 7 (default 0 = historical behaviour, no guard): minimum number of REAL (delivered) updates
    # needed for the server to aggregate. With fewer, the round abstains (no aggregate, no server step,
    # no surrogates). Median/MAD filtering has no outlier-discrimination power below 3 samples.
    min_real_updates: int = 0


@dataclass
class AttackConfig:
    attack_type: str = "none"  # none | sign_flip | gaussian | model_replacement | zero | label_flip
    malicious_fraction: float = 0.0
    attack_scale: float = 5.0
    label_flip_probability: float = 1.0
    # natural_fixed_clients (historical): a fixed random set of clients is malicious in every
    #   round, so exposure depends on which clients the selection policy prefers.
    # exposure_controlled: in each round exactly round(fraction * selected) of the SELECTED
    #   clients (chosen from a per-(seed, round) stream) are attackers, so every selection
    #   policy faces the same attacker exposure.
    assignment: str = "natural_fixed_clients"


@dataclass
class FailureConfig:
    enabled: bool = True
    client_failure_probability: float = 0.05
    recovery_enabled: bool = True
    recovery_weight_factor: float = 0.5
    detection_delay_ms: float = 20.0
    reconstruction_time_ms: float = 35.0
    accuracy_recovery_target_ratio: float = 0.95
    recovery_metric: str = "f1"  # accuracy | f1 | balanced_accuracy
    recovery_min_future_rounds: int = 1
    # Recovery is assessed on a short moving average rather than a single noisy
    # validation point.
    recovery_smoothing_window: int = 3
    # Experimental variant C: cap on the COLLECTIVE share of retained surrogate
    # (imputed) updates in the aggregation weights. None = historical behaviour.
    surrogate_total_weight_cap: float | None = None


@dataclass
class RoutingConfig:
    enabled: bool = True
    num_edges: int = 3
    alpha_latency: float = 0.4
    beta_stability: float = 0.3
    gamma_security: float = 0.3
    dynamic_sigma: float = 0.025
    link_outage_probability: float = 0.01
    packets_per_update: int = 100
    # top_k (historical deterministic routing) | uniform_random | coverage_aware
    selection_policy: str = "top_k"
    # coverage_aware utility = route_score - coverage_penalty * (times selected) / (round-1)
    coverage_penalty: float = 0.5
    # independent_draws (historical: packet reception and update delivery are separate
    # random events) | packet_coupled (update delivered iff every packet is received within
    # 1 + max_retransmissions transmissions)
    delivery_model: str = "independent_draws"
    max_retransmissions: int = 2
    retransmission_rtt_factor: float = 2.0
    # sequential (historical shared generators) | matched (every random draw is derived from
    # (seed, round, client), so exogenous traces do not depend on who else was selected)
    trace_mode: str = "sequential"


@dataclass
class ExperimentConfig:
    name: str = "unsw_fl_experiment_v4"
    method_name: str = "proposed"
    output_dir: str = "results"
    seed: int = 42
    device: str = "auto"
    deterministic: bool = True
    save_probabilities: bool = True
    create_plots: bool = True
    early_stopping_patience: int | None = 6
    early_stopping_min_rounds: int = 15
    early_stopping_min_delta: float = 1e-4
    # Validation-only mode: the test partition is never loaded, predicted on,
    # used for threshold selection, or exported. Final metrics are computed on
    # the validation partition only.
    validation_only: bool = False
    # Identifier of the exact algorithm variant (written into run metadata).
    variant_name: str = "reference_6a"
    # Per-round forensic diagnostics (aggregate/applied/velocity norms and cosines, saved
    # global states). Logging only; no effect on training.
    save_round_diagnostics: bool = False
    # Version tag written into every run (reference_v1_historical | corrected_v2_phase6c).
    algorithm_version: str = "reference_v1_historical"
    # When set, all artefacts are written directly into this directory (one immutable
    # directory per arm/seed) instead of output_dir/name/method_name/seed_N.
    exact_output_dir: str | None = None


@dataclass
class Config:
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    fl: FLConfig = field(default_factory=FLConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)
    attack: AttackConfig = field(default_factory=AttackConfig)
    failure: FailureConfig = field(default_factory=FailureConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)

    def validate(self) -> None:
        if self.data.dataset_name not in {"unsw_nb15", "ciciot2023"}:
            raise ValueError("data.dataset_name must be 'unsw_nb15' or 'ciciot2023'")
        if not 0 < self.data.validation_fraction < 1:
            raise ValueError("data.validation_fraction must be in (0, 1)")
        if self.data.dataset_name == "ciciot2023":
            if not self.data.validation_csv:
                raise ValueError("CICIoT2023 requires data.validation_csv")
            if self.data.enable_calibrated_evaluation:
                raise ValueError(
                    "CICIoT2023 uses an explicit validation split; "
                    "data.enable_calibrated_evaluation must be false"
                )
        if self.data.enable_calibrated_evaluation and not (
            0 < self.data.calibration_fraction_of_test < 1
        ):
            raise ValueError("data.calibration_fraction_of_test must be in (0, 1)")
        if self.fl.num_clients < 1:
            raise ValueError("fl.num_clients must be at least 1")
        if not 1 <= self.fl.clients_per_round <= self.fl.num_clients:
            raise ValueError("fl.clients_per_round must be in [1, num_clients]")
        if self.fl.rounds < 1 or self.fl.local_epochs < 1:
            raise ValueError("fl.rounds and fl.local_epochs must be positive")
        if self.fl.batch_size < 1:
            raise ValueError("fl.batch_size must be positive")
        if self.fl.learning_rate <= 0:
            raise ValueError("fl.learning_rate must be positive")
        if self.fl.server_learning_rate <= 0:
            raise ValueError("fl.server_learning_rate must be positive")
        if not 0 <= self.fl.server_momentum < 1:
            raise ValueError("fl.server_momentum must be in [0, 1)")
        if self.fl.partition not in {"iid", "dirichlet"}:
            raise ValueError("fl.partition must be 'iid' or 'dirichlet'")
        if self.privacy.mode not in {"none", "local_update", "central_client"}:
            raise ValueError("Unsupported privacy.mode")
        if self.privacy.clip_norm <= 0:
            raise ValueError("privacy.clip_norm must be positive")
        if self.privacy.noise_multiplier < 0:
            raise ValueError("privacy.noise_multiplier cannot be negative")
        if self.privacy.target_epsilon is not None and self.privacy.target_epsilon <= 0:
            raise ValueError("privacy.target_epsilon must be positive or null")
        if not 0 < self.privacy.delta < 1:
            raise ValueError("privacy.delta must be in (0, 1)")
        if self.privacy.accountant_sample_rate is not None and not (
            0 < self.privacy.accountant_sample_rate <= 1
        ):
            raise ValueError("privacy.accountant_sample_rate must be in (0, 1]")
        if not 0 < self.privacy.max_client_weight_share <= 1:
            raise ValueError("privacy.max_client_weight_share must be in (0, 1]")
        if self.privacy.adjacency_factor <= 0:
            raise ValueError("privacy.adjacency_factor must be positive")
        if self.threshold.objective not in {
            "fpr_cap",
            "max_f1",
            "max_balanced_accuracy",
            "youden",
        }:
            raise ValueError("Unsupported threshold.objective")
        if not 0 <= self.threshold.max_fpr <= 1:
            raise ValueError("threshold.max_fpr must be in [0, 1]")
        if not 0 <= self.threshold.min_recall <= 1:
            raise ValueError("threshold.min_recall must be in [0, 1]")
        if self.threshold.grid_size < 3:
            raise ValueError("threshold.grid_size must be at least 3")
        if not self.threshold.operating_fpr_caps:
            raise ValueError("threshold.operating_fpr_caps cannot be empty")
        if any(not 0 < value < 1 for value in self.threshold.operating_fpr_caps):
            raise ValueError("threshold.operating_fpr_caps values must be in (0, 1)")
        if self.threshold.model_selection_metric not in {
            "accuracy",
            "balanced_accuracy",
            "precision",
            "recall_adr",
            "specificity",
            "f1",
            "roc_auc",
            "pr_auc",
        }:
            raise ValueError("Unsupported threshold.model_selection_metric")
        if self.data.validation_split not in {"random_stratified", "group_disjoint"}:
            raise ValueError("data.validation_split must be random_stratified or group_disjoint")
        if not 0.0 <= self.data.threshold_calibration_fraction <= 0.9:
            raise ValueError("data.threshold_calibration_fraction must be in [0, 0.9]")
        if self.aggregation.surrogate_handling not in {"reference", "post_filter_real_only"}:
            raise ValueError("aggregation.surrogate_handling must be reference or post_filter_real_only")
        if self.aggregation.surrogate_handling == "post_filter_real_only" and self.aggregation.method in {"median", "trimmed_mean"}:
            raise ValueError("post_filter_real_only needs a filtering/weighting aggregator (distance_filter, multi_krum, fedavg)")
        if self.aggregation.min_real_updates < 0:
            raise ValueError("aggregation.min_real_updates must be >= 0 (0 disables the guard)")
        if self.attack.assignment not in {"natural_fixed_clients", "exposure_controlled"}:
            raise ValueError("attack.assignment must be natural_fixed_clients or exposure_controlled")
        if self.data.validation_three_way and self.data.threshold_calibration_fraction > 0:
            raise ValueError("validation_three_way and threshold_calibration_fraction are mutually exclusive")
        if self.fl.weighting not in {"sample_proportional", "uniform"}:
            raise ValueError("fl.weighting must be sample_proportional or uniform")
        if self.failure.surrogate_total_weight_cap is not None and not 0.0 < self.failure.surrogate_total_weight_cap < 1.0:
            raise ValueError("failure.surrogate_total_weight_cap must be in (0, 1) or null")
        if self.routing.selection_policy not in {"top_k", "uniform_random", "coverage_aware"}:
            raise ValueError("routing.selection_policy must be top_k, uniform_random or coverage_aware")
        if self.routing.delivery_model not in {"independent_draws", "packet_coupled"}:
            raise ValueError("routing.delivery_model must be independent_draws or packet_coupled")
        if self.routing.trace_mode not in {"sequential", "matched"}:
            raise ValueError("routing.trace_mode must be sequential or matched")
        if self.routing.max_retransmissions < 0 or self.routing.coverage_penalty < 0:
            raise ValueError("routing.max_retransmissions and coverage_penalty must be non-negative")
        if self.routing.selection_policy != "top_k" and not self.routing.enabled:
            raise ValueError("a non-default selection_policy requires routing.enabled=true")
        if self.aggregation.method not in {
            "fedavg",
            "median",
            "trimmed_mean",
            "distance_filter",
            "multi_krum",
        }:
            raise ValueError("Unsupported aggregation.method")
        if self.privacy.mode == "central_client" and self.aggregation.method in {
            "median",
            "trimmed_mean",
        }:
            # The central-DP path re-aggregates survivors with clipped, capped
            # FedAvg; a median/trimmed-mean estimate would be silently discarded.
            raise ValueError(
                "privacy.mode='central_client' is incompatible with "
                f"aggregation.method='{self.aggregation.method}': the robust "
                "estimate would be replaced by clipped FedAvg. Use "
                "distance_filter, multi_krum or fedavg."
            )
        if not 0 <= self.attack.malicious_fraction < 1:
            raise ValueError("attack.malicious_fraction must be in [0, 1)")
        if not 0 <= self.failure.client_failure_probability <= 1:
            raise ValueError("failure probability must be in [0, 1]")
        if self.failure.recovery_metric not in {"accuracy", "f1", "balanced_accuracy"}:
            raise ValueError("Unsupported failure.recovery_metric")
        if self.failure.recovery_min_future_rounds < 1:
            raise ValueError("failure.recovery_min_future_rounds must be at least 1")
        if self.failure.recovery_smoothing_window < 1:
            raise ValueError("failure.recovery_smoothing_window must be at least 1")
        if abs(
            self.routing.alpha_latency
            + self.routing.beta_stability
            + self.routing.gamma_security
            - 1.0
        ) > 1e-6:
            raise ValueError("Routing weights must sum to 1")
        if self.experiment.early_stopping_patience is not None and (
            self.experiment.early_stopping_patience < 1
        ):
            raise ValueError("early_stopping_patience must be positive or null")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def clone(self) -> "Config":
        return deepcopy(self)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        cfg = cls()
        for section_name, values in raw.items():
            if not hasattr(cfg, section_name):
                raise ValueError(f"Unknown config section: {section_name}")
            section = getattr(cfg, section_name)
            if not isinstance(values, dict):
                raise ValueError(f"Section {section_name} must be a mapping")
            for key, value in values.items():
                if not hasattr(section, key):
                    raise ValueError(f"Unknown config key: {section_name}.{key}")
                current = getattr(section, key)
                if isinstance(current, tuple) and isinstance(value, list):
                    value = tuple(value)
                setattr(section, key, value)
        cfg.validate()
        return cfg

    def save_yaml(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(self.to_dict(), handle, sort_keys=False, allow_unicode=True)
