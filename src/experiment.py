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
from .partitioning import make_partitions
from .plotting import create_run_plots
from .privacy import (
    add_gaussian_noise,
    approximate_rdp_epsilon,
    calibrate_noise_multiplier,
    capped_normalized_weights,
    clip_update,
)
from .recovery import recover_failed_update
from .server import Server
from .state import State, state_l2_norm, state_num_bytes, subtract_states
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
        "subsampling_amplification_valid": not cfg.routing.enabled,
        "accounting_note": (
            "RDP Poisson-sampling estimate. Routed client selection and the "
            "data-dependent robust filter are not covered by a formal proof; "
            "report this value as an estimated privacy budget."
        ),
    }


def run_experiment(cfg: Config) -> Path:
    cfg.validate()
    set_global_seed(cfg.experiment.seed, cfg.experiment.deterministic)
    device = resolve_device(cfg.experiment.device)

    run_dir = (
        Path(cfg.experiment.output_dir)
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
    )
    dataset_summary = _dataset_summary(bundle)
    save_json(dataset_summary, run_dir / "dataset_summary.json")
    pd.DataFrame([dataset_summary]).to_csv(run_dir / "dataset_summary.csv", index=False)
    pd.DataFrame({"feature_name": bundle.feature_names}).to_csv(
        run_dir / "feature_names.csv", index=False
    )
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

    initial_probabilities = server.predict_probabilities(bundle.X_val)
    initial_default, initial_selected = _validation_metrics(
        cfg, bundle.y_val, initial_probabilities
    )
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

    update_bytes = state_num_bytes(server.get_global_state())

    for round_number in trange(1, cfg.fl.rounds + 1, desc=cfg.experiment.method_name):
        round_start = time.perf_counter()
        network.update_round(cfg.routing.enabled)
        if cfg.routing.enabled:
            selected_clients = network.select_clients(cfg.fl.clients_per_round)
        else:
            selected_clients = rng.choice(
                cfg.fl.num_clients,
                size=cfg.fl.clients_per_round,
                replace=False,
            ).tolist()

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
            explicit_failure = (
                cfg.failure.enabled
                and rng.random() < cfg.failure.client_failure_probability
            )
            transfer["round"] = round_number
            transfer["explicit_client_failure"] = explicit_failure
            transfer["selected"] = True
            transfer["malicious"] = client_id in malicious_clients

            network_failure = cfg.failure.enabled and not bool(transfer["update_delivered"])
            if explicit_failure or network_failure:
                failed_clients.append(client_id)
                transfer["received_by_server"] = False
                network_rows.append(transfer)
                continue

            is_label_flip = (
                client_id in malicious_clients
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
            if client_id in malicious_clients and cfg.attack.attack_type != "label_flip":
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
            weights.append(float(local_result.num_samples))
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
        recovered_count = 0
        recovery_times: List[float] = []
        recovered_by_client: Dict[int, float] = {}
        if cfg.failure.recovery_enabled and failed_clients and len(updates) >= 2:
            average_delay = float(np.mean(transfer_delays)) if transfer_delays else 0.0
            healthy_updates = list(updates)
            for failed_client in failed_clients:
                recovery = recover_failed_update(
                    healthy_updates,
                    cfg.failure.detection_delay_ms,
                    cfg.failure.reconstruction_time_ms,
                    average_delay,
                )
                updates.append(recovery.update)
                recovered_weight = (
                    len(clients[failed_client].y) * cfg.failure.recovery_weight_factor
                )
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
        privacy_noise_std = 0.0
        privacy_max_weight_share = 0.0
        privacy_clipped_fraction = 0.0
        aggregate_signal_l2_norm = 0.0
        privacy_noise_l2_norm = 0.0
        privacy_noise_to_signal_ratio = 0.0
        server_applied_update_l2_norm = 0.0
        if updates:
            # Robust filtering is performed on un-clipped updates. For central
            # client-level DP, only the surviving updates are then clipped,
            # weight-capped, averaged, and noised. This restores attack
            # separability that was lost when every update was clipped first.
            detection_result, actual_aggregation_method = _safe_aggregate(
                updates, weights, cfg
            )
            kept_indices = detection_result.kept_indices
            kept_count = len(kept_indices)
            rejected_count = len(detection_result.rejected_indices)

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
                private_raw_weights = [weights[index] for index in kept_indices]
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
                aggregate_signal_l2_norm = float(state_l2_norm(aggregate).item())

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
                        "is_malicious_client": client_id in malicious_clients,
                        "effective_malicious_update": (
                            client_id in malicious_clients
                            and not update_recovered_flags[update_index]
                        ),
                        "kept": update_index in kept_set,
                        "pre_clip_l2_norm": pre_norm,
                        "post_clip_l2_norm": post_norm,
                        "diagnostic_distance_or_score": diagnostic,
                        "actual_aggregation_method": actual_aggregation_method,
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
            if cfg.privacy.mode != "none":
                privacy_steps += 1

        val_probabilities = server.predict_probabilities(bundle.X_val)
        val_default, val_selected = _validation_metrics(
            cfg, bundle.y_val, val_probabilities
        )

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
                "kept_updates": kept_count,
                "rejected_updates": rejected_count,
                "failed_clients": len(failed_clients),
                "recovered_clients": recovered_count,
                "malicious_selected": len(set(selected_clients) & malicious_clients),
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
    return run_dir
