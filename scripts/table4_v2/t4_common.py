"""Shared constants/helpers for the Table 4 v2 controlled replacement study (validation-only; reserved test data is never opened)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import (DEFAULT_REQUIRED_ARTIFACTS, atomic_write_json, code_fingerprint, git_head, load_manifest, log,  # noqa: E402,F401
                        manifest_hash, now_utc, pid_alive, sha256_bytes, sha256_file, sha256_gzip_content, sha256_text_file, verify_run_dir)

VERSION = "table4_controlled_v2"
OUT_ROOT = "results_table4_controlled_v2"
CFG_DIR = ROOT / "configs" / "table4_v2"
DOC_DIR = ROOT / "docs" / "table4_v2"
MANIFEST = DOC_DIR / "EXPERIMENT_MANIFEST.json"
DATASETS = ["unsw", "ciciot"]          # fast dataset first
SEEDS = [12, 13, 14, 15, 16]
ROUNDS = 30
FG = "data/CICIoT2023/prepared_verified_v2_filegroup"
PHASE6C_MANIFEST = ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"

# fingerprint of everything that determines training results for THIS study (the Phase 6C globs plus this study's configs/orchestrator)
FINGERPRINT_GLOBS = ["src/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6c/run_one.py", "scripts/phase6a/run_validation_only.py",
                     "scripts/phase6b/run_variant.py", "scripts/table4_v2/t4_common.py", "scripts/table4_v2/orchestrator.py",
                     "prepare_ciciot2023.py", "configs/table4_v2/*.yaml"]


def fingerprint(root: Path = ROOT) -> str:
    return code_fingerprint(root, FINGERPRINT_GLOBS)


# arm id -> (parent locked Phase 6C arm, role, description, dotted-path overrides applied to the parent)
NEW_ARMS = {
    "t4_e1_fedavg_random_path": ("scenario_fedavg_random", "E1",
                                 "FedAvg, uniform-random client selection, RANDOM path assignment, no recovery, no DP (routing disabled)",
                                 {"routing.path_policy": "random"}),
    "t4_e2_robust_random_path": ("robust_random_no_imputation", "E2",
                                 "MAD distance-filter FedAvg, uniform-random selection, RANDOM path assignment, no recovery, no DP (routing disabled)",
                                 {"routing.path_policy": "random"}),
    "t4_e3_dpfedavg_random_path": ("scenario_fedavg_random", "E3",
                                   "DP+FedAvg: E1 plus central-client clipping, per-client weight cap 0.1 and Gaussian noise calibrated to diagnostic eps~10",
                                   {"routing.path_policy": "random", "privacy.mode": "central_client", "privacy.target_epsilon": 10.0,
                                    "privacy.auto_calibrate_noise": True}),
    "t4_e4_proposed_eps20": ("reference_gaussian", "E4",
                             "Reference pipeline with central Gaussian; privacy target changed from eps~10 to eps~20 (calibration only)",
                             {"privacy.target_epsilon": 20.0}),
}
# existing locked comparators included in the method matrix (NOT re-run)
COMPARATORS = ["clean_fedavg", "scenario_fedavg_topk", "scenario_fedavg_random", "robust_random_no_imputation", "reference", "reference_gaussian"]
