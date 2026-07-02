from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DataConfig
from src.data import load_and_preprocess_unsw


def test_preprocessor_handles_unseen_test_category(tmp_path: Path):
    train = pd.DataFrame(
        {
            "id": range(20),
            "proto": ["tcp", "udp"] * 10,
            "service": ["http", "dns"] * 10,
            "state": ["FIN", "INT"] * 10,
            "duration": np.arange(20),
            "attack_cat": ["Normal", "DoS"] * 10,
            "label": [0, 1] * 10,
        }
    )
    test = train.iloc[:10].copy()
    test["proto"] = "unseen_proto"
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    cfg = DataConfig(
        train_csv=str(train_path),
        test_csv=str(test_path),
        validation_fraction=0.2,
    )
    bundle = load_and_preprocess_unsw(cfg, seed=1)
    assert bundle.X_train.shape[1] == bundle.X_test.shape[1]
    assert bundle.X_train.shape[1] == bundle.X_calibration.shape[1]
    assert bundle.X_train.shape[1] == bundle.X_calibrated_test.shape[1]
    assert np.isfinite(bundle.X_test).all()
    assert len(bundle.y_calibration) + len(bundle.y_calibrated_test) == len(bundle.y_test)
    assert set(bundle.y_calibration.tolist()) == {0, 1}
    assert set(bundle.y_calibrated_test.tolist()) == {0, 1}
