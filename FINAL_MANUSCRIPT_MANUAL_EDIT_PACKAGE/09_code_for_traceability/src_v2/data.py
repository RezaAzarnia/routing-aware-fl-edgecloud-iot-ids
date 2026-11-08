from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import List

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import DataConfig
from .data_integrity import conflicting_fingerprint_groups, predictor_fingerprint


@dataclass
class DatasetBundle:
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    # Standard benchmark: the complete official test partition. The decision
    # threshold for this protocol is selected only on the training validation set.
    X_test: np.ndarray
    y_test: np.ndarray
    test_attack_categories: np.ndarray
    # Secondary calibrated protocol: a deterministic subset of the official test
    # file is used only for threshold calibration, and the remainder is held out
    # for evaluation. Results from this protocol must be labelled separately.
    X_calibration: np.ndarray
    y_calibration: np.ndarray
    calibration_attack_categories: np.ndarray
    X_calibrated_test: np.ndarray
    y_calibrated_test: np.ndarray
    calibrated_test_attack_categories: np.ndarray
    calibration_enabled: bool
    feature_names: List[str]
    raw_train_rows: int
    raw_test_rows: int
    original_column_count: int
    selected_raw_feature_count: int
    # Optional audit information (defaults keep older constructors valid).
    validation_split_info: dict | None = None
    train_exclusions: pd.DataFrame | None = None
    # Threshold-calibration partition (None when the historical protocol is used).
    X_thr: np.ndarray | None = None
    y_thr: np.ndarray | None = None
    # Report partition (three-way protocol): never used for thresholds or checkpoint choice.
    X_rep: np.ndarray | None = None
    y_rep: np.ndarray | None = None
    # Phase 10: global held-out training rows (excluded from preprocessor fitting); None when holdout is disabled (historical).
    holdout_mask: np.ndarray | None = None
    holdout_groups: np.ndarray | None = None
    # SUPP_V2: leakage audit of the client holdout ({'enabled': False} when no holdout is requested)
    client_holdout_audit: dict | None = None


def _group_disjoint_validation_split(
    features: pd.DataFrame, y: np.ndarray, validation_fraction: float, seed: int
):
    """Deterministic, label-stratified split in which identical predictor vectors
    (canonical fingerprint) never straddle the train/validation boundary."""
    from sklearn.model_selection import StratifiedGroupKFold

    fingerprint = predictor_fingerprint(features, list(features.columns))
    _, groups = np.unique(fingerprint, return_inverse=True)
    n_splits = max(2, int(round(1.0 / validation_fraction)))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    train_idx, val_idx = next(splitter.split(features, y, groups))
    return np.sort(train_idx), np.sort(val_idx), fingerprint, n_splits


def _split_threshold_partition(features: pd.DataFrame, y: np.ndarray, fraction: float, seed: int):
    """Split the validation pool into (evaluation, calibration) parts that never share a
    predictor vector. Returns eval_features, calib_features, y_eval, y_calib, info."""
    from sklearn.model_selection import StratifiedGroupKFold

    fingerprint = predictor_fingerprint(features, list(features.columns))
    _, groups = np.unique(fingerprint, return_inverse=True)
    n_splits = max(2, int(round(1.0 / fraction)))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    eval_idx, calib_idx = next(splitter.split(features, y, groups))
    eval_idx, calib_idx = np.sort(eval_idx), np.sort(calib_idx)
    info = {
        "protocol": "predictor_group_disjoint_calibration_vs_evaluation",
        "n_splits": n_splits,
        "calibration_rows": int(len(calib_idx)), "evaluation_rows": int(len(eval_idx)),
        "calibration_benign": int((y[calib_idx] == 0).sum()), "calibration_attack": int((y[calib_idx] == 1).sum()),
        "evaluation_benign": int((y[eval_idx] == 0).sum()), "evaluation_attack": int((y[eval_idx] == 1).sum()),
        "shared_predictor_vectors": int(np.isin(fingerprint[calib_idx], fingerprint[eval_idx]).sum()),
    }
    return features.iloc[eval_idx], features.iloc[calib_idx], y[eval_idx], y[calib_idx], info


