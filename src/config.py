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


@dataclass
class AttackConfig:
    attack_type: str = "none"  # none | sign_flip | gaussian | model_replacement | zero | label_flip
    malicious_fraction: float = 0.0
    attack_scale: float = 5.0
    label_flip_probability: float = 1.0


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
