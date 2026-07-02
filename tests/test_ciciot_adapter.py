from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DataConfig
from src.data import load_dataset


def _write_split(path: Path, n: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    labels = np.tile([0, 1], n // 2 + 1)[:n]
    frame = pd.DataFrame(
        {
            "flow_duration": rng.normal(size=n),
            "Rate": rng.normal(size=n) + labels,
            "attack_category": np.where(labels == 0, "BenignTraffic", "DDoS-UDP_Flood"),
            "label": labels,
        }
    )
    frame.to_csv(path, index=False)


def test_ciciot_loader_uses_explicit_splits_and_train_only_preprocessing(tmp_path: Path) -> None:
    train = tmp_path / "train.csv"
    val = tmp_path / "validation.csv"
    test = tmp_path / "test.csv"
    _write_split(train, 100, 1)
    _write_split(val, 40, 2)
    _write_split(test, 60, 3)

    cfg = DataConfig(
        dataset_name="ciciot2023",
        train_csv=str(train),
        validation_csv=str(val),
        test_csv=str(test),
        label_col="label",
        attack_category_col="attack_category",
        drop_cols=("attack_category",),
        categorical_cols=(),
        enable_calibrated_evaluation=False,
    )
    bundle = load_dataset(cfg, seed=7)
    assert bundle.X_train.shape == (100, 2)
    assert bundle.X_val.shape == (40, 2)
    assert bundle.X_test.shape == (60, 2)
    assert bundle.calibration_enabled is False
    assert set(bundle.test_attack_categories) == {"BenignTraffic", "DDoS-UDP_Flood"}
    assert len(bundle.feature_names) == 2
