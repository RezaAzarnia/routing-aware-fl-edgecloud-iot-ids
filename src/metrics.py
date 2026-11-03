from __future__ import annotations

from typing import Dict

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


def binary_classification_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, float]:
    y_true = np.asarray(y_true).astype(int)
    # Phase 7b: ONE decision rule. Scores are used as given (only clipped to [0, 1], a no-op for valid
    # probabilities) so that ``score >= threshold`` here is exactly the rule used by select_decision_threshold.
    # Clipping to (1e-7, 1-1e-7) before the comparison made a selected threshold of exactly 1.0 predict nothing
    # (false F1=precision=recall=FPR=0) and created artificial ROC ties; numerical clipping is now applied
    # only inside the logarithmic loss, where it is mathematically needed.
    probabilities = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    predictions = (probabilities >= float(threshold)).astype(int)
    loss_probabilities = np.clip(probabilities, 1e-7, 1 - 1e-7)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    specificity = tn / (tn + fp + 1e-12)
    fpr = fp / (fp + tn + 1e-12)

    result = {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall_adr": float(recall_score(y_true, predictions, zero_division=0)),
        "specificity": float(specificity),
        "fpr": float(fpr),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "loss": float(
            log_loss(
                y_true,
                np.column_stack([1 - loss_probabilities, loss_probabilities]),
                labels=[0, 1],
            )
        ),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
    try:
        result["roc_auc"] = float(roc_auc_score(y_true, probabilities))
    except ValueError:
        result["roc_auc"] = float("nan")
    try:
        result["pr_auc"] = float(average_precision_score(y_true, probabilities))
    except ValueError:
        result["pr_auc"] = float("nan")
    return result


def _threshold_candidates(probabilities: np.ndarray, grid_size: int) -> np.ndarray:
    probabilities = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    unique = np.unique(probabilities)
    if len(unique) > grid_size:
        quantiles = np.linspace(0.0, 1.0, grid_size)
        unique = np.unique(np.quantile(unique, quantiles))
    return np.unique(np.concatenate(([0.0, 0.5, 1.0], unique)))


def select_decision_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    objective: str = "fpr_cap",
    max_fpr: float = 0.15,
    min_recall: float = 0.60,
    grid_size: int = 1001,
) -> Dict[str, float | bool | str]:
    """Select an operating threshold using validation data only.

    For ``fpr_cap`` the preferred point must satisfy both the FPR and recall
    constraints. If no such point exists, the fallback stays under the FPR cap
    when possible and maximizes recall, while explicitly marking the constraint
    as infeasible. This prevents a low-FPR but near-zero-recall threshold from
    silently being treated as a successful IDS operating point.
    """
    y_true = np.asarray(y_true).astype(int)
    probabilities = np.asarray(probabilities, dtype=float)
    candidates = _threshold_candidates(probabilities, grid_size)

    order = np.argsort(probabilities)
    sorted_probabilities = probabilities[order]
    sorted_labels = y_true[order]
    cumulative_positives = np.concatenate(([0], np.cumsum(sorted_labels)))
    split_indices = np.searchsorted(sorted_probabilities, candidates, side="left")

    total_positives = int(sorted_labels.sum())
    total_negatives = int(len(sorted_labels) - total_positives)
    predicted_positive = len(sorted_labels) - split_indices
    true_positive = total_positives - cumulative_positives[split_indices]
    false_positive = predicted_positive - true_positive
    false_negative = total_positives - true_positive
    true_negative = total_negatives - false_positive

    recall = true_positive / np.maximum(total_positives, 1)
    fpr = false_positive / np.maximum(total_negatives, 1)
    precision = true_positive / np.maximum(true_positive + false_positive, 1)
    specificity = true_negative / np.maximum(total_negatives, 1)
    accuracy = (true_positive + true_negative) / max(len(sorted_labels), 1)
    balanced_accuracy = (recall + specificity) / 2.0
    f1 = 2.0 * precision * recall / np.maximum(precision + recall, 1e-12)

    feasible = True
    fallback_reason = "none"
    if objective == "fpr_cap":
        full_mask = (fpr <= max_fpr + 1e-12) & (recall >= min_recall - 1e-12)
        if full_mask.any():
            mask = full_mask
        else:
            feasible = False
            fpr_only = fpr <= max_fpr + 1e-12
            if fpr_only.any():
                mask = fpr_only
                fallback_reason = "recall_constraint_infeasible"
            else:
                mask = np.ones_like(fpr, dtype=bool)
                fallback_reason = "fpr_and_recall_constraints_infeasible"
        indices = np.where(mask)[0]
        # Primary: recall, secondary: F1 and balanced accuracy, final tie-break:
        # threshold nearest 0.5 for a less extreme operating point.
        local = np.lexsort(
            (
                -np.abs(candidates[indices] - 0.5),
                balanced_accuracy[indices],
                f1[indices],
                recall[indices],
            )
        )[-1]
        selected_index = int(indices[local])
    elif objective == "max_f1":
        selected_index = int(np.lexsort((-fpr, balanced_accuracy, f1))[-1])
        fallback_reason = "not_applicable"
    elif objective == "max_balanced_accuracy":
        selected_index = int(np.lexsort((-fpr, f1, balanced_accuracy))[-1])
        fallback_reason = "not_applicable"
    elif objective == "youden":
        youden = recall - fpr
        selected_index = int(np.lexsort((-fpr, f1, youden))[-1])
        fallback_reason = "not_applicable"
    else:
        raise ValueError(f"Unknown threshold objective: {objective}")

    threshold = float(candidates[selected_index])
    selected = binary_classification_metrics(y_true, probabilities, threshold=threshold)
    fpr_violation = max(0.0, float(selected["fpr"]) - float(max_fpr))
    recall_shortfall = max(0.0, float(min_recall) - float(selected["recall_adr"]))
    return {
        **selected,
        "objective": objective,
        "constraint_feasible": bool(feasible),
        "fallback_reason": fallback_reason,
        "max_fpr_constraint": float(max_fpr),
        "min_recall_constraint": float(min_recall),
        "fpr_constraint_violation": fpr_violation,
        "recall_constraint_shortfall": recall_shortfall,
    }


