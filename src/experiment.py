from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd
import torch
from tqdm import trange

from .aggregation import AggregationResult, aggregate_updates, fedavg
from .attacks import apply_update_attack
from .client import Client
from .config import Config
from .data import DatasetBundle, load_dataset
from .metrics import (
    binary_classification_metrics,
    evaluate_operating_points,
    oracle_recall_at_fpr_caps,
    select_decision_threshold,
)
from .model import ANN
from .network import DynamicEdgeCloudNetwork
from .history_selector import HistorySelector
from .partitioning import make_partitions, split_client_holdout_by_mask
from .plotting import create_run_plots
from .privacy import (
    add_gaussian_noise,
    approximate_rdp_epsilon,
    calibrate_noise_multiplier,
    capped_normalized_weights,
    group_capped_normalized_weights,
    clip_update,
)
from .recovery import recover_failed_update
from .server import Server
from .metric_accounting import reconcile_network_events
from .state import State, state_l2_norm, state_num_bytes, state_to_vector, subtract_states
from .utils import resolve_device, save_json, set_global_seed


RECOVERY_COLUMNS = [
    "failure_round",
    "client_id",
    "recovery_applied",
    "simulated_recovery_time_ms",
    "recovery_metric",
    "recovery_smoothing_window",
    "pre_failure_metric",
    "target_metric",
    "post_failure_metric",
    "post_failure_metric_smoothed",
    "performance_recovered_round",
    "performance_recovery_rounds",
]

AGGREGATION_COLUMNS = [
    "round",
    "update_index",
    "client_id",
    "is_recovered_update",
    "is_malicious_client",
    "effective_malicious_update",
    "kept",
    "pre_clip_l2_norm",
    "post_clip_l2_norm",
    "diagnostic_distance_or_score",
    "actual_aggregation_method",
    "raw_weight",
    "applied_weight_share",
]

NETWORK_COLUMNS = [
    "round",
    "client_id",
    "edge_id",
    "end_to_end_delay_ms",
    "pdr",
    "path_stability",
    "security_score",
    "transfer_efficiency_mbps",
    "update_bytes",
    "update_delivered",
    "explicit_client_failure",
    "selected",
    "malicious",
    "received_by_server",
    "expected_pdr",
    "delivery_draw",
    "packets_lost",
    "explicit_failure_draw",
    "failure_reason",
    "propagation_latency_ms",
    "serialization_ms",
    "jitter_ms",
    "bandwidth_mbps",
    "bytes_on_wire",
    "retransmission_rounds",
    "packets_unrecovered",
]


def _moving_average(values: Sequence[float], window: int) -> float:
    finite = [float(value) for value in values if np.isfinite(value)]
    if not finite:
        return float("nan")
    return float(np.mean(finite[-max(1, int(window)) :]))


def _model_factory(cfg: Config, input_dim: int):
    def factory() -> ANN:
        return ANN(
            input_dim=input_dim,
            hidden_dims=cfg.model.hidden_dims,
            dropout=cfg.model.dropout,
            num_classes=2,
        )

    return factory


def _dataset_summary(bundle: DatasetBundle) -> Dict[str, int | float]:
    return {
        "raw_training_rows": bundle.raw_train_rows,
        "raw_testing_rows": bundle.raw_test_rows,
        "training_rows_after_validation_split": len(bundle.y_train),
        "validation_rows": len(bundle.y_val),
        "testing_rows_used_standard_benchmark": len(bundle.y_test),
        "calibration_rows_secondary_protocol": len(bundle.y_calibration),
        "calibrated_final_test_rows_secondary_protocol": len(bundle.y_calibrated_test),
        "calibrated_evaluation_enabled": bool(bundle.calibration_enabled),
        "original_column_count": bundle.original_column_count,
        "selected_raw_input_features": bundle.selected_raw_feature_count,
        "encoded_feature_dimension": bundle.X_train.shape[1],
        "training_normal": int((bundle.y_train == 0).sum()),
        "training_attack": int((bundle.y_train == 1).sum()),
        "validation_normal": int((bundle.y_val == 0).sum()),
        "validation_attack": int((bundle.y_val == 1).sum()),
        "testing_normal": int((bundle.y_test == 0).sum()),
        "testing_attack": int((bundle.y_test == 1).sum()),
        "calibration_normal": int((bundle.y_calibration == 0).sum()),
        "calibration_attack": int((bundle.y_calibration == 1).sum()),
        "calibrated_test_normal": int((bundle.y_calibrated_test == 0).sum()),
        "calibrated_test_attack": int((bundle.y_calibrated_test == 1).sum()),
    }


def _per_attack_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    categories: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    predictions = (probabilities >= threshold).astype(int)
    rows = []
    categories = np.asarray(categories).astype(str)
    for category in sorted(np.unique(categories)):
        mask = categories == category
        count = int(mask.sum())
        if count == 0:
            continue
        if category.lower() == "normal" or np.all(y_true[mask] == 0):
            rate = float((predictions[mask] == 1).mean())
            metric_name = "false_positive_rate"
        else:
            rate = float((predictions[mask] == 1).mean())
            metric_name = "detection_rate"
        rows.append(
            {
                "attack_category": category,
                "samples": count,
                "metric": metric_name,
                "rate": rate,
                "decision_threshold": threshold,
            }
        )
    return pd.DataFrame(rows)


