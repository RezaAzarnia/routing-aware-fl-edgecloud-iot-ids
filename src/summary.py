from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _summarize_final_metrics(experiment_dir: Path) -> pd.DataFrame:
    records = []
    for path in experiment_dir.glob("*/seed_*/final_test_metrics.json"):
        with open(path, "r", encoding="utf-8") as handle:
            records.append(json.load(handle))
    if not records:
        raise FileNotFoundError(f"No final_test_metrics.json files found under {experiment_dir}")

    raw = pd.DataFrame(records)
    raw.to_csv(experiment_dir / "all_final_results.csv", index=False)
    metric_prefixes = (
        "test_",
        "standard_test_",
        "calibrated_test_",
        "calibration_",
        "standard_",
        "network_",
        "communication_",
        "failure_",
        "recovery_",
        "privacy_",
    )
    metric_columns = [
        column
        for column in raw.columns
        if (
            column.startswith(metric_prefixes)
            or column in {"rounds_completed", "best_validation_score", "decision_threshold"}
        )
        and pd.api.types.is_numeric_dtype(raw[column])
    ]
    rows = []
    for method, group in raw.groupby("method"):
        for metric in metric_columns:
            values = group[metric].dropna().astype(float)
            if values.empty:
                continue
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            margin = 1.96 * std / np.sqrt(len(values)) if len(values) > 1 else 0.0
            q1 = float(values.quantile(0.25))
            median = float(values.median())
            q3 = float(values.quantile(0.75))
            rows.append(
                {
                    "method": method,
                    "metric": metric,
                    "n_seeds": len(values),
                    "mean": mean,
                    "std": std,
                    "median": median,
                    "q1": q1,
                    "q3": q3,
                    "iqr": q3 - q1,
                    "ci95_lower": mean - margin,
                    "ci95_upper": mean + margin,
                }
            )
    summary = pd.DataFrame(rows)
    summary.to_csv(experiment_dir / "suite_summary.csv", index=False)
    return summary


def _plot_final_bars(summary: pd.DataFrame, experiment_dir: Path) -> None:
    for metric in [
        "test_accuracy",
        "test_balanced_accuracy",
        "test_f1",
        "test_recall_adr",
        "test_fpr",
        "test_roc_auc",
        "calibrated_test_f1",
        "calibrated_test_recall_adr",
        "calibrated_test_fpr",
        "calibrated_test_roc_auc",
        "standard_fpr_transport_gap",
        "calibrated_fpr_transport_gap",
        "network_mean_end_to_end_delay_ms",
        "network_mean_path_stability",
        "network_mean_pdr",
        "network_mean_transfer_efficiency_mbps",
        "recovery_mean_performance_rounds",
        "privacy_final_epsilon_estimate",
    ]:
        subset = summary[summary["metric"] == metric].copy()
        if subset.empty:
            continue
        subset = subset.sort_values("method")
        plt.figure(figsize=(max(7, len(subset) * 1.1), 4.8))
        x = np.arange(len(subset))
        errors = np.vstack(
            [subset["mean"] - subset["ci95_lower"], subset["ci95_upper"] - subset["mean"]]
        )
        plt.bar(x, subset["mean"], yerr=errors, capsize=4)
        plt.xticks(x, subset["method"], rotation=35, ha="right")
        plt.ylabel(metric.replace("test_", "").replace("_", " ").title())
        plt.title(f"{metric.replace('_', ' ').title()} with 95% CI")
        plt.tight_layout()
        plt.savefig(experiment_dir / f"summary_{metric}.png", dpi=180)
        plt.close()


