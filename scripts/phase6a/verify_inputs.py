"""Verify (read-only) every input the Phase-6A runs depend on and lock the test files.

Writes docs/phase6a/input_verification.json. Fails (non-zero exit) on any mismatch.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prepare_ciciot2023 import sha256_gzip_content  # noqa: E402
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402

OUT = ROOT / "docs" / "phase6a"
OUT.mkdir(parents=True, exist_ok=True)
hist = json.loads((ROOT / "docs" / "data_integrity" / "historical_data_hashes.json").read_text())
FG = ROOT / "data" / "CICIoT2023" / "prepared_verified_v2_filegroup"
meta = json.loads((FG / "preparation_metadata.json").read_text())


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


report = {"checks": {}}
ok = True


def check(name, cond, detail=None):
    global ok
    report["checks"][name] = {"pass": bool(cond), "detail": detail}
    ok &= bool(cond)


for name, ref in hist["unsw"].items():
    check(f"unsw_sha256::{name}", sha(ROOT / "data" / name) == ref["sha256"], ref["sha256"])
for split, digest in meta["split_content_sha256"].items():
    check(f"cic_filegroup_content_sha256::{split}", sha256_gzip_content(FG / f"{split}.csv.gz") == digest, digest)
expected = {"train": 926133, "validation": 146626, "test": 300000}
for split, n in expected.items():
    check(f"cic_filegroup_rows::{split}", meta["prepared_rows_by_split"][split] == n, n)
check("cic_feature_count_39", len(meta["feature_columns"]) == 39)
check("cic_external_manifest_exact_match",
      json.loads((ROOT / "docs/data_integrity/external_manifest_comparison.json").read_text())["verdict"] == "EXACT_MATCH")
for cfg_name in ("phase6a_unsw_no_dp", "phase6a_unsw_dp_original", "phase6a_ciciot_no_dp", "phase6a_ciciot_dp_original"):
    cfg = Config.from_yaml(ROOT / "configs" / f"{cfg_name}.yaml")
    check(f"{cfg_name}::validation_only_and_blank_test", cfg.experiment.validation_only and cfg.data.test_csv == "")
    check(f"{cfg_name}::scale", (cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds, cfg.fl.local_epochs,
                                 cfg.fl.batch_size, cfg.fl.learning_rate, tuple(cfg.model.hidden_dims))
          == (50, 10, 30, 2, 256, 0.0003, (128, 96, 64)))
    bundle = load_dataset(cfg.data, seed=cfg.experiment.seed, load_test=False)
    info = bundle.validation_split_info
    check(f"{cfg_name}::no_test_rows_loaded", len(bundle.y_test) == 0)
    check(f"{cfg_name}::finite_inputs", bool(np.isfinite(bundle.X_train).all() and np.isfinite(bundle.X_val).all()))
    report.setdefault("splits", {})[cfg_name] = {
        "train": int(len(bundle.y_train)), "validation": int(len(bundle.y_val)),
        "features": int(bundle.X_train.shape[1]),
        "validation_rows_sharing_predictor_vector_with_train": info.get("validation_rows_sharing_predictor_vector_with_train"),
        "train_benign": int((bundle.y_train == 0).sum()), "train_attack": int((bundle.y_train == 1).sum()),
        "val_benign": int((bundle.y_val == 0).sum()), "val_attack": int((bundle.y_val == 1).sum()),
    }
    if cfg.data.dataset_name == "unsw_nb15":
        check(f"{cfg_name}::group_disjoint_zero_overlap",
              info["validation_rows_sharing_predictor_vector_with_train"] == 0)
    else:
        check(f"{cfg_name}::cic_split_sizes", (len(bundle.y_train), len(bundle.y_val)) == (926133, 146626))
report["test_files_locked"] = {
    "unsw_testing_csv_sha256": sha(ROOT / "data" / "UNSW_NB15_testing-set.csv"),
    "cic_filegroup_test_content_sha256": meta["split_content_sha256"]["test"],
}
report["all_pass"] = ok
(OUT / "input_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({k: v["pass"] for k, v in report["checks"].items()}, indent=1))
print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