def _split_three_way(features: pd.DataFrame, y: np.ndarray, seed: int):
    """Predictor-group-disjoint, label-stratified three-way split of the validation pool.
    Returns (sel_features, cal_features, rep_features, y_sel, y_cal, y_rep, info)."""
    from sklearn.model_selection import StratifiedGroupKFold

    fingerprint = predictor_fingerprint(features, list(features.columns))
    _, groups = np.unique(fingerprint, return_inverse=True)
    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
    folds = [np.sort(test_idx) for _, test_idx in splitter.split(features, y, groups)]
    cal, sel, rep = folds
    fp = fingerprint
    info = {
        "protocol": "three_way_predictor_group_disjoint",
        "calibration_rows": int(len(cal)), "selection_rows": int(len(sel)), "report_rows": int(len(rep)),
        "calibration_benign": int((y[cal] == 0).sum()), "selection_benign": int((y[sel] == 0).sum()),
        "report_benign": int((y[rep] == 0).sum()),
        "shared_vectors_cal_sel": int(np.isin(fp[cal], fp[sel]).sum()),
        "shared_vectors_cal_rep": int(np.isin(fp[cal], fp[rep]).sum()),
        "shared_vectors_sel_rep": int(np.isin(fp[sel], fp[rep]).sum()),
    }
    return features.iloc[sel], features.iloc[cal], features.iloc[rep], y[sel], y[cal], y[rep], info


def _transform_or_empty(preprocessor, features: pd.DataFrame, width: int) -> np.ndarray:
    """Transform features, returning an empty (0, width) float32 array for empty input."""
    if len(features) == 0:
        return np.empty((0, width), dtype=np.float32)
    return preprocessor.transform(features).astype(np.float32, copy=False)


def _split_validation(features: pd.DataFrame, y: np.ndarray, cfg: DataConfig, seed: int):
    """Return X_train_raw, X_val_raw, y_train, y_val, info."""
    info: dict = {"protocol": cfg.validation_split, "seed": int(seed)}
    if cfg.validation_split == "group_disjoint":
        tr, va, fingerprint, n_splits = _group_disjoint_validation_split(
            features, y, cfg.validation_fraction, seed
        )
        shared = int(np.isin(fingerprint[va], fingerprint[tr]).sum())
        info.update({"n_splits": n_splits, "validation_rows_sharing_predictor_vector_with_train": shared})
        X_tr, X_va = features.iloc[tr], features.iloc[va]
        y_tr, y_va = y[tr], y[va]
    else:
        X_tr, X_va, y_tr, y_va = train_test_split(
            features, y, test_size=cfg.validation_fraction, random_state=seed, stratify=y
        )
        fingerprint_tr = predictor_fingerprint(X_tr, list(X_tr.columns))
        fingerprint_va = predictor_fingerprint(X_va, list(X_va.columns))
        info["validation_rows_sharing_predictor_vector_with_train"] = int(
            np.isin(fingerprint_va, fingerprint_tr).sum()
        )
    info.update({
        "train_rows": int(len(y_tr)), "validation_rows": int(len(y_va)),
        "train_attack": int((y_tr == 1).sum()), "train_benign": int((y_tr == 0).sum()),
        "validation_attack": int((y_va == 1).sum()), "validation_benign": int((y_va == 0).sum()),
    })
    return X_tr, X_va, y_tr, y_va, info


def _drop_conflicting_train_groups(X: pd.DataFrame, y: np.ndarray, cfg: DataConfig):
    """Optional prespecified training-side policy: drop predictor-identical groups
    that carry both binary labels. Returns X, y, manifest (or None when disabled)."""
    if not cfg.exclude_conflicting_train_groups:
        return X, y, None
    fingerprint = predictor_fingerprint(X, list(X.columns))
    manifest = conflicting_fingerprint_groups(fingerprint, y)
    drop = np.isin(fingerprint, manifest["fingerprint"].to_numpy(dtype=np.uint64))
    return X.loc[~drop], y[~drop], manifest