def _relative_improvements(summary: pd.DataFrame, experiment_dir: Path) -> None:
    available_methods = set(summary["method"].unique())
    baseline = None
    for candidate in ["fedavg_scenario", "fedavg_clean", "fedavg"]:
        if candidate in available_methods:
            baseline = candidate
            break
    if baseline is None:
        return

    lower_is_better = {
        "test_fpr",
        "test_loss",
        "network_mean_end_to_end_delay_ms",
        "communication_total_bytes",
        "failure_total_clients",
        "recovery_mean_simulated_time_ms",
        "recovery_mean_performance_rounds",
        "privacy_final_epsilon_estimate",
    }
    rows = []
    for metric in summary["metric"].unique():
        baseline_rows = summary[(summary["method"] == baseline) & (summary["metric"] == metric)]
        if baseline_rows.empty:
            continue
        baseline_mean = float(baseline_rows.iloc[0]["mean"])
        for _, row in summary[summary["metric"] == metric].iterrows():
            method_mean = float(row["mean"])
            if abs(baseline_mean) < 1e-12:
                relative = np.nan
            elif metric in lower_is_better:
                relative = (baseline_mean - method_mean) / abs(baseline_mean) * 100
            else:
                relative = (method_mean - baseline_mean) / abs(baseline_mean) * 100
            rows.append(
                {
                    "baseline": baseline,
                    "method": row["method"],
                    "metric": metric,
                    "baseline_mean": baseline_mean,
                    "method_mean": method_mean,
                    "absolute_difference": method_mean - baseline_mean,
                    "relative_improvement_percent": relative,
                    "direction": "lower_is_better" if metric in lower_is_better else "higher_is_better",
                }
            )
    pd.DataFrame(rows).to_csv(experiment_dir / "relative_improvements.csv", index=False)


def _summarize_round_curves(experiment_dir: Path) -> pd.DataFrame:
    frames = []
    for path in experiment_dir.glob("*/seed_*/round_metrics.csv"):
        frame = pd.read_csv(path)
        frame["method"] = path.parents[1].name
        frame["seed"] = int(path.parent.name.split("_")[-1])
        frames.append(frame)
    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)
    metric_columns = [
        "val_accuracy",
        "val_f1",
        "val_recall_adr",
        "val_fpr",
        "val_roc_auc",
        "val_pr_auc",
        "val_loss",
        "selected_threshold",
        "privacy_epsilon_estimate",
        "mean_end_to_end_delay_ms",
        "mean_pdr",
        "mean_path_stability",
        "mean_transfer_efficiency_mbps",
        "privacy_clipped_fraction",
        "aggregate_signal_l2_norm",
        "privacy_noise_l2_norm",
        "privacy_noise_to_signal_ratio",
        "server_applied_update_l2_norm",
    ]
    rows = []
    for (method, round_number), group in raw.groupby(["method", "round"]):
        for metric in metric_columns:
            if metric not in group:
                continue
            values = group[metric].dropna().astype(float)
            if values.empty:
                continue
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            margin = 1.96 * std / np.sqrt(len(values)) if len(values) > 1 else 0.0
            rows.append(
                {
                    "method": method,
                    "round": int(round_number),
                    "metric": metric,
                    "n_seeds": len(values),
                    "mean": mean,
                    "std": std,
                    "ci95_lower": mean - margin,
                    "ci95_upper": mean + margin,
                }
            )
    curve_summary = pd.DataFrame(rows)
    curve_summary.to_csv(experiment_dir / "round_curve_summary.csv", index=False)
    return curve_summary


def _plot_round_curves(curves: pd.DataFrame, experiment_dir: Path) -> None:
    if curves.empty:
        return
    metrics = [
        "val_accuracy",
        "val_f1",
        "val_recall_adr",
        "val_fpr",
        "val_roc_auc",
        "selected_threshold",
        "privacy_epsilon_estimate",
        "mean_end_to_end_delay_ms",
        "mean_pdr",
        "mean_path_stability",
    ]
    for metric in metrics:
        subset = curves[curves["metric"] == metric]
        if subset.empty:
            continue
        plt.figure(figsize=(7.5, 5))
        for method, group in subset.groupby("method"):
            group = group.sort_values("round")
            x = group["round"].to_numpy()
            mean = group["mean"].to_numpy()
            lower = group["ci95_lower"].to_numpy()
            upper = group["ci95_upper"].to_numpy()
            line = plt.plot(x, mean, marker="o", markersize=3, label=method)[0]
            plt.fill_between(x, lower, upper, alpha=0.15, color=line.get_color())
        plt.xlabel("Communication Round")
        plt.ylabel(metric.replace("_", " ").title())
        plt.title(f"{metric.replace('_', ' ').title()} across Seeds")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(experiment_dir / f"round_summary_{metric}.png", dpi=180)
        plt.close()