def _validation_metrics(
    cfg: Config,
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[Dict[str, float], Dict[str, float | bool | str]]:
    default_metrics = binary_classification_metrics(y_true, probabilities, threshold=0.5)
    if not cfg.threshold.enabled:
        return default_metrics, {
            **default_metrics,
            "objective": "fixed_0.5",
            "constraint_feasible": True,
            "max_fpr_constraint": cfg.threshold.max_fpr,
            "min_recall_constraint": cfg.threshold.min_recall,
        }
    selected = select_decision_threshold(
        y_true,
        probabilities,
        objective=cfg.threshold.objective,
        max_fpr=cfg.threshold.max_fpr,
        min_recall=cfg.threshold.min_recall,
        grid_size=cfg.threshold.grid_size,
    )
    return default_metrics, selected


def _safe_aggregate(
    updates: Sequence[State],
    weights: Sequence[float],
    cfg: Config,
) -> tuple[AggregationResult, str]:
    requested = cfg.aggregation.method
    try:
        result = aggregate_updates(
            updates,
            weights,
            method=requested,
            trim_ratio=cfg.aggregation.trim_ratio,
            distance_k=cfg.aggregation.distance_k,
            byzantine_assumption=cfg.aggregation.byzantine_assumption,
        )
        return result, requested
    except ValueError as exc:
        # Multi-Krum can become mathematically undefined after failures. Falling
        # back keeps a run reproducible and records the actual method used.
        if requested == "multi_krum":
            fallback = "distance_filter" if len(updates) >= 3 else "fedavg"
            result = aggregate_updates(
                updates,
                weights,
                method=fallback,
                trim_ratio=cfg.aggregation.trim_ratio,
                distance_k=cfg.aggregation.distance_k,
                byzantine_assumption=0,
            )
            return result, f"{fallback}_fallback_from_multi_krum:{exc}"
        raise


def _selection_mechanism(cfg: Config) -> str:
    if cfg.routing.enabled:
        if cfg.routing.selection_policy == "uniform_random":
            return "uniform_without_replacement_fixed_size_with_intelligent_edge_routing"
        if cfg.routing.selection_policy == "coverage_aware":
            return "deterministic_coverage_aware_top_k"
        return "deterministic_top_k_by_route_score"
    return "uniform_without_replacement_fixed_size"


def _evaluate_protocol(cfg: Config, bundle: DatasetBundle, server: Server):
    """Validation-side evaluation. With a calibration partition the decision threshold is
    selected on the CALIBRATION observations only and applied to the independent
    EVALUATION observations; otherwise (historical) both use the same observations."""
    p_val = server.predict_probabilities(bundle.X_val)
    if bundle.X_thr is None or bundle.y_thr is None or len(bundle.y_thr) == 0:
        default, selected = _validation_metrics(cfg, bundle.y_val, p_val)
        selected = dict(selected)
        selected["threshold_source"] = "same_validation_observations"
        return default, selected, p_val
    p_thr = server.predict_probabilities(bundle.X_thr)
    _, calibration = _validation_metrics(cfg, bundle.y_thr, p_thr)
    threshold = float(calibration["threshold"])
    default = binary_classification_metrics(bundle.y_val, p_val, 0.5)
    selected = dict(binary_classification_metrics(bundle.y_val, p_val, threshold))
    selected.update({
        "objective": calibration.get("objective"),
        "constraint_feasible": bool(calibration["constraint_feasible"]),
        "max_fpr_constraint": calibration.get("max_fpr_constraint", cfg.threshold.max_fpr),
        "min_recall_constraint": calibration.get("min_recall_constraint", cfg.threshold.min_recall),
        "threshold_source": "separate_calibration_partition",
        "calibration_fpr": float(calibration["fpr"]),
        "calibration_recall_adr": float(calibration["recall_adr"]),
        "calibration_f1": float(calibration["f1"]),
        "calibration_rows": int(len(bundle.y_thr)),
    })
    if bundle.X_rep is not None and bundle.y_rep is not None and len(bundle.y_rep):
        # logged for transparency only; never used for any selection decision
        rep = binary_classification_metrics(bundle.y_rep, server.predict_probabilities(bundle.X_rep), threshold)
        for key in ("roc_auc", "pr_auc", "f1", "fpr", "recall_adr", "precision"):
            selected[f"rep_{key}"] = float(rep.get(key, float("nan")))
    return default, selected, p_val


def _privacy_plan(cfg: Config) -> Dict[str, float | str | bool | None]:
    if cfg.privacy.mode == "none":
        return {
            "privacy_mode": "none",
            "privacy_enabled": False,
            "effective_noise_multiplier": 0.0,
            "accountant_sample_rate": 0.0,
            "planned_steps": cfg.fl.rounds,
            "planned_epsilon_estimate": 0.0,
            "delta": cfg.privacy.delta,
            "target_epsilon": None,
            "accounting_note": "Privacy disabled.",
            "subsampling_amplification_valid": False,
            "poisson_subsampling_assumption_satisfied": False,
            "epsilon_is_certified_guarantee": False,
            "selection_mechanism": _selection_mechanism(cfg),
        }

    sample_rate = (
        cfg.privacy.accountant_sample_rate
        if cfg.privacy.accountant_sample_rate is not None
        else cfg.fl.clients_per_round / cfg.fl.num_clients
    )
    noise_multiplier = cfg.privacy.noise_multiplier
    if cfg.privacy.auto_calibrate_noise and cfg.privacy.target_epsilon is not None:
        noise_multiplier = calibrate_noise_multiplier(
            target_epsilon=cfg.privacy.target_epsilon,
            steps=cfg.fl.rounds,
            delta=cfg.privacy.delta,
            sample_rate=sample_rate,
        )
    planned_epsilon = approximate_rdp_epsilon(
        noise_multiplier,
        cfg.fl.rounds,
        cfg.privacy.delta,
        sample_rate,
    )
    return {
        "privacy_mode": cfg.privacy.mode,
        "privacy_enabled": True,
        "effective_noise_multiplier": float(noise_multiplier),
        "accountant_sample_rate": float(sample_rate),
        "planned_steps": cfg.fl.rounds,
        "planned_epsilon_estimate": float(planned_epsilon),
        "delta": cfg.privacy.delta,
        "target_epsilon": cfg.privacy.target_epsilon,
        "auto_calibrated": cfg.privacy.auto_calibrate_noise,
        "clip_norm": cfg.privacy.clip_norm,
        "max_client_weight_share": cfg.privacy.max_client_weight_share,
        "adjacency_factor": cfg.privacy.adjacency_factor,
        # Subsampling amplification requires client selection that is random
        # and secret. Deterministic top-k routed selection re-selects the same
        # clients, so q=clients_per_round/num_clients does not hold for them.
        "client_selection_is_random": not cfg.routing.enabled,
        # Neither selection scheme is Poisson subsampling: routed selection is
        # deterministic top-k, the alternative is a fixed-size uniform draw without
        # replacement. The RDP routine assumes Poisson sampling, so amplification
        # by subsampling is NOT established for either; epsilon is a diagnostic
        # estimate, not a certified guarantee.
        "selection_mechanism": _selection_mechanism(cfg),
        "poisson_subsampling_assumption_satisfied": False,
        "subsampling_amplification_valid": False,
        "epsilon_is_certified_guarantee": False,
        "accounting_note": (
            "RDP Poisson-sampling estimate. Routed client selection and the "
            "data-dependent robust filter are not covered by a formal proof; "
            "report this value as an estimated privacy budget."
        ),
    }


def _write_run_metadata(
    cfg: Config,
    run_dir: Path,
    round_df: pd.DataFrame,
    privacy_plan: Dict,
    privacy_steps: int,
    early_stopped: bool,
) -> None:
    methods = []
    if "actual_aggregation_method" in round_df:
        methods = sorted(round_df["actual_aggregation_method"].dropna().astype(str).unique().tolist())
    save_json(
        {
            "median_convention": (
                "true median: mean of the two middle order statistics for even counts "
                "(src.aggregation.true_median); torch.median (lower median) is not used"
            ),
            "aggregation": {
                "requested": cfg.aggregation.method,
                "actual_methods_used": methods,
                "distance_k": cfg.aggregation.distance_k,
                "trim_ratio": cfg.aggregation.trim_ratio,
                "byzantine_assumption": cfg.aggregation.byzantine_assumption,
            },
            "privacy": {
                **privacy_plan,
                "mechanism": (
                    "central Gaussian noise added to the clipped, weight-capped aggregate "
                    "released after robust filtering; server momentum is post-processing"
                ),
                "release_count": int(privacy_steps),
                "epsilon_label": "diagnostic RDP estimate under a Poisson-sampling assumption",
            },
            "missing_update_handling": {
                "enabled": cfg.failure.recovery_enabled,
                "terminology": (
                    "surrogate imputation: a coordinate-wise true median of received updates "
                    "substitutes for a missing update; no information about the missing "
                    "client's private data is recovered"
                ),
                "weight_factor": cfg.failure.recovery_weight_factor,
            },
            "routing_enabled": cfg.routing.enabled,
            "variant_name": cfg.experiment.variant_name,
            "algorithm_version": cfg.experiment.algorithm_version,
            "attack_assignment": cfg.attack.assignment,
            "surrogate_handling": cfg.aggregation.surrogate_handling,
            "weight_cap_statement": (
                "A strict per-client weight cap c is mathematically infeasible whenever fewer than 1/c "
                "updates are retained (the maximum weight is at least 1/n); the effective cap is max(c, 1/n). "
                "Per-round requested/min-feasible/effective/actual values are logged."
            ),
            "privacy_claim_statement": (
                "The Gaussian step is an empirical noise-injection defence. The reported epsilon is a "
                "diagnostic RDP estimate that assumes Poisson client sampling, which is not satisfied; it is "
                "NOT a certified differential-privacy guarantee."
            ),
            "algorithm_spec": {
                "selection_policy": cfg.routing.selection_policy,
                "coverage_penalty": cfg.routing.coverage_penalty,
                "delivery_model": cfg.routing.delivery_model,
                "max_retransmissions": cfg.routing.max_retransmissions,
                "trace_mode": cfg.routing.trace_mode,
                "weighting": cfg.fl.weighting,
                "imputation": ("none" if not cfg.failure.recovery_enabled else "coordinate_median_surrogate"),
                "recovery_weight_factor": cfg.failure.recovery_weight_factor,
                "surrogate_total_weight_cap": cfg.failure.surrogate_total_weight_cap,
                "threshold_calibration_fraction": cfg.data.threshold_calibration_fraction,
                "privacy_mode": cfg.privacy.mode,
                "server_momentum": cfg.fl.server_momentum,
                "server_learning_rate": cfg.fl.server_learning_rate,
            },
            "validation_only": cfg.experiment.validation_only,
            "test_data_loaded": not cfg.experiment.validation_only,
            "seed": cfg.experiment.seed,
            "rounds_executed": int(len(round_df) - 1),
            "early_stopped": bool(early_stopped),
            "versions": {
                "torch": torch.__version__,
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
        },
        run_dir / "run_metadata.json",
    )


def _finalize_validation_only(
    cfg: Config,
    bundle: DatasetBundle,
    server: Server,
    best_state: State,
    best_round: int,
    run_dir: Path,
    round_df: pd.DataFrame,
    privacy_plan: Dict,
    privacy_steps: int,
    early_stopped: bool,
) -> Path:
    """Final reporting for validation-only runs: no test data exists in `bundle`."""
    three_way = bundle.X_rep is not None and bundle.y_rep is not None and len(bundle.y_rep) > 0
    report_y = bundle.y_rep if three_way else bundle.y_val
    # last-round model (reported next to the best checkpoint to expose selection optimism)
    last_state = server.get_global_state()
    torch.save(last_state, run_dir / "last_model_state.pt")
    _, last_selected, _ = _evaluate_protocol(cfg, bundle, server)
    last_report = None
    if three_way:
        last_report = binary_classification_metrics(
            report_y, server.predict_probabilities(bundle.X_rep), float(last_selected["threshold"])
        )
    server.load_global_state(best_state, reset_optimizer_state=True)
    default_metrics, selected, probabilities = _evaluate_protocol(cfg, bundle, server)
    p_report = server.predict_probabilities(bundle.X_rep) if three_way else probabilities
    report_at_selected = binary_classification_metrics(report_y, p_report, float(selected["threshold"]))

    def plain(mapping):
        out = {}
        for key, value in mapping.items():
            if isinstance(value, (np.bool_, bool)):
                out[key] = bool(value)
            elif isinstance(value, (np.integer,)):
                out[key] = int(value)
            elif isinstance(value, (np.floating, float)):
                out[key] = float(value)
            elif isinstance(value, (int, str)):
                out[key] = value
        return out

    # Prespecified FPR targets (not chosen from any result). Thresholds come from the
    # calibration partition when it exists; the "same observations" numbers are shown
    # only to quantify the optimism of the historical protocol.
    has_calibration = bundle.X_thr is not None and bundle.y_thr is not None and len(bundle.y_thr) > 0
    p_calibration = server.predict_probabilities(bundle.X_thr) if has_calibration else None
    threshold_diagnostics = {}
    for target in (0.01, 0.05, 0.15):
        entry = {"target_fpr": target}
        same = select_decision_threshold(
            report_y, p_report, objective="fpr_cap", max_fpr=target, min_recall=0.0,
            grid_size=cfg.threshold.grid_size,
        )
        entry["same_observation_optimistic"] = plain({
            k: same[k] for k in ("threshold", "fpr", "recall_adr", "precision", "f1", "constraint_feasible")})
        if has_calibration:
            cal = select_decision_threshold(
                bundle.y_thr, p_calibration, objective="fpr_cap", max_fpr=target, min_recall=0.0,
                grid_size=cfg.threshold.grid_size,
            )
            held = binary_classification_metrics(report_y, p_report, threshold=float(cal["threshold"]))
            entry["calibration_partition"] = plain({
                k: cal[k] for k in ("threshold", "fpr", "recall_adr", "precision", "f1", "constraint_feasible")})
            entry["independent_evaluation"] = plain({
                k: held[k] for k in ("threshold", "fpr", "recall_adr", "precision", "f1", "tn", "fp", "fn", "tp")})
            entry["fpr_shift_evaluation_minus_calibration"] = float(held["fpr"] - cal["fpr"])
        threshold_diagnostics[f"{int(round(target * 100))}pct"] = entry
    save_json(threshold_diagnostics, run_dir / "threshold_diagnostics.json")

    final = {
        "protocol": "validation_only",
        "test_data_loaded": False,
        "threshold_source": selected.get("threshold_source"),
        "best_round": int(best_round),
        "validation_rows": int(len(bundle.y_val)),
        "selected_operating_point": plain(selected),
        "default_threshold_0_5": plain(default_metrics),
        "threshold_diagnostics": threshold_diagnostics,
        "partitions": {
            "calibration_rows": int(len(bundle.y_thr)) if bundle.y_thr is not None else 0,
            "selection_rows": int(len(bundle.y_val)),
            "report_rows": int(len(report_y)),
            "three_way": bool(three_way),
        },
        "report_partition_at_selected_threshold": plain(report_at_selected),
        "last_round_selection_partition": plain(last_selected),
        "last_round_report_partition": plain(last_report) if last_report is not None else None,
    }
    save_json(final, run_dir / "final_validation_metrics.json")
    pd.DataFrame(
        [[report_at_selected["tn"], report_at_selected["fp"]], [report_at_selected["fn"], report_at_selected["tp"]]],
        index=["true_normal", "true_attack"],
        columns=["pred_normal", "pred_attack"],
    ).to_csv(run_dir / "confusion_matrix_validation.csv")
    if cfg.experiment.save_probabilities:
        pd.DataFrame({"y_true": bundle.y_val, "probability_attack": probabilities}).to_csv(
            run_dir / "validation_predictions.csv", index=False
        )
    _write_run_metadata(cfg, run_dir, round_df, privacy_plan, privacy_steps, early_stopped)
    return run_dir


def run_experiment(cfg: Config) -> Path:
    cfg.validate()
    set_global_seed(cfg.experiment.seed, cfg.experiment.deterministic)
    device = resolve_device(cfg.experiment.device)

    run_dir = (
        Path(cfg.experiment.exact_output_dir)
        if cfg.experiment.exact_output_dir
        else Path(cfg.experiment.output_dir)
        / cfg.experiment.name
        / cfg.experiment.method_name
        / f"seed_{cfg.experiment.seed}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg.save_yaml(run_dir / "resolved_config.yaml")

    privacy_plan = _privacy_plan(cfg)
    save_json(privacy_plan, run_dir / "privacy_plan.json")
    effective_noise_multiplier = float(privacy_plan["effective_noise_multiplier"])
    accountant_sample_rate = float(privacy_plan["accountant_sample_rate"])

    bundle = load_dataset(
        cfg.data,
        seed=cfg.experiment.seed,
        preprocessor_output=run_dir / "preprocessor.joblib",
        load_test=not cfg.experiment.validation_only,
        holdout_fraction=cfg.fl.client_holdout_fraction,
    )
    dataset_summary = _dataset_summary(bundle)
    save_json(dataset_summary, run_dir / "dataset_summary.json")
    pd.DataFrame([dataset_summary]).to_csv(run_dir / "dataset_summary.csv", index=False)
    pd.DataFrame({"feature_name": bundle.feature_names}).to_csv(
        run_dir / "feature_names.csv", index=False
    )
    if bundle.validation_split_info is not None:
        save_json(bundle.validation_split_info, run_dir / "validation_split_info.json")
    if bundle.train_exclusions is not None:
        bundle.train_exclusions.to_csv(run_dir / "train_conflict_exclusion_manifest.csv", index=False)
    if cfg.data.prepared_metadata_json:
        metadata_path = Path(cfg.data.prepared_metadata_json)
        if metadata_path.exists():
            import shutil
            shutil.copy2(metadata_path, run_dir / "dataset_preparation_metadata.json")

    partitions = make_partitions(
        bundle.y_train,
        num_clients=cfg.fl.num_clients,
        strategy=cfg.fl.partition,
        seed=cfg.experiment.seed,
        dirichlet_alpha=cfg.fl.dirichlet_alpha,
        min_client_samples=cfg.fl.min_client_samples,
    )
    full_partitions = partitions
    if cfg.fl.client_holdout_fraction > 0:
        partitions, _holdout = split_client_holdout_by_mask(full_partitions, bundle.holdout_mask)
    else:
        partitions = full_partitions
    clients: List[Client] = []
    distribution_rows = []
    for client_id, indices in enumerate(partitions):
        client_y = bundle.y_train[indices]
        clients.append(Client(client_id, bundle.X_train[indices], client_y, device=device))
        distribution_rows.append(
            {
                "client_id": client_id,
                "num_samples": len(indices),
                "normal_count": int((client_y == 0).sum()),
                "attack_count": int((client_y == 1).sum()),
                "attack_ratio": float((client_y == 1).mean()),
            }
        )
    pd.DataFrame(distribution_rows).to_csv(run_dir / "client_distribution.csv", index=False)

    rng = np.random.default_rng(cfg.experiment.seed + 2000)
    malicious_count = int(round(cfg.fl.num_clients * cfg.attack.malicious_fraction))
    malicious_clients = set(
        rng.choice(cfg.fl.num_clients, size=malicious_count, replace=False).tolist()
        if malicious_count > 0
        else []
    )
    save_json(
        {
            "attack_type": cfg.attack.attack_type,
            "assignment": cfg.attack.assignment,
            "malicious_clients": sorted(malicious_clients),
        },
        run_dir / "malicious_clients.json",
    )

    model_factory = _model_factory(cfg, bundle.X_train.shape[1])
    server = Server(model_factory(), device=device)
    network = DynamicEdgeCloudNetwork(
        cfg.fl.num_clients,
        cfg.routing,
        cfg.experiment.seed + 3000,
    )
    if cfg.routing.network_data_coupling > 0:
        _minority = 0 if (bundle.y_train == 0).sum() <= (bundle.y_train == 1).sum() else 1
        _driver = np.array([float((bundle.y_train[idx] == _minority).mean()) for idx in full_partitions])
        network.couple_links_to_scores(_driver, cfg.routing.network_data_coupling, cfg.experiment.seed)
    history_selector = (HistorySelector(cfg.fl.num_clients, cfg.routing.alpha_latency, cfg.routing.beta_stability, cfg.routing.ucb_c, seed=cfg.experiment.seed)
                        if cfg.routing.selection_policy == "history_ucb" else None)

    initial_default, initial_selected, initial_probabilities = _evaluate_protocol(cfg, bundle, server)
    round_rows = [
        {
            "round": 0,
            "selected_clients": 0,
            "received_updates": 0,
            "kept_updates": 0,
            "rejected_updates": 0,
            "failed_clients": 0,
            "recovered_clients": 0,
            "malicious_selected": 0,
            "malicious_received": 0,
            "mean_train_loss": np.nan,
            "mean_local_train_seconds": np.nan,
            "round_seconds": 0.0,
            "communication_bytes": 0,
            "mean_end_to_end_delay_ms": np.nan,
            "mean_pdr": np.nan,
            "mean_path_stability": np.nan,
            "mean_security_score": np.nan,
            "mean_transfer_efficiency_mbps": np.nan,
            "mean_recovery_time_ms": np.nan,
            "privacy_epsilon_estimate": 0.0,
            "privacy_noise_std": 0.0,
            "privacy_max_weight_share": 0.0,
            "privacy_clipped_fraction": 0.0,
            "aggregate_signal_l2_norm": 0.0,
            "privacy_noise_l2_norm": 0.0,
            "privacy_noise_to_signal_ratio": 0.0,
            "server_applied_update_l2_norm": 0.0,
            "selected_threshold": float(initial_selected["threshold"]),
            "threshold_constraint_feasible": bool(initial_selected["constraint_feasible"]),
            **{f"val_{key}": value for key, value in initial_selected.items() if isinstance(value, (int, float, np.number, bool))},
            **{f"val_default_{key}": value for key, value in initial_default.items()},
        }
    ]
    network_rows: List[Dict] = []
    recovery_events: List[Dict] = []
    aggregation_rows: List[Dict] = []
    pending_performance_recovery: List[Dict] = []

    selection_metric = cfg.threshold.model_selection_metric
    best_score = float(initial_selected[selection_metric])
    best_val_f1 = float(initial_selected["f1"])
    best_round = 0
    best_threshold = float(initial_selected["threshold"])
    best_threshold_feasible = bool(initial_selected["constraint_feasible"])
    best_validation_threshold_fpr = float(initial_selected["fpr"])
    best_validation_threshold_recall = float(initial_selected["recall_adr"])
    best_validation_threshold_f1 = float(initial_selected["f1"])
    recovery_metric_history: List[float] = [
        float(initial_selected[cfg.failure.recovery_metric])
    ]
    best_state = server.get_global_state()
    torch.save(best_state, run_dir / "best_model_state.pt")
    stale_rounds = 0
    privacy_steps = 0
    early_stopped = False
    selection_counts = np.zeros(cfg.fl.num_clients)
    assignment_rows: List[Dict] = []
    diag_rows: List[Dict] = []
    diag_prev: Dict[str, torch.Tensor] = {}
    if cfg.experiment.save_round_diagnostics:
        (run_dir / "round_states").mkdir(exist_ok=True)

    update_bytes = state_num_bytes(server.get_global_state())

    for round_number in trange(1, cfg.fl.rounds + 1, desc=cfg.experiment.method_name):
        round_start = time.perf_counter()
        network.update_round(cfg.routing.enabled)
        if cfg.routing.enabled:
            policy = cfg.routing.selection_policy
            if policy == "uniform_random":
                selection_rng = np.random.default_rng([cfg.experiment.seed, 5000, round_number])
                selected_clients = selection_rng.choice(
                    cfg.fl.num_clients, size=cfg.fl.clients_per_round, replace=False
                ).tolist()
            elif policy == "history_ucb":
                selected_clients = history_selector.select(cfg.fl.clients_per_round, round_number)
            elif policy == "coverage_aware":
                selected_clients = network.select_clients_coverage_aware(
                    cfg.fl.clients_per_round, selection_counts, round_number, cfg.routing.coverage_penalty
                )
            else:
                selected_clients = network.select_clients(cfg.fl.clients_per_round)
        else:
            selected_clients = rng.choice(
                cfg.fl.num_clients,
                size=cfg.fl.clients_per_round,
                replace=False,
            ).tolist()
        for chosen in selected_clients:
            selection_counts[chosen] += 1
        if cfg.attack.assignment == "exposure_controlled":
            attackers_this_round = int(round(cfg.attack.malicious_fraction * len(selected_clients)))
            ordering = np.random.default_rng([cfg.experiment.seed, 6000, round_number]).permutation(
                sorted(int(c) for c in selected_clients)
            )
            round_malicious = {int(c) for c in ordering[:attackers_this_round]}
            assignment_rows.extend({"round": round_number, "client_id": c} for c in sorted(round_malicious))
        else:
            round_malicious = malicious_clients

        global_snapshot = server.get_global_state()
        updates: List[State] = []
        weights: List[float] = []
        update_client_ids: List[int] = []
        update_recovered_flags: List[bool] = []
        local_losses: List[float] = []
        local_times: List[float] = []
        failed_clients: List[int] = []
        transfer_delays: List[float] = []
        malicious_received = 0

        for client_id in selected_clients:
            transfer = network.simulate_transfer(client_id, update_bytes)
            # Same RNG consumption as before: the draw happens only when failures
            # are enabled. The draw value is logged for diagnosis.
            if not cfg.failure.enabled:
                failure_draw = float("nan")
            elif cfg.routing.trace_mode == "matched":
                failure_draw = float(
                    np.random.default_rng([cfg.experiment.seed, 2000, round_number, int(client_id)]).random()
                )
            else:
                failure_draw = float(rng.random())
            explicit_failure = bool(
                cfg.failure.enabled
                and failure_draw < cfg.failure.client_failure_probability
            )
            transfer["round"] = round_number
            transfer["explicit_client_failure"] = explicit_failure
            transfer["explicit_failure_draw"] = failure_draw
            transfer["selected"] = True
            transfer["malicious"] = client_id in round_malicious

            network_failure = cfg.failure.enabled and not bool(transfer["update_delivered"])
            if explicit_failure and network_failure:
                transfer["failure_reason"] = "explicit_and_network"
            elif explicit_failure:
                transfer["failure_reason"] = "explicit_client_failure"
            elif network_failure:
                transfer["failure_reason"] = "network_update_not_delivered"
            elif not bool(transfer["update_delivered"]):
                transfer["failure_reason"] = "delivery_draw_failed_but_failure_model_disabled"
            else:
                transfer["failure_reason"] = "none"
            if explicit_failure or network_failure:
                failed_clients.append(client_id)
                transfer["received_by_server"] = False
                network_rows.append(transfer)
                continue

            is_label_flip = (
                client_id in round_malicious
                and cfg.attack.attack_type == "label_flip"
            )
            local_result = clients[client_id].train_local(
                model_factory=model_factory,
                global_state=global_snapshot,
                epochs=cfg.fl.local_epochs,
                batch_size=cfg.fl.batch_size,
                learning_rate=cfg.fl.learning_rate,
                weight_decay=cfg.fl.weight_decay,
                seed=cfg.experiment.seed * 100_000 + round_number * 1000 + client_id,
                privacy_mode=cfg.privacy.mode,
                clip_norm=cfg.privacy.clip_norm,
                noise_multiplier=effective_noise_multiplier,
                label_flip_probability=(
                    cfg.attack.label_flip_probability if is_label_flip else 0.0
                ),
            )
            update = local_result.update
            if client_id in round_malicious and cfg.attack.attack_type != "label_flip":
                attack_generator = torch.Generator(device="cpu")
                attack_generator.manual_seed(
                    cfg.experiment.seed * 200_000 + round_number * 1000 + client_id
                )
                update = apply_update_attack(
                    update,
                    cfg.attack.attack_type,
                    cfg.attack.attack_scale,
                    generator=attack_generator,
                )
                malicious_received += 1
            elif is_label_flip:
                malicious_received += 1

            updates.append(update)
            weights.append(
                float(local_result.num_samples) if cfg.fl.weighting == "sample_proportional" else 1.0
            )
            update_client_ids.append(client_id)
            update_recovered_flags.append(False)
            local_losses.append(local_result.mean_loss)
            local_times.append(local_result.train_seconds)
            transfer_delays.append(float(transfer["end_to_end_delay_ms"]))
            transfer["received_by_server"] = True
            transfer["local_train_seconds"] = local_result.train_seconds
            transfer["local_train_loss"] = local_result.mean_loss
            transfer["flipped_labels"] = local_result.flipped_labels
            network_rows.append(transfer)

        received_count = len(updates)
        # Phase 7 guard (inactive when min_real_updates == 0, the historical behaviour): with fewer than
        # min_real_updates delivered real updates the round abstains.
        aggregation_skipped = bool(
            cfg.aggregation.min_real_updates > 0 and 0 < received_count < cfg.aggregation.min_real_updates
        )
        recovered_count = 0
        recovery_times: List[float] = []
        recovered_by_client: Dict[int, float] = {}
        real_filter_result = None
        real_filter_label = ""
        post_filter_mode = cfg.aggregation.surrogate_handling == "post_filter_real_only"
        if cfg.failure.recovery_enabled and failed_clients and len(updates) >= 2 and not aggregation_skipped:
            average_delay = float(np.mean(transfer_delays)) if transfer_delays else 0.0
            healthy_updates = list(updates)
            if post_filter_mode:
                # corrected variant: robust statistics from REAL updates only; surrogates are then
                # built from the retained real updates (never from, nor into, the filter statistics)
                real_filter_result, real_filter_label = _safe_aggregate(updates, weights, cfg)
                healthy_updates = [updates[i] for i in real_filter_result.kept_indices]
            for failed_client in (failed_clients if len(healthy_updates) >= 2 else []):
                recovery = recover_failed_update(
                    healthy_updates,
                    cfg.failure.detection_delay_ms,
                    cfg.failure.reconstruction_time_ms,
                    average_delay,
                )
                updates.append(recovery.update)
                base_weight = (
                    len(clients[failed_client].y) if cfg.fl.weighting == "sample_proportional" else 1.0
                )
                recovered_weight = base_weight * cfg.failure.recovery_weight_factor
                weights.append(float(recovered_weight))
                update_client_ids.append(failed_client)
                update_recovered_flags.append(True)
                recovered_count += 1
                recovery_times.append(recovery.recovery_time_ms)
                recovered_by_client[failed_client] = recovery.recovery_time_ms

        pre_failure_metric = _moving_average(
            recovery_metric_history, cfg.failure.recovery_smoothing_window
        )
        for failed_client in failed_clients:
            event = {
                "failure_round": round_number,
                "client_id": failed_client,
                "recovery_applied": failed_client in recovered_by_client,
                "simulated_recovery_time_ms": recovered_by_client.get(
                    failed_client, np.nan
                ),
                "recovery_metric": cfg.failure.recovery_metric,
                "recovery_smoothing_window": cfg.failure.recovery_smoothing_window,
                "pre_failure_metric": pre_failure_metric,
                "target_metric": pre_failure_metric
                * cfg.failure.accuracy_recovery_target_ratio,
                "post_failure_metric": np.nan,
                "post_failure_metric_smoothed": np.nan,
                "performance_recovered_round": np.nan,
                "performance_recovery_rounds": np.nan,
            }
            recovery_events.append(event)
            pending_performance_recovery.append(
                {
                    "event_index": len(recovery_events) - 1,
                    "failure_round": round_number,
                    "target": event["target_metric"],
                }
            )

        kept_count = 0
        rejected_count = 0
        actual_aggregation_method = "none"
        applied_shares: List[float] = []
        weight_diag = {
            "weight_cap_requested": float("nan"), "weight_cap_min_feasible": float("nan"),
            "weight_cap_effective": float("nan"), "retained_for_weighting": 0,
            "max_applied_weight_share": float("nan"), "weight_cap_binding": False,
            "weight_cap_infeasible_strict": False, "surrogate_cap_applied": False,
        }
        privacy_noise_std = 0.0
        privacy_max_weight_share = 0.0
        privacy_clipped_fraction = 0.0
        aggregate_signal_l2_norm = 0.0
        privacy_noise_l2_norm = 0.0
        privacy_noise_to_signal_ratio = 0.0
        server_applied_update_l2_norm = 0.0
        if updates and not aggregation_skipped:
            # Robust filtering is performed on un-clipped updates. For central
            # client-level DP, only the surviving updates are then clipped,
            # weight-capped, averaged, and noised. This restores attack
            # separability that was lost when every update was clipped first.
            if post_filter_mode and real_filter_result is not None and recovered_count > 0:
                n_real = len(updates) - recovered_count
                detection_result = AggregationResult(
                    update=real_filter_result.update,
                    kept_indices=list(real_filter_result.kept_indices) + list(range(n_real, len(updates))),
                    rejected_indices=list(real_filter_result.rejected_indices),
                    distances=list(real_filter_result.distances),
                )
                actual_aggregation_method = f"{real_filter_label}[real_only_filter+post_filter_surrogates]"
            else:
                detection_result, actual_aggregation_method = _safe_aggregate(
                    updates, weights, cfg
                )
            kept_indices = detection_result.kept_indices
            kept_count = len(kept_indices)
            rejected_count = len(detection_result.rejected_indices)

            # Variant C: collective cap on the surrogate share among RETAINED updates.
            effective_weights = list(weights)
            surrogate_cap_applied = False
            surrogate_cap = cfg.failure.surrogate_total_weight_cap
            if surrogate_cap is not None:
                kept_real = [i for i in kept_indices if not update_recovered_flags[i]]
                kept_sur = [i for i in kept_indices if update_recovered_flags[i]]
                total_real = sum(weights[i] for i in kept_real)
                total_sur = sum(weights[i] for i in kept_sur)
                if kept_sur and total_real > 0 and total_sur / (total_real + total_sur) > surrogate_cap:
                    scale = surrogate_cap * total_real / ((1.0 - surrogate_cap) * total_sur)
                    for i in kept_sur:
                        effective_weights[i] = weights[i] * scale
                    surrogate_cap_applied = True

            if cfg.privacy.mode == "central_client":
                kept_norms = [
                    float(state_l2_norm(updates[index]).item()) for index in kept_indices
                ]
                privacy_clipped_fraction = float(
                    np.mean([norm > cfg.privacy.clip_norm for norm in kept_norms])
                ) if kept_norms else 0.0
                private_updates = [
                    clip_update(updates[index], cfg.privacy.clip_norm)
                    for index in kept_indices
                ]
                private_raw_weights = [effective_weights[index] for index in kept_indices]
                if cfg.privacy.preserve_surrogate_cap and surrogate_cap is not None:
                    private_weights, privacy_max_weight_share = group_capped_normalized_weights(
                        private_raw_weights,
                        [update_recovered_flags[index] for index in kept_indices],
                        surrogate_cap,
                        cfg.privacy.max_client_weight_share,
                    )
                else:
                    private_weights, privacy_max_weight_share = capped_normalized_weights(
                        private_raw_weights,
                        cfg.privacy.max_client_weight_share,
                    )
                aggregate_before_noise = fedavg(private_updates, private_weights)
                aggregate_signal_l2_norm = float(
                    state_l2_norm(aggregate_before_noise).item()
                )
                sensitivity = (
                    cfg.privacy.clip_norm
                    * privacy_max_weight_share
                    * cfg.privacy.adjacency_factor
                )
                privacy_noise_std = effective_noise_multiplier * sensitivity
                noise_generator = torch.Generator(device="cpu")
                noise_generator.manual_seed(
                    cfg.experiment.seed * 300_000 + round_number
                )
                aggregate = add_gaussian_noise(
                    aggregate_before_noise,
                    std=privacy_noise_std,
                    generator=noise_generator,
                )
                noise_state = subtract_states(aggregate, aggregate_before_noise)
                privacy_noise_l2_norm = float(state_l2_norm(noise_state).item())
                privacy_noise_to_signal_ratio = privacy_noise_l2_norm / max(
                    aggregate_signal_l2_norm, 1e-12
                )
                actual_aggregation_method += "+clipped_capped_fedavg+central_noise"
            else:
                aggregate = detection_result.update
                if (surrogate_cap_applied or (post_filter_mode and recovered_count > 0)) and cfg.aggregation.method not in {"median", "trimmed_mean"}:
                    aggregate = fedavg(
                        [updates[i] for i in kept_indices],
                        [effective_weights[i] for i in kept_indices],
                    )
                aggregate_signal_l2_norm = float(state_l2_norm(aggregate).item())

            # Final weight share each update actually received in the released
            # aggregate (NaN for coordinate-wise robust estimators, which are not
            # weight based).
            if cfg.privacy.mode == "central_client":
                applied_shares = [0.0] * len(updates)
                for position, index in enumerate(kept_indices):
                    applied_shares[index] = float(private_weights[position])
            elif cfg.aggregation.method in {"median", "trimmed_mean"}:
                applied_shares = [float("nan")] * len(updates)
            else:
                kept_total = float(sum(effective_weights[i] for i in kept_indices)) or 1.0
                applied_shares = [0.0] * len(updates)
                for index in kept_indices:
                    applied_shares[index] = float(effective_weights[index]) / kept_total

            retained = len(kept_indices)
            valid_shares = [s for s in applied_shares if not np.isnan(s)]
            max_share = max(valid_shares) if valid_shares else float("nan")
            dp_active = cfg.privacy.mode == "central_client"
            requested_cap = cfg.privacy.max_client_weight_share if dp_active else float("nan")
            weight_diag = {
                "weight_cap_requested": requested_cap,
                "weight_cap_min_feasible": 1.0 / max(retained, 1),
                "weight_cap_effective": (min(1.0, max(requested_cap, 1.0 / max(retained, 1))) if dp_active else float("nan")),
                "retained_for_weighting": retained,
                "max_applied_weight_share": max_share,
                "weight_cap_binding": bool(dp_active and max_share >= max(requested_cap, 1.0 / max(retained, 1)) - 1e-9),
                "weight_cap_infeasible_strict": bool(dp_active and requested_cap < 1.0 / max(retained, 1) - 1e-12),
                "surrogate_cap_applied": surrogate_cap_applied,
            }

            kept_set = set(kept_indices)
            for update_index, client_id in enumerate(update_client_ids):
                diagnostic = (
                    detection_result.distances[update_index]
                    if update_index < len(detection_result.distances)
                    else np.nan
                )
                pre_norm = float(state_l2_norm(updates[update_index]).item())
                post_norm = min(pre_norm, cfg.privacy.clip_norm) if cfg.privacy.mode == "central_client" else pre_norm
                aggregation_rows.append(
                    {
                        "round": round_number,
                        "update_index": update_index,
                        "client_id": client_id,
                        "is_recovered_update": update_recovered_flags[update_index],
                        "is_malicious_client": client_id in round_malicious,
                        "effective_malicious_update": (
                            client_id in round_malicious
                            and not update_recovered_flags[update_index]
                        ),
                        "kept": update_index in kept_set,
                        "pre_clip_l2_norm": pre_norm,
                        "post_clip_l2_norm": post_norm,
                        "diagnostic_distance_or_score": diagnostic,
                        "actual_aggregation_method": actual_aggregation_method,
                        "raw_weight": float(weights[update_index]),
                        "applied_weight_share": applied_shares[update_index],
                    }
                )

            applied_update = server.apply_update(
                aggregate,
                learning_rate=cfg.fl.server_learning_rate,
                momentum=cfg.fl.server_momentum,
            )
            server_applied_update_l2_norm = float(
                state_l2_norm(applied_update).item()
            )
            if cfg.experiment.save_round_diagnostics:
                vec_applied = state_to_vector(applied_update)
                vec_aggregate = state_to_vector(aggregate)
                vec_velocity = state_to_vector(server._velocity)
                vec_params = state_to_vector(server.get_global_state())

                def _cos(a, b):
                    return float(torch.dot(a, b) / (a.norm() * b.norm() + 1e-12))

                diag_rows.append({
                    "round": round_number,
                    "aggregate_norm": float(vec_aggregate.norm()),
                    "applied_norm": float(vec_applied.norm()),
                    "velocity_norm": float(vec_velocity.norm()),
                    "global_param_norm": float(vec_params.norm()),
                    "cos_applied_vs_prev_applied": _cos(vec_applied, diag_prev["applied"]) if "applied" in diag_prev else float("nan"),
                    "cos_aggregate_vs_prev_aggregate": _cos(vec_aggregate, diag_prev["aggregate"]) if "aggregate" in diag_prev else float("nan"),
                    "cos_applied_vs_velocity": _cos(vec_applied, vec_velocity),
                    "selected_clients": ";".join(str(c) for c in selected_clients),
                    "kept_clients": ";".join(str(update_client_ids[i]) for i in kept_indices),
                })
                diag_prev["applied"], diag_prev["aggregate"] = vec_applied, vec_aggregate
                torch.save(server.get_global_state(), run_dir / "round_states" / f"round_{round_number:02d}.pt")
            if cfg.privacy.mode != "none":
                privacy_steps += 1

        val_default, val_selected, val_probabilities = _evaluate_protocol(cfg, bundle, server)
        if diag_rows and diag_rows[-1]["round"] == round_number:
            diag_rows[-1].update({
                "val_mean_probability": float(np.mean(val_probabilities)),
                "val_fraction_predicted_attack_at_0_5": float(np.mean(val_probabilities >= 0.5)),
                "val_roc_auc": float(val_selected.get("roc_auc", float("nan"))),
            })

        current_recovery_raw = float(val_selected[cfg.failure.recovery_metric])
        recovery_metric_history.append(current_recovery_raw)
        current_recovery_value = _moving_average(
            recovery_metric_history, cfg.failure.recovery_smoothing_window
        )
        for event_index in range(len(recovery_events) - len(failed_clients), len(recovery_events)):
            if event_index >= 0 and recovery_events[event_index]["failure_round"] == round_number:
                recovery_events[event_index]["post_failure_metric"] = current_recovery_raw
                recovery_events[event_index]["post_failure_metric_smoothed"] = (
                    current_recovery_value
                )

        unresolved = []
        for pending in pending_performance_recovery:
            earliest = (
                pending["failure_round"] + cfg.failure.recovery_min_future_rounds
            )
            if round_number >= earliest and current_recovery_value >= pending["target"]:
                event = recovery_events[pending["event_index"]]
                event["performance_recovered_round"] = round_number
                event["performance_recovery_rounds"] = (
                    round_number - event["failure_round"]
                )
            else:
                unresolved.append(pending)
        pending_performance_recovery = unresolved

        current_score = float(val_selected[selection_metric])
        improved = current_score > best_score + cfg.experiment.early_stopping_min_delta
        if improved:
            best_score = current_score
            best_val_f1 = float(val_selected["f1"])
            best_round = round_number
            best_threshold = float(val_selected["threshold"])
            best_threshold_feasible = bool(val_selected["constraint_feasible"])
            best_validation_threshold_fpr = float(val_selected["fpr"])
            best_validation_threshold_recall = float(val_selected["recall_adr"])
            best_validation_threshold_f1 = float(val_selected["f1"])
            best_state = server.get_global_state()
            torch.save(best_state, run_dir / "best_model_state.pt")
            stale_rounds = 0
        else:
            stale_rounds += 1

        round_network = [row for row in network_rows if row["round"] == round_number]
        if history_selector is not None:
            for row in round_network:
                _got = bool(row.get("received_by_server", False))
                history_selector.observe(int(row["client_id"]), _got, float(row["end_to_end_delay_ms"]) if _got else None)
        epsilon = (
            approximate_rdp_epsilon(
                effective_noise_multiplier,
                privacy_steps,
                cfg.privacy.delta,
                accountant_sample_rate,
            )
            if cfg.privacy.mode != "none"
            else 0.0
        )
        round_rows.append(
            {
                "round": round_number,
                "selected_clients": len(selected_clients),
                "received_updates": received_count,
                "aggregation_skipped": int(aggregation_skipped),
                "kept_updates": kept_count,
                "rejected_updates": rejected_count,
                "failed_clients": len(failed_clients),
                "recovered_clients": recovered_count,
                # Terminology: these are surrogate (imputed) updates built from the
                # received updates; nothing about the missing client's data is recovered.
                "imputed_clients": recovered_count,
                **weight_diag,
                "communication_bytes_on_wire": int(
                    sum(int(r.get("bytes_on_wire", r["update_bytes"])) for r in round_network)
                ),
                "real_weight_share": float(
                    np.nansum([s for s, f in zip(applied_shares, update_recovered_flags) if not f])
                ),
                "surrogate_weight_share": float(
                    np.nansum([s for s, f in zip(applied_shares, update_recovered_flags) if f])
                ),
                "mean_update_delivered": float(
                    np.mean([bool(r["update_delivered"]) for r in round_network])
                ) if round_network else np.nan,
                "mean_expected_pdr": float(
                    np.mean([r["expected_pdr"] for r in round_network])
                ) if round_network else np.nan,
                "malicious_selected": len(set(selected_clients) & round_malicious),
                "malicious_received": malicious_received,
                "mean_train_loss": float(np.mean(local_losses)) if local_losses else np.nan,
                "mean_local_train_seconds": float(np.mean(local_times)) if local_times else np.nan,
                "round_seconds": time.perf_counter() - round_start,
                "communication_bytes": int(
                    sum(int(row["update_bytes"]) for row in round_network)
                ),
                "mean_end_to_end_delay_ms": float(
                    np.mean([row["end_to_end_delay_ms"] for row in round_network])
                )
                if round_network
                else np.nan,
                "mean_pdr": float(np.mean([row["pdr"] for row in round_network]))
                if round_network
                else np.nan,
                "mean_path_stability": float(
                    np.mean([row["path_stability"] for row in round_network])
                )
                if round_network
                else np.nan,
                "mean_security_score": float(
                    np.mean([row["security_score"] for row in round_network])
                )
                if round_network
                else np.nan,
                "mean_transfer_efficiency_mbps": float(
                    np.mean([row["transfer_efficiency_mbps"] for row in round_network])
                )
                if round_network
                else np.nan,
                "mean_recovery_time_ms": float(np.mean(recovery_times))
                if recovery_times
                else np.nan,
                "privacy_epsilon_estimate": epsilon,
                "privacy_noise_std": privacy_noise_std,
                "privacy_max_weight_share": privacy_max_weight_share,
                "privacy_clipped_fraction": privacy_clipped_fraction,
                "aggregate_signal_l2_norm": aggregate_signal_l2_norm,
                "privacy_noise_l2_norm": privacy_noise_l2_norm,
                "privacy_noise_to_signal_ratio": privacy_noise_to_signal_ratio,
                "server_applied_update_l2_norm": server_applied_update_l2_norm,
                "selected_threshold": float(val_selected["threshold"]),
                "threshold_constraint_feasible": bool(
                    val_selected["constraint_feasible"]
                ),
                "actual_aggregation_method": actual_aggregation_method,
                **{
                    f"val_{key}": value
                    for key, value in val_selected.items()
                    if isinstance(value, (int, float, np.number, bool))
                },
                **{f"val_default_{key}": value for key, value in val_default.items()},
            }
        )

        patience = cfg.experiment.early_stopping_patience
        if (
            patience is not None
            and round_number >= cfg.experiment.early_stopping_min_rounds
            and stale_rounds >= patience
        ):
            early_stopped = True
            break

    for pending in pending_performance_recovery:
        event = recovery_events[pending["event_index"]]
        event["performance_recovered_round"] = np.nan
        event["performance_recovery_rounds"] = np.nan

    round_df = pd.DataFrame(round_rows)
    network_df = pd.DataFrame(network_rows)
    if network_df.empty:
        network_df = pd.DataFrame(columns=NETWORK_COLUMNS)
    recovery_df = pd.DataFrame(recovery_events, columns=RECOVERY_COLUMNS)
    aggregation_df = pd.DataFrame(aggregation_rows, columns=AGGREGATION_COLUMNS)
    round_df.to_csv(run_dir / "round_metrics.csv", index=False)
    network_df.to_csv(run_dir / "network_metrics.csv", index=False)
    recovery_df.to_csv(run_dir / "recovery_events.csv", index=False)
    aggregation_df.to_csv(run_dir / "aggregation_diagnostics.csv", index=False)
    if len(network_df) and "pdr" in network_df:
        # Raises AssertionError if the event / round accounting is inconsistent.
        save_json(
            reconcile_network_events(network_df, round_df, cfg.failure.enabled),
            run_dir / "metric_accounting.json",
        )
    if diag_rows:
        pd.DataFrame(diag_rows).to_csv(run_dir / "round_diagnostics.csv", index=False)
    if assignment_rows:
        pd.DataFrame(assignment_rows).to_csv(run_dir / "attacker_assignment.csv", index=False)

    if cfg.experiment.validation_only:
        return _finalize_validation_only(
            cfg, bundle, server, best_state, best_round, run_dir, round_df,
            privacy_plan, privacy_steps, early_stopped,
        )

    # ------------------------------------------------------------------
    # Final evaluation protocols
    # ------------------------------------------------------------------
    # 1) Standard benchmark: the complete official test partition remains
    #    intact. The threshold is selected only on the training validation set.
    # 2) Secondary calibrated protocol: a deterministic calibration subset of
    #    the official test file selects the threshold, which is then applied to
    #    a disjoint held-out remainder. These results are labelled separately.
    server.load_global_state(best_state, reset_optimizer_state=True)

    best_val_probabilities = server.predict_probabilities(bundle.X_val)
    best_val_default, best_val_selected = _validation_metrics(
        cfg, bundle.y_val, best_val_probabilities
    )
    best_threshold = float(best_val_selected["threshold"])
    best_threshold_feasible = bool(best_val_selected["constraint_feasible"])
    best_validation_threshold_fpr = float(best_val_selected["fpr"])
    best_validation_threshold_recall = float(best_val_selected["recall_adr"])
    best_validation_threshold_f1 = float(best_val_selected["f1"])

    standard_probabilities = server.predict_probabilities(bundle.X_test)
    standard_metrics = binary_classification_metrics(
        bundle.y_test, standard_probabilities, threshold=best_threshold
    )
    standard_default_metrics = binary_classification_metrics(
        bundle.y_test, standard_probabilities, threshold=0.5
    )

    calibration_probabilities = np.asarray([], dtype=float)
    calibrated_test_probabilities = np.asarray([], dtype=float)
    calibrated_threshold = float("nan")
    calibration_selected: Dict[str, float | bool | str] = {}
    calibrated_test_metrics: Dict[str, float] = {}
    calibrated_test_default_metrics: Dict[str, float] = {}
    if bundle.calibration_enabled and len(bundle.y_calibration) and len(bundle.y_calibrated_test):
        calibration_probabilities = server.predict_probabilities(bundle.X_calibration)
        calibrated_test_probabilities = server.predict_probabilities(bundle.X_calibrated_test)
        _, calibration_selected = _validation_metrics(
            cfg, bundle.y_calibration, calibration_probabilities
        )
        calibrated_threshold = float(calibration_selected["threshold"])
        calibrated_test_metrics = binary_classification_metrics(
            bundle.y_calibrated_test,
            calibrated_test_probabilities,
            threshold=calibrated_threshold,
        )
        calibrated_test_default_metrics = binary_classification_metrics(
            bundle.y_calibrated_test,
            calibrated_test_probabilities,
            threshold=0.5,
        )

    # Deployable operating points: thresholds are always selected on a reference
    # set and then transported unchanged to a disjoint evaluation set.
    standard_operating_points = evaluate_operating_points(
        bundle.y_val,
        best_val_probabilities,
        bundle.y_test,
        standard_probabilities,
        cfg.threshold.operating_fpr_caps,
        grid_size=cfg.threshold.grid_size,
        reference_name="training_validation",
        evaluation_name="official_test_full",
    )
    pd.DataFrame(standard_operating_points).to_csv(
        run_dir / "standard_operating_points.csv", index=False
    )

    calibrated_operating_points: list[Dict[str, float | bool | str]] = []
    if bundle.calibration_enabled and len(bundle.y_calibration) and len(bundle.y_calibrated_test):
        calibrated_operating_points = evaluate_operating_points(
            bundle.y_calibration,
            calibration_probabilities,
            bundle.y_calibrated_test,
            calibrated_test_probabilities,
            cfg.threshold.operating_fpr_caps,
            grid_size=cfg.threshold.grid_size,
            reference_name="official_test_calibration_subset",
            evaluation_name="official_test_heldout_subset",
        )
    pd.DataFrame(calibrated_operating_points).to_csv(
        run_dir / "calibrated_operating_points.csv", index=False
    )

    oracle_rows = oracle_recall_at_fpr_caps(
        bundle.y_test,
        standard_probabilities,
        cfg.threshold.operating_fpr_caps,
        grid_size=cfg.threshold.grid_size,
        evaluation_name="official_test_full",
    )
    if bundle.calibration_enabled and len(bundle.y_calibrated_test):
        oracle_rows.extend(
            oracle_recall_at_fpr_caps(
                bundle.y_calibrated_test,
                calibrated_test_probabilities,
                cfg.threshold.operating_fpr_caps,
                grid_size=cfg.threshold.grid_size,
                evaluation_name="official_test_heldout_subset",
            )
        )
    pd.DataFrame(oracle_rows).to_csv(
        run_dir / "oracle_operating_point_diagnostics_NOT_FOR_PRIMARY_REPORTING.csv",
        index=False,
    )

    final_epsilon = (
        approximate_rdp_epsilon(
            effective_noise_multiplier,
            privacy_steps,
            cfg.privacy.delta,
            accountant_sample_rate,
        )
        if cfg.privacy.mode != "none"
        else 0.0
    )
    recovery_successes = (
        int(recovery_df["performance_recovery_rounds"].notna().sum())
        if not recovery_df.empty and "performance_recovery_rounds" in recovery_df
        else 0
    )
    recovery_event_count = len(recovery_df)
    mean_network = {
        "network_mean_end_to_end_delay_ms": float(network_df["end_to_end_delay_ms"].mean())
        if not network_df.empty
        else np.nan,
        "network_mean_pdr": float(network_df["pdr"].mean())
        if not network_df.empty
        else np.nan,
        "network_mean_path_stability": float(network_df["path_stability"].mean())
        if not network_df.empty
        else np.nan,
        "network_mean_security_score": float(network_df["security_score"].mean())
        if not network_df.empty
        else np.nan,
        "network_mean_transfer_efficiency_mbps": float(
            network_df["transfer_efficiency_mbps"].mean()
        )
        if not network_df.empty
        else np.nan,
        "communication_total_bytes": int(round_df["communication_bytes"].sum()),
        "failure_total_clients": int(round_df["failed_clients"].sum()),
        "recovery_total_clients": int(round_df["recovered_clients"].sum()),
        "recovery_event_count": recovery_event_count,
        "recovery_success_count": recovery_successes,
        "recovery_success_rate": (
            recovery_successes / recovery_event_count if recovery_event_count else np.nan
        ),
        "recovery_mean_simulated_time_ms": (
            float(recovery_df["simulated_recovery_time_ms"].dropna().mean())
            if not recovery_df.empty
            and not recovery_df["simulated_recovery_time_ms"].dropna().empty
            else np.nan
        ),
        "recovery_mean_performance_rounds": (
            float(recovery_df["performance_recovery_rounds"].dropna().mean())
            if not recovery_df.empty
            and not recovery_df["performance_recovery_rounds"].dropna().empty
            else np.nan
        ),
    }

    calibrated_fields: Dict[str, float | bool | str | int] = {
        "calibrated_protocol_enabled": bool(bundle.calibration_enabled),
        "calibration_rows": int(len(bundle.y_calibration)),
        "calibrated_test_rows": int(len(bundle.y_calibrated_test)),
        "calibration_fraction_of_official_test": float(
            cfg.data.calibration_fraction_of_test
            if bundle.calibration_enabled
            else 0.0
        ),
        "calibrated_decision_threshold": calibrated_threshold,
    }
    if calibration_selected:
        calibrated_fields.update(
            {
                f"calibration_{key}": value
                for key, value in calibration_selected.items()
                if isinstance(value, (int, float, np.number, bool))
            }
        )
    if calibrated_test_metrics:
        calibrated_fields.update(
            {f"calibrated_test_{key}": value for key, value in calibrated_test_metrics.items()}
        )
        calibrated_fields.update(
            {
                f"calibrated_test_default_{key}": value
                for key, value in calibrated_test_default_metrics.items()
            }
        )
        calibrated_fields["calibrated_fpr_transport_gap"] = float(
            calibrated_test_metrics["fpr"] - float(calibration_selected["fpr"])
        )
        calibrated_fields["calibrated_recall_transport_gap"] = float(
            calibrated_test_metrics["recall_adr"]
            - float(calibration_selected["recall_adr"])
        )

    final = {
        "experiment": cfg.experiment.name,
        "method": cfg.experiment.method_name,
        "seed": cfg.experiment.seed,
        "rounds_completed": int(round_df["round"].max()),
        "early_stopped": early_stopped,
        "best_round": best_round,
        "model_selection_metric": selection_metric,
        "best_validation_score": best_score,
        "best_validation_f1": best_val_f1,
        "best_validation_threshold_fpr": best_validation_threshold_fpr,
        "best_validation_threshold_recall": best_validation_threshold_recall,
        "best_validation_threshold_f1": best_validation_threshold_f1,
        "decision_threshold": best_threshold,
        "threshold_objective": cfg.threshold.objective,
        "threshold_max_fpr": cfg.threshold.max_fpr,
        "threshold_min_recall": cfg.threshold.min_recall,
        "threshold_constraint_feasible_on_validation": best_threshold_feasible,
        "standard_benchmark_protocol": (
            "Complete official testing CSV; threshold selected only on the training validation split."
        ),
        "calibrated_protocol_note": (
            "Secondary analysis only: threshold selected on a stratified calibration subset of the official test CSV and evaluated on its disjoint held-out remainder."
        ),
        "standard_fpr_transport_gap": float(
            standard_metrics["fpr"] - best_validation_threshold_fpr
        ),
        "standard_recall_transport_gap": float(
            standard_metrics["recall_adr"] - best_validation_threshold_recall
        ),
        "privacy_enabled": cfg.privacy.mode != "none",
        "privacy_mode": cfg.privacy.mode,
        "privacy_effective_noise_multiplier": effective_noise_multiplier,
        "privacy_accountant_sample_rate": accountant_sample_rate,
        "privacy_final_epsilon_estimate": final_epsilon,
        "privacy_delta": cfg.privacy.delta,
        "privacy_target_epsilon": (
            cfg.privacy.target_epsilon if cfg.privacy.mode != "none" else None
        ),
        "privacy_clip_norm": cfg.privacy.clip_norm if cfg.privacy.mode != "none" else None,
        "privacy_max_client_weight_share": (
            cfg.privacy.max_client_weight_share if cfg.privacy.mode != "none" else None
        ),
        "mean_privacy_clipped_fraction": float(
            round_df.loc[round_df["round"] > 0, "privacy_clipped_fraction"].mean()
        ) if cfg.privacy.mode != "none" else 0.0,
        "mean_privacy_noise_to_signal_ratio": float(
            round_df.loc[round_df["round"] > 0, "privacy_noise_to_signal_ratio"]
            .replace([np.inf, -np.inf], np.nan)
            .mean()
        ) if cfg.privacy.mode != "none" else 0.0,
        "server_learning_rate": cfg.fl.server_learning_rate,
        "server_momentum": cfg.fl.server_momentum,
        "aggregation_method": cfg.aggregation.method,
        "attack_enabled": (
            cfg.attack.attack_type != "none" and cfg.attack.malicious_fraction > 0
        ),
        "attack_type": cfg.attack.attack_type,
        "malicious_fraction": cfg.attack.malicious_fraction,
        "failure_enabled": cfg.failure.enabled,
        "recovery_enabled": cfg.failure.enabled and cfg.failure.recovery_enabled,
        "failure_probability": (
            cfg.failure.client_failure_probability if cfg.failure.enabled else 0.0
        ),
        "routing_enabled": cfg.routing.enabled,
        "partition": cfg.fl.partition,
        "dirichlet_alpha": cfg.fl.dirichlet_alpha,
        # Backward-compatible test_* names refer to the standard benchmark.
        **{f"test_{key}": value for key, value in standard_metrics.items()},
        **{f"test_default_{key}": value for key, value in standard_default_metrics.items()},
        **{f"standard_test_{key}": value for key, value in standard_metrics.items()},
        **calibrated_fields,
        **mean_network,
    }
    save_json(final, run_dir / "final_test_metrics.json")
    pd.DataFrame([final]).to_csv(run_dir / "final_test_metrics.csv", index=False)

    standard_predictions = (standard_probabilities >= best_threshold).astype(int)
    standard_default_predictions = (standard_probabilities >= 0.5).astype(int)
    if cfg.experiment.save_probabilities:
        standard_prediction_frame = pd.DataFrame(
            {
                "y_true": bundle.y_test,
                "probability_attack": standard_probabilities,
                "prediction_validation_threshold": standard_predictions,
                "prediction_default_0_5": standard_default_predictions,
                "decision_threshold": best_threshold,
                "attack_category": bundle.test_attack_categories,
                "protocol": "standard_official_test_full",
            }
        )
        standard_prediction_frame.to_csv(run_dir / "standard_test_predictions.csv", index=False)
        # Backward-compatible filename.
        standard_prediction_frame.to_csv(run_dir / "test_predictions.csv", index=False)

        if bundle.calibration_enabled and len(bundle.y_calibration):
            pd.DataFrame(
                {
                    "y_true": bundle.y_calibration,
                    "probability_attack": calibration_probabilities,
                    "prediction_calibration_threshold": (
                        calibration_probabilities >= calibrated_threshold
                    ).astype(int),
                    "decision_threshold": calibrated_threshold,
                    "attack_category": bundle.calibration_attack_categories,
                    "protocol": "calibration_subset_secondary",
                }
            ).to_csv(run_dir / "calibration_predictions.csv", index=False)
            pd.DataFrame(
                {
                    "y_true": bundle.y_calibrated_test,
                    "probability_attack": calibrated_test_probabilities,
                    "prediction_calibration_threshold": (
                        calibrated_test_probabilities >= calibrated_threshold
                    ).astype(int),
                    "prediction_default_0_5": (
                        calibrated_test_probabilities >= 0.5
                    ).astype(int),
                    "decision_threshold": calibrated_threshold,
                    "attack_category": bundle.calibrated_test_attack_categories,
                    "protocol": "heldout_calibrated_test_secondary",
                }
            ).to_csv(run_dir / "calibrated_test_predictions.csv", index=False)

    _per_attack_metrics(
        bundle.y_test,
        standard_probabilities,
        bundle.test_attack_categories,
        threshold=best_threshold,
    ).to_csv(run_dir / "per_attack_metrics_standard.csv", index=False)
    # Backward-compatible filename.
    _per_attack_metrics(
        bundle.y_test,
        standard_probabilities,
        bundle.test_attack_categories,
        threshold=best_threshold,
    ).to_csv(run_dir / "per_attack_metrics.csv", index=False)
    if bundle.calibration_enabled and len(bundle.y_calibrated_test):
        _per_attack_metrics(
            bundle.y_calibrated_test,
            calibrated_test_probabilities,
            bundle.calibrated_test_attack_categories,
            threshold=calibrated_threshold,
        ).to_csv(run_dir / "per_attack_metrics_calibrated.csv", index=False)

    standard_confusion = pd.DataFrame(
        [
            [standard_metrics["tn"], standard_metrics["fp"]],
            [standard_metrics["fn"], standard_metrics["tp"]],
        ],
        index=["true_normal", "true_attack"],
        columns=["pred_normal", "pred_attack"],
    )
    standard_confusion.to_csv(run_dir / "confusion_matrix.csv")
    standard_confusion.to_csv(run_dir / "confusion_matrix_standard.csv")
    default_confusion = pd.DataFrame(
        [
            [standard_default_metrics["tn"], standard_default_metrics["fp"]],
            [standard_default_metrics["fn"], standard_default_metrics["tp"]],
        ],
        index=["true_normal", "true_attack"],
        columns=["pred_normal", "pred_attack"],
    )
    default_confusion.to_csv(run_dir / "confusion_matrix_default_0_5.csv")
    if calibrated_test_metrics:
        pd.DataFrame(
            [
                [calibrated_test_metrics["tn"], calibrated_test_metrics["fp"]],
                [calibrated_test_metrics["fn"], calibrated_test_metrics["tp"]],
            ],
            index=["true_normal", "true_attack"],
            columns=["pred_normal", "pred_attack"],
        ).to_csv(run_dir / "confusion_matrix_calibrated.csv")

    if cfg.experiment.create_plots:
        create_run_plots(
            run_dir / "round_metrics.csv",
            run_dir / "network_metrics.csv",
            bundle.y_test,
            standard_probabilities,
            run_dir / "plots",
            decision_threshold=best_threshold,
        )
    _write_run_metadata(cfg, run_dir, round_df, privacy_plan, privacy_steps, early_stopped)
    return run_dir