def _stratified_subsample(
    frame: pd.DataFrame, label_col: str, max_samples: int | None, seed: int
) -> pd.DataFrame:
    if max_samples is None or len(frame) <= max_samples:
        return frame.reset_index(drop=True)
    sampled, _ = train_test_split(
        frame,
        train_size=max_samples,
        random_state=seed,
        stratify=frame[label_col],
    )
    return sampled.reset_index(drop=True)


def _sanitize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned = cleaned.replace([np.inf, -np.inf], np.nan)
    return cleaned


def _attack_categories(frame: pd.DataFrame, cfg: DataConfig) -> np.ndarray:
    if cfg.attack_category_col in frame:
        return frame[cfg.attack_category_col].fillna("Unknown").astype(str).to_numpy()
    return np.where(frame[cfg.label_col].to_numpy() == 0, "Normal", "Attack")


def _calibration_stratify_key(frame: pd.DataFrame, cfg: DataConfig) -> pd.Series:
    """Build a stable stratification key and collapse rare attack categories.

    A train/test split requires at least two members in every stratum. Rare
    attack categories are therefore collapsed to the binary label rather than
    causing the entire calibrated protocol to fail.
    """
    labels = frame[cfg.label_col].astype(str)
    if not cfg.calibration_stratify_attack_category or cfg.attack_category_col not in frame:
        return labels

    categories = frame[cfg.attack_category_col].fillna("Unknown").astype(str)
    composite = labels + "::" + categories
    counts = composite.value_counts()
    rare = composite.map(counts).fillna(0) < 2
    return composite.where(~rare, labels + "::OTHER")