def evaluate_operating_points(
    reference_y: np.ndarray,
    reference_probabilities: np.ndarray,
    evaluation_y: np.ndarray,
    evaluation_probabilities: np.ndarray,
    fpr_caps: tuple[float, ...] | list[float],
    grid_size: int = 1001,
    reference_name: str = "validation",
    evaluation_name: str = "test",
) -> list[Dict[str, float | bool | str]]:
    """Select thresholds on a reference set and apply them unchanged elsewhere.

    This is the deployable protocol used for Recall@FPR reporting. It must not be
    confused with an oracle threshold selected directly on the evaluation set.
    """
    rows: list[Dict[str, float | bool | str]] = []
    for cap in fpr_caps:
        selected = select_decision_threshold(
            reference_y,
            reference_probabilities,
            objective="fpr_cap",
            max_fpr=float(cap),
            min_recall=0.0,
            grid_size=grid_size,
        )
        evaluated = binary_classification_metrics(
            evaluation_y,
            evaluation_probabilities,
            threshold=float(selected["threshold"]),
        )
        row: Dict[str, float | bool | str] = {
            "reference_set": reference_name,
            "evaluation_set": evaluation_name,
            "target_fpr_cap": float(cap),
            "selected_threshold": float(selected["threshold"]),
            "reference_constraint_feasible": bool(selected["constraint_feasible"]),
            "reference_recall": float(selected["recall_adr"]),
            "reference_fpr": float(selected["fpr"]),
            "reference_precision": float(selected["precision"]),
            "reference_f1": float(selected["f1"]),
            "evaluation_recall": float(evaluated["recall_adr"]),
            "evaluation_fpr": float(evaluated["fpr"]),
            "evaluation_precision": float(evaluated["precision"]),
            "evaluation_f1": float(evaluated["f1"]),
            "evaluation_balanced_accuracy": float(evaluated["balanced_accuracy"]),
            "evaluation_accuracy": float(evaluated["accuracy"]),
            "fpr_transport_gap": float(evaluated["fpr"] - selected["fpr"]),
            "recall_transport_gap": float(evaluated["recall_adr"] - selected["recall_adr"]),
        }
        rows.append(row)
    return rows


def oracle_recall_at_fpr_caps(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    fpr_caps: tuple[float, ...] | list[float],
    grid_size: int = 1001,
    evaluation_name: str = "test",
) -> list[Dict[str, float | bool | str]]:
    """Diagnostic upper-bound curve with thresholds selected on the same set.

    These rows are explicitly marked as oracle diagnostics and must not be used
    as the primary deployable result in a paper.
    """
    rows: list[Dict[str, float | bool | str]] = []
    for cap in fpr_caps:
        selected = select_decision_threshold(
            y_true,
            probabilities,
            objective="fpr_cap",
            max_fpr=float(cap),
            min_recall=0.0,
            grid_size=grid_size,
        )
        rows.append(
            {
                "evaluation_set": evaluation_name,
                "target_fpr_cap": float(cap),
                "oracle_threshold": float(selected["threshold"]),
                "oracle_recall": float(selected["recall_adr"]),
                "oracle_fpr": float(selected["fpr"]),
                "oracle_precision": float(selected["precision"]),
                "oracle_f1": float(selected["f1"]),
                "oracle_only_not_deployable": True,
            }
        )
    return rows
