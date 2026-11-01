import json
from pathlib import Path

from src.summary import create_clip_sweep_report, create_pilot_report


def _write_result(root: Path, method: str, payload: dict) -> None:
    target = root / method / "seed_1"
    target.mkdir(parents=True, exist_ok=True)
    record = {"experiment": root.name, "method": method, "seed": 1, **payload}
    (target / "final_test_metrics.json").write_text(json.dumps(record), encoding="utf-8")


def test_clip_report_recommends_a_tested_norm(tmp_path: Path):
    for clip, auc, fraction, ratio in [
        (0.05, 0.80, 0.99, 20.0),
        (0.10, 0.81, 0.80, 15.0),
        (0.20, 0.79, 0.45, 14.0),
    ]:
        name = f"clip_sweep_eps20_clip_{str(clip).replace('.', '_')}"
        _write_result(
            tmp_path,
            name,
            {
                "privacy_clip_norm": clip,
                "best_validation_score": auc,
                "mean_privacy_clipped_fraction": fraction,
                "mean_privacy_noise_to_signal_ratio": ratio,
            },
        )
    report_path = create_clip_sweep_report(tmp_path)
    report = json.loads((tmp_path / "CLIP_SWEEP_REPORT.json").read_text())
    assert report_path.exists()
    assert report["recommended_clip_norm"] in {0.05, 0.10, 0.20}
    assert report["verdict"] == "USE_RECOMMENDED_CLIP"


def test_pilot_report_recognizes_common_standard_threshold_shift(tmp_path: Path):
    common = {
        "test_roc_auc": 0.85,
        "test_fpr": 0.35,
        "standard_fpr_transport_gap": 0.20,
        "calibrated_test_fpr": 0.15,
        "calibrated_test_recall_adr": 0.70,
        "calibrated_test_f1": 0.75,
    }
    _write_result(tmp_path, "pilot_clean", {**common, "test_balanced_accuracy": 0.75})
    _write_result(tmp_path, "pilot_scenario_no_dp", {**common, "test_roc_auc": 0.80})
    for name, epsilon, auc in [
        ("pilot_proposed_dp_eps20", 20.0, 0.79),
        ("pilot_proposed_dp_eps10", 10.0, 0.76),
    ]:
        _write_result(
            tmp_path,
            name,
            {
                **common,
                "test_roc_auc": auc,
                "privacy_target_epsilon": epsilon,
                "privacy_final_epsilon_estimate": epsilon,
                "privacy_clip_norm": 0.1,
                "mean_privacy_clipped_fraction": 0.8,
                "mean_privacy_noise_to_signal_ratio": 10.0,
            },
        )
    create_pilot_report(tmp_path)
    report = json.loads((tmp_path / "PILOT_REPORT.json").read_text())
    assert report["verdict"] == "GO_CORE_WITH_CALIBRATION_SHIFT"
    assert report["diagnostics"]["calibration_shift"]["common_standard_fpr_failure"]