def _split_calibration_protocol(
    raw_test: pd.DataFrame,
    cfg: DataConfig,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    if not cfg.enable_calibrated_evaluation:
        empty = raw_test.iloc[0:0].copy().reset_index(drop=True)
        return empty, raw_test.reset_index(drop=True), False

    stratify_key = _calibration_stratify_key(raw_test, cfg)
    try:
        calibration, final_eval = train_test_split(
            raw_test,
            train_size=cfg.calibration_fraction_of_test,
            random_state=seed + 2,
            stratify=stratify_key,
        )
    except ValueError:
        # Fallback to binary label stratification for very small pilot samples.
        calibration, final_eval = train_test_split(
            raw_test,
            train_size=cfg.calibration_fraction_of_test,
            random_state=seed + 2,
            stratify=raw_test[cfg.label_col],
        )
    return (
        calibration.reset_index(drop=True),
        final_eval.reset_index(drop=True),
        True,
    )


def fit_preprocessor_with_client_holdout(preprocessor, X_train_raw: pd.DataFrame, y_train: np.ndarray, holdout_fraction: float, seed: int):
    """SUPP_V2 (shared by UNSW-NB15 and CICIoT2023): leakage-safe, deterministic, group-aware GLOBAL client holdout.

    Verbatim extraction of the Phase-10 UNSW procedure (so UNSW results are unchanged), made dataset-independent and given strict fail-closed checks:
      1. predictor groups are formed on the 6-significant-digit rounded predictor vector (64-bit canonical row hash);
      2. whole groups are held out (seeded stream that depends only on (groups, fraction, seed));
      3. the preprocessor is fitted exclusively on non-holdout training rows, holdout rows are only transformed;
      4. closure: any training row whose ENCODED vector or predictor group also occurs in the holdout joins the holdout; refit; repeat until no straddling;
      5. fail closed if (a) closure does not converge, (b) any predictor group or encoded vector still straddles, (c) the holdout is empty, lacks a class, or
         grew beyond 3x the request, (d) the non-holdout part lacks a class.
    Returns (X_train_encoded_for_all_rows, holdout_mask, holdout_groups, audit)."""
    import hashlib

    from .partitioning import group_holdout_mask

    y_train = np.asarray(y_train)
    _g = X_train_raw.copy()
    for _c in _g.columns:
        if pd.api.types.is_numeric_dtype(_g[_c]):
            _v = _g[_c].to_numpy(dtype=np.float64)
            _fin = np.isfinite(_v) & (_v != 0)
            _mag = np.floor(np.log10(np.where(_fin, np.abs(_v), 1.0)))
            _scale = 10.0 ** (5 - _mag)
            _g[_c] = np.where(_fin, np.round(np.where(_fin, _v, 0.0) * _scale) / _scale, _v)
    holdout_groups = predictor_fingerprint(_g, list(_g.columns))
    holdout_mask = group_holdout_mask(y_train, holdout_groups, holdout_fraction, seed)
    initial_holdout_rows = int(holdout_mask.sum())
    iterations = 0
    converged = False
    for iterations in range(1, 13):
        preprocessor.fit(X_train_raw.iloc[np.where(~holdout_mask)[0]])
        X_train = preprocessor.transform(X_train_raw).astype(np.float32, copy=False)
        _enc = predictor_fingerprint(pd.DataFrame(X_train), list(range(X_train.shape[1])))
        _straddle = np.intersect1d(_enc[holdout_mask], _enc[~holdout_mask])
        _gstraddle = np.intersect1d(holdout_groups[holdout_mask], holdout_groups[~holdout_mask])
        if len(_straddle) == 0 and len(_gstraddle) == 0:
            converged = True
            break
        holdout_mask = holdout_mask | np.isin(_enc, _straddle) | np.isin(holdout_groups, _gstraddle)
    if not converged:
        raise RuntimeError("client holdout closure did not converge; refusing to continue (fail closed)")
    # independent final verification (does not reuse the loop's last booleans)
    enc_h, enc_t = _enc[holdout_mask], _enc[~holdout_mask]
    grp_h, grp_t = holdout_groups[holdout_mask], holdout_groups[~holdout_mask]
    n_enc_overlap = int(len(np.intersect1d(enc_h, enc_t)))
    n_grp_overlap = int(len(np.intersect1d(grp_h, grp_t)))
    n = len(y_train)
    n_h = int(holdout_mask.sum())
    if n_enc_overlap or n_grp_overlap:
        raise RuntimeError(f"client holdout leakage: {n_grp_overlap} predictor groups / {n_enc_overlap} encoded vectors straddle train and holdout")
    if n_h == 0:
        raise RuntimeError("client holdout is empty")
    if len(np.unique(y_train[holdout_mask])) < 2 or len(np.unique(y_train[~holdout_mask])) < 2:
        raise RuntimeError("client holdout or the retained training rows lack a class")
    if n_h > 3.0 * holdout_fraction * n:
        raise RuntimeError(f"holdout closure inflated the holdout to {n_h / n:.3f} of the rows (requested {holdout_fraction}); refusing to continue")
    audit = {
        "enabled": True, "requested_fraction": float(holdout_fraction), "seed": int(seed), "grouping": "6-significant-digit rounded predictor vector, 64-bit canonical row hash",
        "train_rows_before_holdout": int(n), "holdout_rows": n_h, "realized_fraction": n_h / n, "holdout_rows_before_closure": initial_holdout_rows,
        "closure_iterations": int(iterations), "predictor_groups_total": int(len(np.unique(holdout_groups))), "predictor_groups_in_holdout": int(len(np.unique(grp_h))),
        "holdout_attack_rows": int((y_train[holdout_mask] == 1).sum()), "holdout_benign_rows": int((y_train[holdout_mask] == 0).sum()),
        "retained_training_attack_rows": int((y_train[~holdout_mask] == 1).sum()), "retained_training_benign_rows": int((y_train[~holdout_mask] == 0).sum()),
        "predictor_groups_straddling_train_holdout": n_grp_overlap, "encoded_vectors_straddling_train_holdout": n_enc_overlap,
        "preprocessor_fit_rows": int((~holdout_mask).sum()), "preprocessor_fitted_on_non_holdout_rows_only": True,
        "holdout_mask_sha256": hashlib.sha256(np.packbits(holdout_mask).tobytes()).hexdigest(),
        "hash_collision_note": "groups are 64-bit row hashes; collision probability among <5e6 rows is < 1e-6",
    }
    return X_train, holdout_mask, holdout_groups, audit


def load_and_preprocess_unsw(
    cfg: DataConfig,
    seed: int,
    preprocessor_output: str | Path | None = None,
    load_test: bool = True,
    holdout_fraction: float = 0.0,
) -> DatasetBundle:
    if not load_test:
        # Validation-only mode: the calibrated protocol is derived from the test
        # file, so it is disabled, and the test file path is never touched.
        cfg = dataclasses.replace(cfg, enable_calibrated_evaluation=False)
    train_path = Path(cfg.train_csv)
    test_path = Path(cfg.test_csv)
    if not train_path.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {train_path}. Put UNSW_NB15_training-set.csv in data/."
        )
    if load_test and not test_path.exists():
        raise FileNotFoundError(
            f"Testing dataset not found: {test_path}. Put UNSW_NB15_testing-set.csv in data/."
        )

    raw_train = pd.read_csv(train_path)
    raw_test = pd.read_csv(test_path) if load_test else raw_train.iloc[0:0].copy()
    original_column_count = len(raw_train.columns)
    raw_train_rows = len(raw_train)
    raw_test_rows = len(raw_test)

    if cfg.label_col not in raw_train or cfg.label_col not in raw_test:
        raise ValueError(f"Label column '{cfg.label_col}' was not found in both CSV files")

    raw_train = _stratified_subsample(raw_train, cfg.label_col, cfg.max_train_samples, seed)
    raw_test = _stratified_subsample(raw_test, cfg.label_col, cfg.max_test_samples, seed + 1)

    raw_calibration, raw_calibrated_test, calibration_enabled = _split_calibration_protocol(
        raw_test, cfg, seed
    )

    y_all = raw_train[cfg.label_col].astype(int).to_numpy(dtype=np.int64)
    y_test = raw_test[cfg.label_col].astype(int).to_numpy(dtype=np.int64)
    y_calibration = raw_calibration[cfg.label_col].astype(int).to_numpy(dtype=np.int64)
    y_calibrated_test = raw_calibrated_test[cfg.label_col].astype(int).to_numpy(dtype=np.int64)

    test_attack_categories = _attack_categories(raw_test, cfg)
    calibration_attack_categories = _attack_categories(raw_calibration, cfg)
    calibrated_test_attack_categories = _attack_categories(raw_calibrated_test, cfg)

    train_features = raw_train.drop(columns=[cfg.label_col, *cfg.drop_cols], errors="ignore")
    test_features = raw_test.drop(columns=[cfg.label_col, *cfg.drop_cols], errors="ignore")
    calibration_features = raw_calibration.drop(
        columns=[cfg.label_col, *cfg.drop_cols], errors="ignore"
    )
    calibrated_test_features = raw_calibrated_test.drop(
        columns=[cfg.label_col, *cfg.drop_cols], errors="ignore"
    )
    train_features = _sanitize_frame(train_features)
    test_features = _sanitize_frame(test_features)
    calibration_features = _sanitize_frame(calibration_features)
    calibrated_test_features = _sanitize_frame(calibrated_test_features)

    missing_categorical = [column for column in cfg.categorical_cols if column not in train_features]
    if missing_categorical:
        raise ValueError(f"Missing expected categorical columns: {missing_categorical}")

    X_train_raw, X_val_raw, y_train, y_val, split_info = _split_validation(
        train_features, y_all, cfg, seed
    )
    X_train_raw, y_train, train_exclusions = _drop_conflicting_train_groups(
        X_train_raw, y_train, cfg
    )
    split_info["train_rows_after_conflict_exclusion"] = int(len(y_train))
    thr_frame = None
    y_thr = None
    if cfg.threshold_calibration_fraction > 0:
        X_val_raw, thr_frame, y_val, y_thr, thr_info = _split_threshold_partition(
            X_val_raw, y_val, cfg.threshold_calibration_fraction, seed + 17
        )
        split_info["threshold_calibration"] = thr_info
        split_info["validation_rows"] = int(len(y_val))

    rep_frame = None
    y_rep = None
    if cfg.validation_three_way:
        X_val_raw, thr_frame, rep_frame, y_val, y_thr, y_rep, three_info = _split_three_way(X_val_raw, y_val, seed + 23)
        split_info["three_way"] = three_info
        split_info["validation_rows"] = int(len(y_val))

    categorical = list(cfg.categorical_cols)
    numeric = [column for column in X_train_raw.columns if column not in categorical]

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", categorical_pipeline, categorical),
            ("numeric", numeric_pipeline, numeric),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )

    holdout_mask = holdout_groups = None
    holdout_audit = {"enabled": False}
    if holdout_fraction > 0:
        X_train, holdout_mask, holdout_groups, holdout_audit = fit_preprocessor_with_client_holdout(preprocessor, X_train_raw, y_train, holdout_fraction, seed)
    else:
        X_train = preprocessor.fit_transform(X_train_raw).astype(np.float32, copy=False)
    X_val = preprocessor.transform(X_val_raw).astype(np.float32, copy=False)
    X_thr = None if thr_frame is None else _transform_or_empty(preprocessor, thr_frame, X_train.shape[1])
    X_rep = None if rep_frame is None else _transform_or_empty(preprocessor, rep_frame, X_train.shape[1])
    X_test = _transform_or_empty(preprocessor, test_features, X_train.shape[1])
    if len(calibration_features):
        X_calibration = preprocessor.transform(calibration_features).astype(np.float32, copy=False)
    else:
        X_calibration = np.empty((0, X_train.shape[1]), dtype=np.float32)
    X_calibrated_test = _transform_or_empty(
        preprocessor, calibrated_test_features, X_train.shape[1]
    )
    feature_names = preprocessor.get_feature_names_out().tolist()

    if preprocessor_output is not None:
        preprocessor_output = Path(preprocessor_output)
        preprocessor_output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(preprocessor, preprocessor_output)

    return DatasetBundle(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        X_test=X_test,
        y_test=y_test,
        test_attack_categories=test_attack_categories,
        X_calibration=X_calibration,
        y_calibration=y_calibration,
        calibration_attack_categories=calibration_attack_categories,
        X_calibrated_test=X_calibrated_test,
        y_calibrated_test=y_calibrated_test,
        calibrated_test_attack_categories=calibrated_test_attack_categories,
        calibration_enabled=calibration_enabled,
        feature_names=feature_names,
        raw_train_rows=raw_train_rows,
        raw_test_rows=raw_test_rows,
        original_column_count=original_column_count,
        selected_raw_feature_count=len(train_features.columns),
        validation_split_info=split_info,
        train_exclusions=train_exclusions,
        X_thr=X_thr,
        y_thr=y_thr,
        X_rep=X_rep,
        y_rep=y_rep,
        holdout_mask=holdout_mask,
        holdout_groups=holdout_groups,
        client_holdout_audit=holdout_audit,
    )


