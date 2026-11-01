from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve


def _save_line(df: pd.DataFrame, x: str, y: str, title: str, ylabel: str, path: Path) -> None:
    if y not in df or df[y].isna().all():
        return
    plt.figure(figsize=(7, 4.5))
    plt.plot(df[x], df[y], marker="o", markersize=3)
    plt.xlabel(x.replace("_", " ").title())
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def create_run_plots(
    round_metrics_path: str | Path,
    network_metrics_path: str | Path,
    y_test: np.ndarray,
    probabilities: np.ndarray,
    output_dir: str | Path,
    decision_threshold: float = 0.5,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rounds = pd.read_csv(round_metrics_path)
    mapping = {
        "val_accuracy": ("Validation Accuracy", "Accuracy"),
        "val_f1": ("Validation F1 over Rounds", "F1"),
        "val_recall_adr": ("Validation Attack Detection Rate", "ADR / Recall"),
        "val_fpr": ("Validation False Positive Rate", "FPR"),
        "val_loss": ("Validation Loss", "Log Loss"),
        "privacy_epsilon_estimate": ("Privacy Estimate over Rounds", "Estimated epsilon"),
        "selected_threshold": ("Validation-Selected Threshold", "Decision Threshold"),
    }
    for column, (title, ylabel) in mapping.items():
        _save_line(rounds, "round", column, title, ylabel, output / f"{column}.png")

    network_path = Path(network_metrics_path)
    if network_path.exists() and network_path.stat().st_size > 0:
        network = pd.read_csv(network_path)
        if not network.empty:
            grouped = network.groupby("round", as_index=False).agg(
                end_to_end_delay_ms=("end_to_end_delay_ms", "mean"),
                pdr=("pdr", "mean"),
                path_stability=("path_stability", "mean"),
                transfer_efficiency_mbps=("transfer_efficiency_mbps", "mean"),
            )
            for column, ylabel in [
                ("end_to_end_delay_ms", "Delay (ms)"),
                ("pdr", "Packet Delivery Ratio"),
                ("path_stability", "Path Stability"),
                ("transfer_efficiency_mbps", "Transfer Efficiency (Mbps)"),
            ]:
                _save_line(
                    grouped,
                    "round",
                    column,
                    f"{ylabel} over Rounds",
                    ylabel,
                    output / f"network_{column}.png",
                )

    predictions = (probabilities >= decision_threshold).astype(int)
    matrix = np.zeros((2, 2), dtype=int)
    for truth, pred in zip(y_test, predictions):
        matrix[int(truth), int(pred)] += 1
    plt.figure(figsize=(5, 4.5))
    plt.imshow(matrix, cmap="Blues")
    plt.title(f"Test Confusion Matrix (threshold={decision_threshold:.4f})")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.xticks([0, 1], ["Normal", "Attack"])
    plt.yticks([0, 1], ["Normal", "Attack"])
    for row in range(2):
        for col in range(2):
            plt.text(col, row, str(matrix[row, col]), ha="center", va="center")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(output / "confusion_matrix.png", dpi=180)
    plt.close()

    if len(np.unique(y_test)) == 2:
        fpr, tpr, _ = roc_curve(y_test, probabilities)
        plt.figure(figsize=(6, 5))
        plt.plot(fpr, tpr)
        plt.plot([0, 1], [0, 1], linestyle="--")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("Test ROC Curve")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output / "roc_curve.png", dpi=180)
        plt.close()

        precision, recall, _ = precision_recall_curve(y_test, probabilities)
        plt.figure(figsize=(6, 5))
        plt.plot(recall, precision)
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title("Test Precision-Recall Curve")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output / "precision_recall_curve.png", dpi=180)
        plt.close()
