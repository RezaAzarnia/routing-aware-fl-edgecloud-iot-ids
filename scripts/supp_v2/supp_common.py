"""SUPP_V2 corrective protocol: shared constants and design. Independent of SUPP_V1 (which stays frozen); reuses only the audited Phase 6C helpers.

SUPP_V2 completes the 32 SUPP_V1 experiment identities that could not be executed (30 CICIoT2023 participation runs: client holdout not implemented for CICIoT2023;
2 chi_rec=0 runs: zero-weight-sum crash), through a versioned source overlay (src_v2/) that changes exactly two modules (data.py, experiment.py).
Every V2 config equals the corresponding locked SUPP_V1 config except for bookkeeping labels (asserted in build_configs.py)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import (DEFAULT_REQUIRED_ARTIFACTS, atomic_write_json, code_fingerprint, git_head, load_manifest, log,  # noqa: E402,F401
                        manifest_hash, now_utc, pid_alive, sha256_bytes, sha256_file, sha256_gzip_content, sha256_text_file, verify_run_dir)

VERSION = "supplementary_v2"
OUT_ROOT = "results_supplementary_v2"
CFG_DIR = ROOT / "configs" / "supp_v2"
DOC_DIR = ROOT / "docs" / "supp_v2"
MANIFEST = DOC_DIR / "EXPERIMENT_MANIFEST.json"
OVERLAY_DIR = ROOT / "src_v2"
V1_CFG_DIR = ROOT / "configs" / "supp_v1"
V1_MANIFEST = ROOT / "docs" / "supp_v1" / "EXPERIMENT_MANIFEST.json"
V1_ROOT = "results_supplementary_v1"
DATASETS = ["unsw", "ciciot"]
ROUNDS = 30
FG = "data/CICIoT2023/prepared_verified_v2_filegroup"
PHASE6C_MANIFEST = ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"
FINGERPRINT_GLOBS = ["src/*.py", "src_v2/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6a/run_validation_only.py", "scripts/phase6b/run_variant.py",
                     "scripts/supp_v2/run_one.py", "scripts/supp_v2/v2_overlay.py", "scripts/supp_v2/supp_common.py", "scripts/supp_v2/orchestrator.py",
                     "prepare_ciciot2023.py", "configs/supp_v2/*.yaml"]
V1_FINGERPRINT_GLOBS = ["src/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6c/run_one.py", "scripts/phase6a/run_validation_only.py",
                        "scripts/phase6b/run_variant.py", "scripts/supp_v1/supp_common.py", "scripts/supp_v1/orchestrator.py",
                        "scripts/supp_v1/timed_run.py", "prepare_ciciot2023.py", "configs/supp_v1/*.yaml"]
BOOKKEEPING = {"experiment.name", "experiment.output_dir"}


def fingerprint(root: Path = ROOT) -> str:
    return code_fingerprint(root, FINGERPRINT_GLOBS)


def v1_fingerprint(root: Path = ROOT) -> str:
    """Recomputes the SUPP_V1 code fingerprint; it must keep equalling the one locked in the V1 manifest (V2 must not alter any V1-fingerprinted file)."""
    return code_fingerprint(root, V1_FINGERPRINT_GLOBS)


S5 = [12, 13, 14, 15, 16]

# arm -> dict(family, dataset -> seeds, role, v1_status, desc). Config = the locked V1 config of the same (dataset, arm) with bookkeeping labels changed only.
PART = [("topk_indep", "top_k", 0.0), ("topk_coup", "top_k", 0.8), ("coverage_indep", "coverage_aware", 0.0), ("coverage_coup", "coverage_aware", 0.8),
        ("uniform_indep", "uniform_random", 0.0), ("uniform_coup", "uniform_random", 0.8)]
DESIGN = []   # list of dict(dataset, arm, seeds, family, role, v1, order)


def add(dataset, arm, seeds, family, role, v1, order):
    DESIGN.append(dict(dataset=dataset, arm=arm, seeds=seeds, family=family, role=role, v1=v1, order=order))


# Family R: regression controls (V1-verified identities re-executed under V2 code; gate BEFORE any corrective run is trusted)
add("unsw", "part_topk_indep", [12], "R_regression", "regression control: UNSW participation (holdout path, top-k selection, independent network)", "verified in SUPP_V1", 1)
add("unsw", "part_coverage_coup", [12], "R_regression", "regression control: UNSW participation (holdout path, coverage-aware selection, coupled network)", "verified in SUPP_V1", 2)
add("unsw", "part_uniform_coup", [13], "R_regression", "regression control: UNSW participation (holdout path, uniform-random selection, coupled network)", "verified in SUPP_V1", 3)
add("ciciot", "sens_k1p5", [12], "R_regression", "regression control: unaffected CICIoT2023 central-DP configuration without client holdout (positive weights)", "verified in SUPP_V1", 4)
# Family B: complete chi_rec=0 sensitivity arm (central-DP pipeline), both datasets, five seeds; seeds 12 and 14 double as positive-weight regression controls
for ds in DATASETS:
    add(ds, "sens_chi0_dp", S5, "B_chi0_dp", "corrective: complete chi_rec=0 arm under the no-valid-contribution policy (V1: seeds 12,14 verified, seed 13 crashed, seeds 15,16 never run)",
        "seeds 12,14 verified; seed 13 failed (zero weight sum); 15,16 not in V1", 10)
# Family E: CICIoT2023 participation (six arms x five seeds) with the leakage-safe V2 client holdout
for j, (arm, _, _) in enumerate(PART):
    add("ciciot", f"part_{arm}", S5, "E_participation_cic", "corrective: CICIoT2023 participation with leakage-safe client holdout",
        "not executable in SUPP_V1 (client holdout not implemented for CICIoT2023)", 20 + j)

# runs of these (dataset, arm, seed) identities are the V1-vs-V2 equivalence gate (the chi0 seeds 12 and 14 are verified in V1 and have zero abstention rounds there)
GATE_IDS = [f"v2__unsw__part_topk_indep__seed12", "v2__unsw__part_coverage_coup__seed12", "v2__unsw__part_uniform_coup__seed13", "v2__ciciot__sens_k1p5__seed12",
            "v2__unsw__sens_chi0_dp__seed12", "v2__unsw__sens_chi0_dp__seed14", "v2__ciciot__sens_chi0_dp__seed12", "v2__ciciot__sens_chi0_dp__seed14", "v2__ciciot__part_topk_indep__seed12",
            "v2__unsw__sens_chi0_dp__seed13"]   # last: end-to-end abstention test (V1 crashed at round 21)