def load_and_preprocess_ciciot2023(
    cfg: DataConfig,
    seed: int,
    preprocessor_output: str | Path | None = None,
    load_test: bool = True,
    holdout_fraction: float = 0.0,
) -> DatasetBundle:
    """Load prepared CICIoT2023 train/validation/test CSV files.

    The raw 169 CSV shards must first be converted with prepare_ciciot2023.py.
    That script creates explicit, reproducible splits and stores both the binary
    label and the original attack name. The preprocessor is fit on training only.
    """
    train_path = Path(cfg.train_csv)
    val_path = Path(cfg.validation_csv or "")
    test_path = Path(cfg.test_csv)
    required = [("training", train_path), ("validation", val_path)]
    if load_test:
        required.append(("testing", test_path))
    for role, path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Prepared CICIoT2023 {role} file not found: {path}. "
                "Run 02_PREPARE_CICIOT2023_PILOT.bat or "
                "02_PREPARE_CICIOT2023_PAPER.bat first."
            )

    raw_train = pd.read_csv(train_path)
    raw_val = pd.read_csv(val_path)
    raw_test = pd.read_csv(test_path) if load_test else raw_train.iloc[0:0].copy()
    original_column_count = len(raw_train.columns)
    raw_train_rows = len(raw_train)
    raw_test_rows = len(raw_test)

    for role, frame in (("training", raw_train), ("validation", raw_val), ("testing", raw_test)):
        if role == "testing" and not load_test:
            continue
        if cfg.label_col not in frame:
            raise ValueError(f"Label column '{cfg.label_col}' missing from CICIoT2023 {role} file")
        if frame[cfg.label_col].nunique(dropna=False) < 2:
            raise ValueError(f"CICIoT2023 {role} split does not contain both binary classes")

    raw_train = _stratified_subsample(raw_train, cfg.label_col, cfg.max_train_samples, seed)
    raw_val = _stratified_subsample(raw_val, cfg.label_col, cfg.max_val_samples, seed + 1)
    raw_test = _stratified_subsample(raw_test, cfg.label_col, cfg.max_test_samples, seed + 2)

    y_train = raw_train[cfg.label_col].astype(int).to_numpy(dtype=np.int64)
    y_val = raw_val[cfg.label_col].astype(int).to_numpy(dtype=np.int64)
    y_test = raw_test[cfg.label_col].astype(int).to_numpy(dtype=np.int64)

    test_attack_categories = _attack_categories(raw_test, cfg)

    train_features = raw_train.drop(columns=[cfg.label_col, *cfg.drop_cols], errors="ignore")
    val_features = raw_val.drop(columns=[cfg.label_col, *cfg.drop_cols], errors="ignore")
    test_features = raw_test.drop(columns=[cfg.label_col, *cfg.drop_cols], errors="ignore")

    # Enforce identical feature schema and ordering across all prepared splits.
    missing_in_val = sorted(set(train_features.columns) - set(val_features.columns))
    missing_in_test = sorted(set(train_features.columns) - set(test_features.columns))
    extras_in_val = sorted(set(val_features.columns) - set(train_features.columns))
    extras_in_test = sorted(set(test_features.columns) - set(train_features.columns))
    if missing_in_val or missing_in_test or extras_in_val or extras_in_test:
        raise ValueError(
            "Prepared CICIoT2023 split schemas differ. "
            f"missing_in_val={missing_in_val[:5]}, missing_in_test={missing_in_test[:5]}, "
            f"extras_in_val={extras_in_val[:5]}, extras_in_test={extras_in_test[:5]}"
        )
    val_features = val_features[train_features.columns]
    test_features = test_features[train_features.columns]

    train_features = _sanitize_frame(train_features)
    val_features = _sanitize_frame(val_features)
    test_features = _sanitize_frame(test_features)

    missing_categorical = [column for column in cfg.categorical_cols if column not in train_features]
    if missing_categorical:
        raise ValueError(f"Missing expected categorical columns: {missing_categorical}")
    categorical = list(cfg.categorical_cols)
    numeric = [column for column in train_features.columns if column not in categorical]
    if not numeric and not categorical:
        raise ValueError("No usable CICIoT2023 features remain after dropping label columns")

    train_features, y_train, train_exclusions = _drop_conflicting_train_groups(
        train_features, y_train, cfg
    )
    split_info = {
        "protocol": "explicit_prepared_validation_file",
        "train_rows": int(len(y_train)), "validation_rows": int(len(y_val)),
        "train_attack": int((y_train == 1).sum()), "train_benign": int((y_train == 0).sum()),
        "validation_attack": int((y_val == 1).sum()), "validation_benign": int((y_val == 0).sum()),
    }

    thr_frame = None
    y_thr = None
    if cfg.threshold_calibration_fraction > 0:
        val_features, thr_frame, y_val, y_thr, thr_info = _split_threshold_partition(
            val_features, y_val, cfg.threshold_calibration_fraction, seed + 17
        )
        split_info["threshold_calibration"] = thr_info
        split_info["validation_rows"] = int(len(y_val))

    rep_frame = None
    y_rep = None
    if cfg.validation_three_way:
        val_features, thr_frame, rep_frame, y_val, y_thr, y_rep, three_info = _split_three_way(val_features, y_val, seed + 23)
        split_info["three_way"] = three_info
        split_info["validation_rows"] = int(len(y_val))

    transformers = []
    if categorical:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical))
    if numeric:
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric_pipeline, numeric))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=True,
    )
    holdout_mask = holdout_groups = None
    holdout_audit = {"enabled": False}
    if holdout_fraction > 0:
        # SUPP_V2: the holdout is carved from the TRAINING partition (after conflict exclusion) before the preprocessor is fitted; the validation / threshold /
        # report partitions come from separate prepared files and are neither used to choose the holdout nor changed by it.
        X_train, holdout_mask, holdout_groups, holdout_audit = fit_preprocessor_with_client_holdout(preprocessor, train_features, y_train, holdout_fraction, seed)
    else:
        X_train = preprocessor.fit_transform(train_features).astype(np.float32, copy=False)
    X_val = preprocessor.transform(val_features).astype(np.float32, copy=False)
    X_thr = None if thr_frame is None else _transform_or_empty(preprocessor, thr_frame, X_train.shape[1])
    X_rep = None if rep_frame is None else _transform_or_empty(preprocessor, rep_frame, X_train.shape[1])
    X_test = _transform_or_empty(preprocessor, test_features, X_train.shape[1])
    feature_names = preprocessor.get_feature_names_out().tolist()

    if preprocessor_output is not None:
        preprocessor_output = Path(preprocessor_output)
        preprocessor_output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(preprocessor, preprocessor_output)

    empty_X = np.empty((0, X_train.shape[1]), dtype=np.float32)
    empty_y = np.empty((0,), dtype=np.int64)
    empty_categories = np.empty((0,), dtype=str)
    return DatasetBundle(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        X_test=X_test,
        y_test=y_test,
        test_attack_categories=test_attack_categories,
        X_calibration=empty_X,
        y_calibration=empty_y,
        calibration_attack_categories=empty_categories,
        X_calibrated_test=X_test,
        y_calibrated_test=y_test,
        calibrated_test_attack_categories=test_attack_categories,
        calibration_enabled=False,
        feature_names=feature_names,
        raw_train_rows=raw_train_rows,
        raw_test_rows=raw_test_rows,
        original_column_count=original_column_count,
        selected_raw_feature_count=len(train_features.columns),
        validation_split_info=split_info,
        train_exclusions=train_exclusions,
        X_thr=X_thr,
        y_thr=y_thr,
        X_rep=X_rep,
        y_rep=y_rep,
        holdout_mask=holdout_mask,
        holdout_groups=holdout_groups,
        client_holdout_audit=holdout_audit,
    )


def load_dataset(
    cfg: DataConfig,
    seed: int,
    preprocessor_output: str | Path | None = None,
    load_test: bool = True,
    holdout_fraction: float = 0.0,
) -> DatasetBundle:
    """Dispatch to the dataset-specific, leakage-safe loader.

    ``load_test=False`` guarantees the test CSV is never opened.
    """
    if cfg.dataset_name == "unsw_nb15":
        return load_and_preprocess_unsw(cfg, seed, preprocessor_output, load_test, holdout_fraction)
    if cfg.dataset_name == "ciciot2023":
        return load_and_preprocess_ciciot2023(cfg, seed, preprocessor_output, load_test, holdout_fraction)
    raise ValueError(f"Unsupported dataset: {cfg.dataset_name}")
