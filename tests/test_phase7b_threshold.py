"""Phase 7b: threshold selection and classification evaluation use one decision rule (score >= threshold)."""
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from src.metrics import binary_classification_metrics, select_decision_threshold


def saturated_scores(seed=0, n=2000):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    p = np.where(y == 1, 1.0, 0.0)
    flip = rng.random(n) < 0.12                           # some benign saturate at 1.0, some attacks at 0.0
    p = np.where(flip, 1.0 - p, p)
    return y, p.astype(float)


def test_threshold_one_predicts_exactly_the_saturated_scores():
    y, p = saturated_scores()
    m = binary_classification_metrics(y, p, threshold=1.0)
    assert m["tp"] + m["fp"] == int((p == 1.0).sum()) > 0
    assert m["f1"] > 0 and m["recall_adr"] > 0


def test_threshold_zero_predicts_everything_positive():
    y, p = saturated_scores()
    m = binary_classification_metrics(y, p, threshold=0.0)
    assert m["tp"] + m["fp"] == len(y) and m["tn"] == 0 and m["fn"] == 0
    assert m["recall_adr"] == 1.0 and m["fpr"] == pytest.approx(1.0)


def only_one_is_feasible(seed=0, n=3000):
    """Over-confident model: benign scores mostly just below 1, attacks mostly exactly 1.0 (float saturation)."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    p = np.where(y == 1, np.where(rng.random(n) < 0.8, 1.0, rng.uniform(0.7, 0.95, n)), np.where(rng.random(n) < 0.08, 1.0, rng.uniform(0.6, 0.99999, n)))
    return y, p.astype(float)


def test_selected_operating_point_is_reproduced_by_the_evaluation_function():
    """The regression: select_decision_threshold chooses 1.0 and the evaluation must reproduce its confusion matrix."""
    y, p = only_one_is_feasible()
    sel = select_decision_threshold(y, p, objective="fpr_cap", max_fpr=0.15, min_recall=0.6)
    assert sel["threshold"] == 1.0 and sel["constraint_feasible"]
    ev = binary_classification_metrics(y, p, threshold=sel["threshold"])
    for key in ("tp", "fp", "fn", "tn", "f1", "precision", "recall_adr", "fpr"):
        assert ev[key] == sel[key], key
    assert ev["recall_adr"] >= 0.6 and ev["fpr"] <= 0.15 + 1e-9 and ev["f1"] > 0.5


@pytest.mark.parametrize("seed", range(6))
def test_selection_and_evaluation_agree_on_random_and_tied_scores(seed):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, 800)
    p = np.round(np.clip(rng.normal(0.3 + 0.4 * y, 0.25), 0, 1), 2)          # many ties, exact 0.0 and 1.0
    sel = select_decision_threshold(y, p)
    ev = binary_classification_metrics(y, p, sel["threshold"])
    for key in ("tp", "fp", "fn", "tn"):
        assert ev[key] == sel[key]


def test_auc_is_computed_on_raw_scores_not_on_clipped_ties():
    y, p = saturated_scores()
    p = np.where(p == 1.0, 1.0 - 1e-9 * np.random.default_rng(1).random(len(p)), p)   # distinct values inside the old clip zone
    assert binary_classification_metrics(y, p, 0.5)["roc_auc"] == pytest.approx(roc_auc_score(y, p))


def test_confusion_matrix_is_consistent_and_loss_is_finite_at_exact_0_and_1():
    y, p = saturated_scores()
    m = binary_classification_metrics(y, p, threshold=0.5)
    assert m["tp"] + m["fp"] + m["tn"] + m["fn"] == len(y)
    assert np.isfinite(m["loss"]) and np.isfinite(m["roc_auc"]) and np.isfinite(m["pr_auc"])


def test_loss_matches_the_historical_clipped_log_loss():
    from sklearn.metrics import log_loss
    y, p = saturated_scores()
    c = np.clip(p, 1e-7, 1 - 1e-7)
    assert binary_classification_metrics(y, p, 0.5)["loss"] == pytest.approx(log_loss(y, np.column_stack([1 - c, c]), labels=[0, 1]))


def test_calibration_threshold_applied_to_a_separate_report_partition():
    """Threshold is chosen on calibration only; the report partition only evaluates it (never re-optimised)."""
    ycal, pcal = only_one_is_feasible(1)
    yrep, prep = only_one_is_feasible(2)
    sel = select_decision_threshold(ycal, pcal)
    rep = binary_classification_metrics(yrep, prep, sel["threshold"])
    assert rep["threshold"] == sel["threshold"]
    assert rep["tp"] + rep["fp"] == int((prep >= sel["threshold"]).sum()) > 0


def test_ordinary_scores_unchanged_by_the_fix():
    """For scores inside (1e-7, 1-1e-7) the new and the historical computation are identical."""
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 500)
    p = np.clip(rng.beta(2 + 3 * y, 3 - 1.5 * y), 1e-4, 1 - 1e-4)
    m = binary_classification_metrics(y, p, 0.37)
    pred = (p >= 0.37).astype(int)
    assert m["tp"] == int(((pred == 1) & (y == 1)).sum()) and m["roc_auc"] == pytest.approx(roc_auc_score(y, p))
