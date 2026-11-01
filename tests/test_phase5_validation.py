"""Phase-5 regression tests: UNSW group-disjoint validation, conflict exclusion,
CICIoT2023 file-group protocol artefacts. Synthetic frames are used only to
exercise code paths."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config, DataConfig
from src.data import load_dataset
from src.data_integrity import conflicting_fingerprint_groups, predictor_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def _repeated_unsw(path: Path, n_unique=300, repeats=4, seed=5):
    """Training file where every predictor vector appears several times, including
    some vectors that carry both labels."""
    rng = np.random.default_rng(seed)
    base = pd.DataFrame({
        "dur": rng.normal(0, 1, n_unique),
        "sbytes": rng.integers(0, 50, n_unique).astype(float),
        "proto": rng.choice(["tcp", "udp"], n_unique),
        "service": rng.choice(["-", "http"], n_unique),
        "state": rng.choice(["FIN", "CON"], n_unique),
    })
    base["label"] = (base["dur"] + rng.normal(0, 0.5, n_unique) > 0).astype(int)
    frames = []
    for r in range(repeats):
        f = base.copy()
        if r == 3:  # conflicting copies: flip the label of the first 20 vectors
            f.loc[:19, "label"] = 1 - f.loc[:19, "label"]
        frames.append(f)
    train = pd.concat(frames, ignore_index=True).sample(frac=1.0, random_state=1).reset_index(drop=True)
    train.insert(0, "id", np.arange(1, len(train) + 1))
    train["attack_cat"] = np.where(train["label"] == 1, "Generic", "Normal")
    test = train.sample(200, random_state=2).reset_index(drop=True)
    test["id"] = np.arange(1, len(test) + 1)
    train.to_csv(path / "tr.csv", index=False)
    test.to_csv(path / "te.csv", index=False)
    return train, test


def _cfg(path: Path, mode: str, exclude=False) -> DataConfig:
    return DataConfig(dataset_name="unsw_nb15", train_csv=str(path / "tr.csv"), test_csv=str(path / "te.csv"),
                      label_col="label", attack_category_col="attack_cat", drop_cols=["id", "attack_cat"],
                      categorical_cols=["proto", "service", "state"], validation_fraction=0.15,
                      enable_calibrated_evaluation=False, validation_split=mode,
                      exclude_conflicting_train_groups=exclude)


def _fingerprints(frame: pd.DataFrame):
    feats = frame.drop(columns=["id", "attack_cat", "label"])
    return predictor_fingerprint(feats, list(feats.columns))


def test_group_disjoint_validation_has_zero_predictor_overlap(tmp_path):
    train, _ = _repeated_unsw(tmp_path)
    hist = load_dataset(_cfg(tmp_path, "random_stratified"), seed=2)
    grp = load_dataset(_cfg(tmp_path, "group_disjoint"), seed=2)
    assert hist.validation_split_info["validation_rows_sharing_predictor_vector_with_train"] > 0, \
        "documents the historical leakage"
    info = grp.validation_split_info
    assert info["validation_rows_sharing_predictor_vector_with_train"] == 0
    assert info["train_rows"] + info["validation_rows"] == len(train)
    assert len(grp.y_train) == info["train_rows"] and len(grp.y_val) == info["validation_rows"]
    # both classes present on both sides, validation fraction close to requested
    assert grp.y_val.min() == 0 and grp.y_val.max() == 1
    assert abs(info["validation_rows"] / len(train) - 0.15) < 0.06


def test_group_disjoint_is_deterministic(tmp_path):
    _repeated_unsw(tmp_path)
    a = load_dataset(_cfg(tmp_path, "group_disjoint"), seed=3)
    b = load_dataset(_cfg(tmp_path, "group_disjoint"), seed=3)
    assert np.array_equal(a.y_val, b.y_val) and np.array_equal(a.X_val, b.X_val)
    assert a.validation_split_info == b.validation_split_info


def test_group_disjoint_keeps_conflicting_groups_together(tmp_path):
    train, _ = _repeated_unsw(tmp_path)
    fp = _fingerprints(train)
    manifest = conflicting_fingerprint_groups(fp, train["label"].to_numpy())
    assert len(manifest) >= 15
    from src.data import _group_disjoint_validation_split

    feats = train.drop(columns=["id", "attack_cat", "label"])
    tr, va, fingerprint, _ = _group_disjoint_validation_split(feats, train["label"].to_numpy(), 0.15, 2)
    assert set(fingerprint[tr]).isdisjoint(set(fingerprint[va]))


def test_conflict_exclusion_only_touches_training_and_writes_manifest(tmp_path):
    _repeated_unsw(tmp_path)
    plain = load_dataset(_cfg(tmp_path, "group_disjoint"), seed=2)
    excl = load_dataset(_cfg(tmp_path, "group_disjoint", exclude=True), seed=2)
    assert excl.train_exclusions is not None and len(excl.train_exclusions) >= 0
    assert len(excl.y_train) <= len(plain.y_train)
    assert np.array_equal(plain.y_val, excl.y_val) and np.array_equal(plain.y_test, excl.y_test)
    assert plain.train_exclusions is None
    processed = pd.DataFrame(excl.X_train)
    kept = conflicting_fingerprint_groups(predictor_fingerprint(processed, list(processed.columns)), excl.y_train)
    assert len(kept) == 0, "no predictor-identical group with both labels may remain in training"
    assert len(plain.y_train) - len(excl.y_train) == int(excl.train_exclusions["rows"].sum())


def test_transformers_fit_on_group_disjoint_training_partition_only(tmp_path):
    import joblib

    _repeated_unsw(tmp_path)
    pre = tmp_path / "pre.joblib"
    bundle = load_dataset(_cfg(tmp_path, "group_disjoint"), seed=2, preprocessor_output=pre)
    fitted = joblib.load(pre)
    scaler = fitted.named_transformers_["numeric"].named_steps["scaler"]
    assert scaler.n_samples_seen_ == len(bundle.y_train)


def test_config_rejects_unknown_validation_split():
    cfg = Config()
    cfg.data.validation_split = "bogus"
    with pytest.raises(ValueError):
        cfg.validate()


@pytest.mark.skipif(not (ROOT / "data" / "UNSW_NB15_testing-set.csv").exists(), reason="UNSW data not present")
def test_real_unsw_group_disjoint_split_and_official_test_untouched():
    import hashlib

    cfg = Config.from_yaml(ROOT / "configs" / "unsw_nb15_groupdisjoint_v2.yaml")
    bundle = load_dataset(cfg.data, seed=2)
    info = bundle.validation_split_info
    assert info["validation_rows_sharing_predictor_vector_with_train"] == 0
    assert info["train_rows"] + info["validation_rows"] == 175_341
    assert len(bundle.y_test) == 82_332
    digest = hashlib.sha256((ROOT / "data" / "UNSW_NB15_testing-set.csv").read_bytes()).hexdigest()
    assert digest == "734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559"


FG = ROOT / "data" / "CICIoT2023" / "prepared_verified_v2_filegroup"


@pytest.mark.skipif(not FG.exists(), reason="file-group dataset not present")
def test_filegroup_dataset_protocol_invariants():
    meta = json.loads((FG / "preparation_metadata.json").read_text(encoding="utf-8"))
    assert meta["split_mode"] == "file_group" and meta["cross_split_key"] == "features"
    assert len(meta["ungrouped_classes_row_stratified"]) == 17
    assignment = meta["file_group_assignment"]
    assert len(assignment) == 290
    # whole files only in a single split for grouped classes
    sources = {}
    for split in ("train", "validation", "test"):
        prov = pd.read_csv(FG / f"{split}_provenance.csv.gz")
        sources[split] = set(prov["_src_file"].str.replace("\\", "/", regex=False))
    grouped = set(assignment)
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        assert not (sources[a] & sources[b] & grouped)
    for split in ("train", "validation", "test"):
        for f in sources[split] & grouped:
            assert assignment[f] == split
    for split, digest in meta["split_content_sha256"].items():
        from prepare_ciciot2023 import sha256_gzip_content
        assert sha256_gzip_content(FG / f"{split}.csv.gz") == digest