def _load_final_results(experiment_dir: Path) -> pd.DataFrame:
    result_path = experiment_dir / "all_final_results.csv"
    if not result_path.exists():
        _summarize_final_metrics(experiment_dir)
    return pd.read_csv(result_path)


def _write_decision_report(
    experiment_dir: Path,
    stem: str,
    title: str,
    report: dict,
) -> Path:
    json_path = experiment_dir / f"{stem}.json"
    def _json_default(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(
            report,
            handle,
            indent=2,
            ensure_ascii=False,
            allow_nan=True,
            default=_json_default,
        )

    lines = [
        title,
        "=" * 78,
        f"VERDICT: {report.get('verdict', 'UNKNOWN')}",
        f"Reason: {report.get('reason', '')}",
        "",
        "This is a one-seed pilot decision, not a paper result.",
        "",
    ]
    for check in report.get("checks", []):
        lines.append(
            f"[{'PASS' if check['pass'] else 'FAIL'}] {check['name']}: "
            f"value={check['value']} target={check['target']}"
        )
    if report.get("recommended_privacy_target") is not None:
        lines.extend(
            [
                "",
                "Recommended target epsilon for the five-seed core run: "
                f"{report['recommended_privacy_target']}",
            ]
        )
    if report.get("diagnostics"):
        lines.extend(["", "Diagnostics:", json.dumps(report["diagnostics"], indent=2, default=_json_default)])
    text_path = experiment_dir / f"{stem}.txt"
    text_path.write_text("\n".join(lines), encoding="utf-8")
    return text_path


def _metric(row: pd.Series, key: str, fallback: str | None = None) -> float:
    value = row.get(key, np.nan)
    if (value is None or not np.isfinite(float(value))) and fallback is not None:
        value = row.get(fallback, np.nan)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _calibration_shift_diagnostic(rows: list[pd.Series]) -> dict:
    standard_fprs = [_metric(row, "test_fpr") for row in rows]
    calibrated_fprs = [_metric(row, "calibrated_test_fpr") for row in rows]
    transport_gaps = [_metric(row, "standard_fpr_transport_gap") for row in rows]
    valid_standard = [value for value in standard_fprs if np.isfinite(value)]
    valid_calibrated = [value for value in calibrated_fprs if np.isfinite(value)]
    common_standard_failure = bool(valid_standard) and all(value > 0.20 for value in valid_standard)
    calibrated_improvement = bool(valid_calibrated) and np.nanmean(valid_calibrated) + 0.05 < np.nanmean(valid_standard)
    return {
        "common_standard_fpr_failure": common_standard_failure,
        "calibrated_protocol_improves_fpr": calibrated_improvement,
        "mean_standard_fpr": float(np.nanmean(valid_standard)) if valid_standard else np.nan,
        "mean_calibrated_fpr": float(np.nanmean(valid_calibrated)) if valid_calibrated else np.nan,
        "mean_standard_fpr_transport_gap": float(np.nanmean(transport_gaps)) if transport_gaps else np.nan,
        "interpretation": (
            "A common validation-to-official-test threshold transport problem is present. "
            "Report both the untouched standard benchmark and the separately labelled calibrated protocol."
            if common_standard_failure and calibrated_improvement
            else "No clear common threshold-transport pattern was detected."
        ),
    }


def create_pilot_stage1_report(experiment_dir: str | Path) -> Path:
    """Decide whether it is worth spending time on the DP and clip-norm pilots."""
    experiment_dir = Path(experiment_dir)
    results = _load_final_results(experiment_dir)
    required = {"pilot_clean", "pilot_scenario_no_dp"}
    missing = sorted(required - set(results["method"]))
    report: dict = {"screening_only": True, "missing_methods": missing, "checks": []}

    if missing:
        report["verdict"] = "STOP"
        report["reason"] = "Pilot stage 1 is incomplete."
        return _write_decision_report(
            experiment_dir,
            "PILOT_STAGE1_REPORT",
            "PILOT STAGE 1 REPORT",
            report,
        )

    def row(method: str) -> pd.Series:
        return results[results["method"] == method].iloc[-1]

    clean = row("pilot_clean")
    scenario = row("pilot_scenario_no_dp")
    checks = [
        {
            "name": "clean_standard_roc_auc",
            "value": _metric(clean, "test_roc_auc"),
            "pass": _metric(clean, "test_roc_auc") >= 0.80,
            "target": ">= 0.80",
            "critical": True,
        },
        {
            "name": "clean_standard_balanced_accuracy",
            "value": _metric(clean, "test_balanced_accuracy"),
            "pass": _metric(clean, "test_balanced_accuracy") >= 0.65,
            "target": ">= 0.65",
            "critical": True,
        },
        {
            "name": "scenario_no_dp_standard_roc_auc",
            "value": _metric(scenario, "test_roc_auc"),
            "pass": _metric(scenario, "test_roc_auc") >= 0.75,
            "target": ">= 0.75",
            "critical": True,
        },
        {
            "name": "scenario_no_dp_calibrated_recall",
            "value": _metric(scenario, "calibrated_test_recall_adr", "test_recall_adr"),
            "pass": _metric(scenario, "calibrated_test_recall_adr", "test_recall_adr") >= 0.50,
            "target": ">= 0.50",
            "critical": False,
        },
        {
            "name": "scenario_no_dp_calibrated_fpr",
            "value": _metric(scenario, "calibrated_test_fpr", "test_fpr"),
            "pass": _metric(scenario, "calibrated_test_fpr", "test_fpr") <= 0.20,
            "target": "<= 0.20",
            "critical": False,
        },
        {
            "name": "scenario_no_dp_standard_fpr_diagnostic",
            "value": _metric(scenario, "test_fpr"),
            "pass": _metric(scenario, "test_fpr") <= 0.20,
            "target": "<= 0.20 (diagnostic, not a hard stop when calibrated protocol succeeds)",
            "critical": False,
        },
    ]
    report["checks"] = checks
    shift = _calibration_shift_diagnostic([clean, scenario])
    report["diagnostics"] = {"calibration_shift": shift}

    if _metric(clean, "test_roc_auc") < 0.70:
        report["verdict"] = "STOP"
        report["reason"] = "Clean learning is too weak; do not run DP or five seeds."
    elif any(not check["pass"] for check in checks if check["critical"]):
        report["verdict"] = "TUNE_MODEL"
        report["reason"] = "The medium pilot runs, but threshold-independent learning targets are not met."
    elif (
        _metric(scenario, "calibrated_test_fpr", "test_fpr") > 0.20
        or _metric(scenario, "calibrated_test_recall_adr", "test_recall_adr") < 0.50
    ):
        report["verdict"] = "TUNE_CALIBRATION"
        report["reason"] = "Learning is adequate, but the secondary calibrated operating point is not yet usable."
    elif shift["common_standard_fpr_failure"] and shift["calibrated_protocol_improves_fpr"]:
        report["verdict"] = "GO_DP_CALIBRATION_SHIFT"
        report["reason"] = (
            "Core learning passed. A common validation-to-official-test threshold shift exists; "
            "continue to DP but preserve both reporting protocols."
        )
    else:
        report["verdict"] = "GO_DP"
        report["reason"] = "Stage 1 passed. Run the clip-norm screen and DP variants next."

    return _write_decision_report(
        experiment_dir,
        "PILOT_STAGE1_REPORT",
        "PILOT STAGE 1 REPORT",
        report,
    )


def create_clip_sweep_report(experiment_dir: str | Path) -> Path:
    """Recommend a clip norm using validation utility and clipping diagnostics only."""
    experiment_dir = Path(experiment_dir)
    results = _load_final_results(experiment_dir)
    subset = results[results["method"].astype(str).str.startswith("clip_sweep_eps20_clip_")].copy()
    report: dict = {"screening_only": True, "checks": [], "recommended_clip_norm": None}
    if subset.empty:
        report["verdict"] = "STOP"
        report["reason"] = "No clip-sweep runs were found."
        return _write_decision_report(
            experiment_dir, "CLIP_SWEEP_REPORT", "CLIP NORM SWEEP REPORT", report
        )

    rows = []
    for _, result in subset.iterrows():
        clip = _metric(result, "privacy_clip_norm")
        val_auc = _metric(result, "best_validation_score")
        clipped_fraction = _metric(result, "mean_privacy_clipped_fraction")
        noise_ratio = _metric(result, "mean_privacy_noise_to_signal_ratio")
        rows.append(
            {
                "method": str(result["method"]),
                "clip_norm": clip,
                "best_validation_roc_auc": val_auc,
                "mean_clipped_fraction": clipped_fraction,
                "mean_noise_to_signal_ratio": noise_ratio,
            }
        )
    frame = pd.DataFrame(rows).sort_values("clip_norm")
    frame.to_csv(experiment_dir / "clip_sweep_summary.csv", index=False)

    max_auc = frame["best_validation_roc_auc"].max()
    competitive = frame[frame["best_validation_roc_auc"] >= max_auc - 0.02].copy()
    # Among variants with essentially equivalent validation AUC, prefer the one
    # that avoids near-total clipping; then prefer lower noise-to-signal ratio.
    competitive["clipping_penalty"] = np.where(
        competitive["mean_clipped_fraction"] > 0.90,
        competitive["mean_clipped_fraction"] - 0.90,
        np.abs(competitive["mean_clipped_fraction"] - 0.70) * 0.25,
    )
    competitive["selection_score"] = (
        competitive["best_validation_roc_auc"]
        - competitive["clipping_penalty"].fillna(0.0)
        - 0.001 * competitive["mean_noise_to_signal_ratio"].fillna(0.0)
    )
    best = competitive.sort_values(
        ["selection_score", "best_validation_roc_auc"], ascending=False
    ).iloc[0]
    recommended = float(best["clip_norm"])
    report["recommended_clip_norm"] = recommended
    report["diagnostics"] = {"variants": rows}
    report["checks"] = [
        {
            "name": "recommended_validation_roc_auc",
            "value": float(best["best_validation_roc_auc"]),
            "pass": float(best["best_validation_roc_auc"]) >= 0.70,
            "target": ">= 0.70",
        },
        {
            "name": "recommended_clipped_fraction",
            "value": float(best["mean_clipped_fraction"]),
            "pass": float(best["mean_clipped_fraction"]) <= 0.95,
            "target": "<= 0.95",
        },
    ]
    if all(item["pass"] for item in report["checks"]):
        report["verdict"] = "USE_RECOMMENDED_CLIP"
        report["reason"] = (
            "Use the recommended clip norm for the epsilon-20 and epsilon-10 one-seed DP pilot."
        )
    else:
        report["verdict"] = "TUNE_CLIP_RANGE"
        report["reason"] = "All tested clip norms still show weak validation utility or near-total clipping."

    return _write_decision_report(
        experiment_dir, "CLIP_SWEEP_REPORT", "CLIP NORM SWEEP REPORT", report
    )


def create_pilot_report(experiment_dir: str | Path) -> Path:
    """Choose whether and with which epsilon to start the five-seed core run."""
    experiment_dir = Path(experiment_dir)
    results = _load_final_results(experiment_dir)
    required = {
        "pilot_clean",
        "pilot_scenario_no_dp",
        "pilot_proposed_dp_eps20",
        "pilot_proposed_dp_eps10",
    }
    missing = sorted(required - set(results["method"]))
    report: dict = {"screening_only": True, "missing_methods": missing, "checks": []}
    if missing:
        report["verdict"] = "STOP"
        report["reason"] = "The complete pilot suite is incomplete."
        return _write_decision_report(
            experiment_dir, "PILOT_REPORT", "COMPLETE PILOT REPORT", report
        )

    def row(method: str) -> pd.Series:
        return results[results["method"] == method].iloc[-1]

    clean = row("pilot_clean")
    no_dp = row("pilot_scenario_no_dp")
    dp20 = row("pilot_proposed_dp_eps20")
    dp10 = row("pilot_proposed_dp_eps10")

    checks = [
        {
            "name": "clean_standard_roc_auc",
            "value": _metric(clean, "test_roc_auc"),
            "pass": _metric(clean, "test_roc_auc") >= 0.80,
            "target": ">= 0.80",
            "critical": True,
            "variant": "stage1",
        },
        {
            "name": "scenario_no_dp_standard_roc_auc",
            "value": _metric(no_dp, "test_roc_auc"),
            "pass": _metric(no_dp, "test_roc_auc") >= 0.75,
            "target": ">= 0.75",
            "critical": True,
            "variant": "stage1",
        },
        {
            "name": "scenario_no_dp_calibrated_fpr",
            "value": _metric(no_dp, "calibrated_test_fpr", "test_fpr"),
            "pass": _metric(no_dp, "calibrated_test_fpr", "test_fpr") <= 0.20,
            "target": "<= 0.20",
            "critical": True,
            "variant": "stage1",
        },
    ]

    def add_dp_checks(label: str, row_data: pd.Series, min_auc: float, max_drop: float) -> list[dict]:
        target = _metric(row_data, "privacy_target_epsilon")
        epsilon = _metric(row_data, "privacy_final_epsilon_estimate")
        calibrated_f1 = _metric(row_data, "calibrated_test_f1", "test_f1")
        no_dp_calibrated_f1 = _metric(no_dp, "calibrated_test_f1", "test_f1")
        f1_drop = no_dp_calibrated_f1 - calibrated_f1
        return [
            {
                "name": f"{label}_standard_roc_auc",
                "value": _metric(row_data, "test_roc_auc"),
                "pass": _metric(row_data, "test_roc_auc") >= min_auc,
                "target": f">= {min_auc:.2f}",
                "critical": True,
                "variant": label,
            },
            {
                "name": f"{label}_calibrated_recall",
                "value": _metric(row_data, "calibrated_test_recall_adr", "test_recall_adr"),
                "pass": _metric(row_data, "calibrated_test_recall_adr", "test_recall_adr") >= 0.50,
                "target": ">= 0.50",
                "critical": True,
                "variant": label,
            },
            {
                "name": f"{label}_calibrated_fpr",
                "value": _metric(row_data, "calibrated_test_fpr", "test_fpr"),
                "pass": _metric(row_data, "calibrated_test_fpr", "test_fpr") <= 0.20,
                "target": "<= 0.20",
                "critical": True,
                "variant": label,
            },
            {
                "name": f"{label}_calibrated_f1_drop",
                "value": f1_drop,
                "pass": f1_drop <= max_drop,
                "target": f"<= {max_drop:.2f}",
                "critical": False,
                "variant": label,
            },
            {
                "name": f"{label}_privacy_budget",
                "value": epsilon,
                "pass": np.isfinite(epsilon) and np.isfinite(target) and epsilon <= target * 1.05,
                "target": f"<= {target * 1.05:.3f}",
                "critical": True,
                "variant": label,
            },
            {
                "name": f"{label}_mean_clipped_fraction",
                "value": _metric(row_data, "mean_privacy_clipped_fraction"),
                "pass": _metric(row_data, "mean_privacy_clipped_fraction") <= 0.95,
                "target": "<= 0.95",
                "critical": False,
                "variant": label,
            },
        ]

    checks.extend(add_dp_checks("eps20", dp20, min_auc=0.70, max_drop=0.12))
    checks.extend(add_dp_checks("eps10", dp10, min_auc=0.65, max_drop=0.15))
    report["checks"] = checks

    def variant_passes(name: str) -> bool:
        relevant = [check for check in checks if check.get("variant") == name]
        return bool(relevant) and all(check["pass"] for check in relevant if check["critical"])

    stage1_ok = all(
        check["pass"] for check in checks if check.get("variant") == "stage1" and check["critical"]
    )
    eps10_ok = variant_passes("eps10")
    eps20_ok = variant_passes("eps20")

    shift = _calibration_shift_diagnostic([clean, no_dp, dp20, dp10])
    report["diagnostics"] = {
        "calibration_shift": shift,
        "eps20": {
            "mean_noise_to_signal_ratio": _metric(dp20, "mean_privacy_noise_to_signal_ratio"),
            "mean_clipped_fraction": _metric(dp20, "mean_privacy_clipped_fraction"),
            "clip_norm": _metric(dp20, "privacy_clip_norm"),
        },
        "eps10": {
            "mean_noise_to_signal_ratio": _metric(dp10, "mean_privacy_noise_to_signal_ratio"),
            "mean_clipped_fraction": _metric(dp10, "mean_privacy_clipped_fraction"),
            "clip_norm": _metric(dp10, "privacy_clip_norm"),
        },
    }

    if not stage1_ok:
        report["verdict"] = "TUNE_CALIBRATION_OR_MODEL"
        report["reason"] = (
            "Threshold-independent learning or the calibrated no-DP operating point is not ready."
        )
        report["recommended_privacy_target"] = None
    elif eps10_ok:
        report["verdict"] = "GO_CORE" if not shift["common_standard_fpr_failure"] else "GO_CORE_WITH_CALIBRATION_SHIFT"
        report["reason"] = (
            "The epsilon-10 pilot passed utility, calibrated operating-point, and privacy checks. "
            "The untouched standard benchmark must still be reported separately."
        )
        report["recommended_privacy_target"] = 10.0
    elif eps20_ok:
        report["verdict"] = "GO_CORE_EPS20" if not shift["common_standard_fpr_failure"] else "GO_CORE_EPS20_WITH_CALIBRATION_SHIFT"
        report["reason"] = (
            "Epsilon 10 is too costly, but epsilon 20 passes the calibrated operating-point checks. "
            "The untouched standard benchmark must still be reported separately."
        )
        report["recommended_privacy_target"] = 20.0
    else:
        report["verdict"] = "TUNE_DP_OR_CLIP"
        report["reason"] = (
            "Non-private learning is viable, but neither DP variant passes the calibrated utility/FPR checks."
        )
        report["recommended_privacy_target"] = None

    return _write_decision_report(
        experiment_dir, "PILOT_REPORT", "COMPLETE PILOT REPORT", report
    )


def summarize_experiment(
    experiment_dir: str | Path,
    create_plots: bool = True,
) -> Path:
    experiment_dir = Path(experiment_dir)
    final_summary = _summarize_final_metrics(experiment_dir)
    _relative_improvements(final_summary, experiment_dir)
    curves = _summarize_round_curves(experiment_dir)
    if create_plots:
        _plot_final_bars(final_summary, experiment_dir)
        _plot_round_curves(curves, experiment_dir)
    return experiment_dir / "suite_summary.csv"
