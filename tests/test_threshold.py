import numpy as np

from src.metrics import (
    binary_classification_metrics,
    evaluate_operating_points,
    select_decision_threshold,
)


def test_validation_threshold_respects_fpr_cap_when_feasible():
    y = np.array([0] * 100 + [1] * 100)
    normal_scores = np.linspace(0.01, 0.45, 100)
    attack_scores = np.linspace(0.35, 0.99, 100)
    probabilities = np.concatenate([normal_scores, attack_scores])
    selected = select_decision_threshold(
        y,
        probabilities,
        objective="fpr_cap",
        max_fpr=0.10,
        grid_size=401,
    )
    assert selected["constraint_feasible"]
    assert selected["fpr"] <= 0.1000001
    checked = binary_classification_metrics(y, probabilities, selected["threshold"])
    assert abs(checked["fpr"] - selected["fpr"]) < 1e-12


def test_threshold_marks_recall_constraint_infeasible():
    y = np.array([0] * 100 + [1] * 100)
    # Heavy overlap makes 60% recall impossible under a 5% FPR cap.
    probabilities = np.concatenate([
        np.linspace(0.1, 0.9, 100),
        np.linspace(0.2, 0.8, 100),
    ])
    selected = select_decision_threshold(
        y,
        probabilities,
        objective="fpr_cap",
        max_fpr=0.05,
        min_recall=0.60,
        grid_size=401,
    )
    assert not selected["constraint_feasible"]
    assert selected["fpr"] <= 0.0500001
    assert selected["recall_constraint_shortfall"] > 0


def test_operating_point_threshold_is_selected_on_reference_and_transport_is_logged():
    reference_y = np.array([0] * 100 + [1] * 100)
    reference_p = np.concatenate([np.linspace(0.01, 0.40, 100), np.linspace(0.35, 0.99, 100)])
    evaluation_y = np.array([0] * 100 + [1] * 100)
    evaluation_p = np.concatenate([np.linspace(0.05, 0.55, 100), np.linspace(0.30, 0.95, 100)])
    rows = evaluate_operating_points(
        reference_y,
        reference_p,
        evaluation_y,
        evaluation_p,
        [0.10],
        grid_size=401,
    )
    assert len(rows) == 1
    assert rows[0]["reference_fpr"] <= 0.100001
    assert "fpr_transport_gap" in rows[0]
    checked = binary_classification_metrics(
        evaluation_y, evaluation_p, rows[0]["selected_threshold"]
    )
    assert abs(checked["fpr"] - rows[0]["evaluation_fpr"]) < 1e-12
