"""Regression tests for CICIoT2023 preparation and dataset-integrity helpers.

Synthetic tiny CSV trees are used ONLY to test code paths; no experimental
result or manuscript number is derived from them.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "prepare_ciciot2023.py"
FEATURES = ["f1", "f2", "f3", "f4"]


def _write(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _make_raw(root: Path, duplicate_top_level: bool, conflict: bool = False) -> dict:
    rng = np.random.default_rng(7)

    def frame(n, shift):
        return pd.DataFrame(rng.normal(shift, 1.0, size=(n, len(FEATURES))), columns=FEATURES)

    parts = {
        "Benign_Final/Benign_Final.pcap.csv": frame(400, 0.0),
        "Benign_Final/Benign_Final1.pcap.csv": frame(400, 0.0),
        "ClassA/ClassA.pcap.csv": frame(300, 3.0),
        "ClassA/ClassA1.pcap.csv": frame(300, 3.0),
        "ClassB/ClassB.pcap.csv": frame(300, -3.0),
    }
    if conflict:
        shared = pd.DataFrame([[9.5, 9.5, 9.5, 9.5]] * 400, columns=FEATURES)
        key_b = "Benign_Final/Benign_Final1.pcap.csv"
        key_a = "ClassA/ClassA1.pcap.csv"
        parts[key_b] = pd.concat([parts[key_b], shared], ignore_index=True)
        parts[key_a] = pd.concat([parts[key_a], shared], ignore_index=True)
    for rel, df in parts.items():
        _write(root / rel, df)
    if duplicate_top_level:
        _write(root / "ClassB.pcap.csv", parts["ClassB/ClassB.pcap.csv"])
    return {rel: len(df) for rel, df in parts.items()}


def _run(raw: Path, out: Path, hashseed: str = "0", extra=()):
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    cmd = [sys.executable, str(SCRIPT), "--raw-dir", str(raw), "--output-dir", str(out),
           "--train-rows", "400", "--val-rows", "150", "--test-rows", "150",
           "--chunk-size", "200", "--seed", "11", "--force", *extra]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((out / "preparation_metadata.json").read_text(encoding="utf-8"))


def _load(out: Path, split: str) -> pd.DataFrame:
    return pd.read_csv(out / f"{split}.csv.gz")


def test_duplicate_source_file_is_processed_once(tmp_path):
    raw = tmp_path / "raw"
    sizes = _make_raw(raw, duplicate_top_level=True)
    meta = _run(raw, tmp_path / "out")
    assert [r["file"] for r in meta["excluded_duplicate_source_files"]] == ["ClassB.pcap.csv"]
    assert meta["source_csv_files"] == 5
    # class contribution equals ONE copy of the file, never two
    assert meta["source_rows_by_label"]["ClassB"] == sizes["ClassB/ClassB.pcap.csv"]
    manifest = pd.read_csv(tmp_path / "out" / "source_files_manifest.csv")
    assert (manifest["status"] == "processed").sum() == 5
    assert manifest["status"].str.startswith("excluded").sum() == 1
    assert (raw / "ClassB.pcap.csv").exists(), "raw files must never be deleted"


def test_repeated_file_contents_do_not_change_class_counts(tmp_path):
    with_dup = tmp_path / "with_dup"
    without = tmp_path / "without"
    _make_raw(with_dup, duplicate_top_level=True)
    _make_raw(without, duplicate_top_level=False)
    a = _run(with_dup, tmp_path / "oa")
    b = _run(without, tmp_path / "ob")
    assert a["source_rows_by_label"] == b["source_rows_by_label"]
    assert a["split_class_counts"] == b["split_class_counts"]


def test_stable_label_seed_is_independent_of_pythonhashseed():
    code = (
        "import sys; sys.path.insert(0, r'%s'); "
        "from prepare_ciciot2023 import stable_label_seed as s; print(s('Backdoor_Malware'))" % ROOT
    )
    legacy = "print(abs(hash('Backdoor_Malware')) % 1000000)"

    def run(snippet, seed):
        return subprocess.run([sys.executable, "-c", snippet], capture_output=True, text=True,
                              env=dict(os.environ, PYTHONHASHSEED=str(seed)), cwd=str(ROOT)).stdout.strip()

    values = {run(code, s) for s in (0, 1, 2)}
    assert len(values) == 1 and next(iter(values)).isdigit()
    assert len({run(legacy, s) for s in (0, 1, 2)}) > 1, \
        "documents the legacy defect: built-in hash() is salted per process"


def test_preparation_is_deterministic_across_processes(tmp_path):
    raw = tmp_path / "raw"
    _make_raw(raw, duplicate_top_level=True)
    m0 = _run(raw, tmp_path / "o0", hashseed="0")
    m1 = _run(raw, tmp_path / "o1", hashseed="12345")
    assert m0["split_content_sha256"] == m1["split_content_sha256"]
    assert m0["prepared_rows_by_split"] == m1["prepared_rows_by_split"]


def test_label_mapping_and_schema(tmp_path):
    raw = tmp_path / "raw"
    _make_raw(raw, duplicate_top_level=False)
    _run(raw, tmp_path / "out")
    for split in ("train", "validation", "test"):
        df = _load(tmp_path / "out", split)
        assert list(df.columns) == FEATURES + ["attack_category", "label"]
        assert set(df.loc[df.label == 0, "attack_category"]) == {"Benign_Final"}
        assert set(df.loc[df.label == 1, "attack_category"]) <= {"ClassA", "ClassB"}
        prov = pd.read_csv(tmp_path / "out" / f"{split}_provenance.csv.gz")
        assert len(prov) == len(df)


def test_no_cross_split_feature_overlap_with_label_blind_key(tmp_path):
    from src.data_integrity import cross_split_report

    raw = tmp_path / "raw"
    _make_raw(raw, duplicate_top_level=False, conflict=True)
    _run(raw, tmp_path / "out")  # default key = features
    tr, va, te = (_load(tmp_path / "out", s) for s in ("train", "validation", "test"))
    for ref, ev in ((te, tr), (te, va), (va, tr)):
        report = cross_split_report(ref, ev, FEATURES)
        assert report["rows_with_feature_vector_in_reference"] == 0


def test_cross_split_overlap_and_conflict_detection():
    from src.data_integrity import conflicting_label_groups, cross_split_report, within_split_report

    ref = pd.DataFrame({"f1": [1.0, 2.0, 3.0, 3.0], "f2": [0.0, -0.0, 1.0, 1.0],
                        "label": [0, 1, 0, 1], "attack_category": ["B", "A", "B", "A"]})
    ev = pd.DataFrame({"f1": [1.0, 2.0, 9.0], "f2": [0.0, 0.0, 0.0],
                       "label": [0, 0, 1], "attack_category": ["B", "B", "A"]})
    cross = cross_split_report(ref, ev, ["f1", "f2"])
    assert cross["rows_with_feature_vector_in_reference"] == 2  # -0.0 canonicalised to 0.0
    assert cross["same_binary_label"] == 1 and cross["conflicting_binary_label"] == 1
    within = within_split_report(ref, ["f1", "f2"])
    assert within["feature_only_duplicate_rows"] == 1
    assert within["conflicting_label_groups"] == 1
    groups = conflicting_label_groups(ref, ["f1", "f2"])
    assert len(groups) == 1 and int(groups.loc[0, "rows"]) == 2


def _tiny_unsw(path_dir: Path, n_train=400, n_test=120):
    rng = np.random.default_rng(3)

    def make(n, shift):
        y = rng.integers(0, 2, n)
        return pd.DataFrame({
            "id": np.arange(1, n + 1),
            "dur": rng.normal(shift, 1, n) + y,
            "sbytes": rng.normal(shift * 10, 5, n),
            "proto": rng.choice(["tcp", "udp"], n),
            "service": rng.choice(["-", "http"], n),
            "state": rng.choice(["FIN", "CON"], n),
            "attack_cat": np.where(y == 1, "Generic", "Normal"),
            "label": y,
        })

    train, test = make(n_train, 0.0), make(n_test, 5.0)
    train.to_csv(path_dir / "tr.csv", index=False)
    test.to_csv(path_dir / "te.csv", index=False)
    return train, test


def test_unsw_preprocessors_fit_on_train_only_and_test_is_preserved(tmp_path):
    import joblib
    from src.config import DataConfig
    from src.data import load_dataset

    _, test = _tiny_unsw(tmp_path)
    cfg = DataConfig(dataset_name="unsw_nb15", train_csv=str(tmp_path / "tr.csv"),
                     test_csv=str(tmp_path / "te.csv"), label_col="label",
                     attack_category_col="attack_cat", drop_cols=["id", "attack_cat"],
                     categorical_cols=["proto", "service", "state"],
                     validation_fraction=0.15, enable_calibrated_evaluation=False)
    pre = tmp_path / "pre.joblib"
    bundle = load_dataset(cfg, seed=2, preprocessor_output=pre)
    assert len(bundle.y_test) == len(test)
    assert np.array_equal(bundle.y_test, test["label"].to_numpy())
    assert not bundle.calibration_enabled
    fitted = joblib.load(pre)
    scaler = fitted.named_transformers_["numeric"].named_steps["scaler"]
    # train 'dur' mean is ~0.5; the shifted test partition (+5) must not influence it
    assert scaler.mean_[0] < 2.0
    assert abs(float(bundle.X_train[:, -2:].mean())) < 0.2
    assert abs(float(bundle.X_test[:, -2:].mean())) > 1.0


@pytest.mark.skipif(not (ROOT / "data" / "UNSW_NB15_training-set.csv").exists(), reason="UNSW data not present")
def test_official_unsw_training_file_unmodified_and_validation_only_load():
    """Default path: touches ONLY the training file (hash + validation-only load). The locked testing file is never opened here."""
    import hashlib
    from src.config import Config
    from src.data import load_dataset

    assert hashlib.sha256((ROOT / "data" / "UNSW_NB15_training-set.csv").read_bytes()).hexdigest() == \
        "bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa"
    cfg = Config.from_yaml(ROOT / "configs" / "full.yaml")
    cfg.data.train_csv = str(ROOT / "data" / "UNSW_NB15_training-set.csv")
    cfg.data.test_csv = ""
    bundle = load_dataset(cfg.data, seed=2, load_test=False)
    assert (len(bundle.y_train), len(bundle.y_val)) == (149_039, 26_302)


@pytest.mark.authorized_integrity
@pytest.mark.skipif(not (ROOT / "data" / "UNSW_NB15_testing-set.csv").exists(), reason="UNSW data not present")
def test_AUTHORIZED_official_unsw_test_file_unmodified_and_test_partition_preserved():
    """Opens the LOCKED UNSW test file (hash, row count, label equality). Runs only in the separately authorised integrity workflow:
    IOTFL_AUTHORIZED_FINAL_TEST_INTEGRITY=1 pytest -m authorized_integrity"""
    import hashlib
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
    from protected_access_guard import authorized
    from src.config import Config
    from src.data import load_dataset

    test_path = ROOT / "data" / "UNSW_NB15_testing-set.csv"
    with authorized(test_path):
        assert hashlib.sha256(test_path.read_bytes()).hexdigest() == "734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559"
        cfg = Config.from_yaml(ROOT / "configs" / "full.yaml")
        cfg.data.train_csv = str(ROOT / "data" / "UNSW_NB15_training-set.csv")
        cfg.data.test_csv = str(test_path)
        bundle = load_dataset(cfg.data, seed=2)
        assert (len(bundle.y_train), len(bundle.y_val), len(bundle.y_test)) == (149_039, 26_302, 82_332)
        raw_test = pd.read_csv(cfg.data.test_csv)
        assert np.array_equal(bundle.y_test, raw_test["label"].to_numpy())


MANIFEST = ROOT / "docs" / "data_integrity" / "ciciot2023_raw_manifest.csv"


@pytest.mark.skipif(not MANIFEST.exists() or not (ROOT / "data" / "CICIoT2023" / "raw_csv").exists(),
                    reason="manifest or raw data absent")
def test_raw_ciciot_matches_recorded_manifest():
    manifest = pd.read_csv(MANIFEST)
    raw = ROOT / "data" / "CICIoT2023" / "raw_csv"
    assert len(manifest) == 310 and manifest["sha256"].nunique() == 309
    for row in manifest.itertuples():
        path = raw / row.path
        assert path.exists() and path.stat().st_size == row.size


def _make_multifile_raw(root: Path) -> None:
    rng = np.random.default_rng(21)
    for cls, shift, nfiles in (("Benign_Final", 0.0, 4), ("ClassA", 3.0, 4), ("ClassB", -3.0, 3), ("Tiny", 6.0, 1)):
        for i in range(nfiles):
            n = 500 if cls != "Tiny" else 60
            frame = pd.DataFrame(rng.normal(shift, 1.0, size=(n, len(FEATURES))), columns=FEATURES)
            _write(root / cls / f"{cls}{i}.pcap.csv", frame)


def test_file_group_mode_keeps_capture_files_in_a_single_split(tmp_path):
    raw = tmp_path / "raw"
    _make_multifile_raw(raw)
    meta = _run(raw, tmp_path / "out", extra=("--split-mode", "file_group"))
    assert meta["split_mode"] == "file_group"
    assert meta["ungrouped_classes_row_stratified"] == ["Tiny"]
    sources = {}
    for split in ("train", "validation", "test"):
        prov = pd.read_csv(tmp_path / "out" / f"{split}_provenance.csv.gz")
        sources[split] = set(prov["_src_file"]) - {p for p in set(prov["_src_file"]) if p.startswith("Tiny")}
    assert sources["train"].isdisjoint(sources["validation"])
    assert sources["train"].isdisjoint(sources["test"])
    assert sources["validation"].isdisjoint(sources["test"])


def test_file_group_mode_is_deterministic_across_processes(tmp_path):
    raw = tmp_path / "raw"
    _make_multifile_raw(raw)
    a = _run(raw, tmp_path / "a", hashseed="1", extra=("--split-mode", "file_group"))
    b = _run(raw, tmp_path / "b", hashseed="99", extra=("--split-mode", "file_group"))
    assert a["split_content_sha256"] == b["split_content_sha256"]
    assert a["file_group_assignment"] == b["file_group_assignment"]


def test_assign_class_files_gives_every_split_a_file():
    sys.path.insert(0, str(ROOT))
    from prepare_ciciot2023 import assign_class_files_to_splits

    rows = {Path(f"f{i}.csv"): n for i, n in enumerate([900, 500, 100])}
    out = assign_class_files_to_splits(rows, {"train": 100, "validation": 10, "test": 10}, seed=5)
    assert sorted(out.values()) == ["test", "train", "validation"]
    assert out == assign_class_files_to_splits(rows, {"train": 100, "validation": 10, "test": 10}, seed=5)


def test_cross_split_hash_is_dtype_independent():
    sys.path.insert(0, str(ROOT))
    from prepare_ciciot2023 import canonical_row_hashes

    as_int = pd.DataFrame({"f1": [5, 7], "f2": [0, 1]})
    as_float = pd.DataFrame({"f1": [5.0, 7.0], "f2": [-0.0, 1.0]})
    legacy_int = pd.util.hash_pandas_object(as_int, index=False).to_numpy()
    legacy_float = pd.util.hash_pandas_object(as_float, index=False).to_numpy()
    assert not np.array_equal(legacy_int, legacy_float), "documents the legacy defect"
    assert np.array_equal(canonical_row_hashes(as_int, ["f1", "f2"]).to_numpy(),
                          canonical_row_hashes(as_float, ["f1", "f2"]).to_numpy())
