"""Shared constants and the experiment design for the supplementary reviewer-response experiments (validation-only; the reserved test data are never opened).

Every arm is derived from a LOCKED Phase 6C parent configuration (read-only) and differs from its parent only in the declared fields."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import (DEFAULT_REQUIRED_ARTIFACTS, atomic_write_json, code_fingerprint, git_head, load_manifest, log,  # noqa: E402,F401
                        manifest_hash, now_utc, pid_alive, sha256_bytes, sha256_file, sha256_gzip_content, sha256_text_file, verify_run_dir)

VERSION = "supplementary_v1"
OUT_ROOT = "results_supplementary_v1"
CFG_DIR = ROOT / "configs" / "supp_v1"
DOC_DIR = ROOT / "docs" / "supp_v1"
MANIFEST = DOC_DIR / "EXPERIMENT_MANIFEST.json"
DATASETS = ["unsw", "ciciot"]
ROUNDS = 30
FG = "data/CICIoT2023/prepared_verified_v2_filegroup"
PHASE6C_MANIFEST = ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"
FINGERPRINT_GLOBS = ["src/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6c/run_one.py", "scripts/phase6a/run_validation_only.py",
                     "scripts/phase6b/run_variant.py", "scripts/supp_v1/supp_common.py", "scripts/supp_v1/orchestrator.py",
                     "scripts/supp_v1/timed_run.py", "prepare_ciciot2023.py", "configs/supp_v1/*.yaml"]


def fingerprint(root: Path = ROOT) -> str:
    return code_fingerprint(root, FINGERPRINT_GLOBS)


S5 = [12, 13, 14, 15, 16]
S3 = [12, 13, 14]
BOTH5 = {"unsw": S5, "ciciot": S5}
SENS_SEEDS = {"unsw": S5, "ciciot": S3}            # five seeds where cheap (UNSW-NB15), three on CICIoT2023
SCALE_SEEDS = {"unsw": S3, "ciciot": S3}

# arm -> dict(family, parent, desc, ch (dotted overrides; a callable receives the parent config), seeds {dataset: [..]}, order, timed)
ARMS: dict[str, dict] = {}


def add(arm, family, parent, desc, ch, seeds, order, timed=False):
    ARMS[arm] = dict(family=family, parent=parent, desc=desc, ch=ch, seeds=seeds, order=order, timed=timed)


# ---- Family A: attack robustness (comment 12). 20% sign-flip (tau=5) cells are REUSED from locked Phase 6C (reference / scenario_fedavg_topk).
PIPES = {"ref": ("reference", "reference pipeline (routed top-k, median surrogates, MAD filter, no noise)"),
         "fedavg": ("scenario_fedavg_topk", "FedAvg baseline (routed top-k, no recovery, no filter)")}
ATTACKS = {"noatk": ({"attack.attack_type": "none", "attack.malicious_fraction": 0.0}, "no attack"),
           "sf10": ({"attack.malicious_fraction": 0.1}, "sign-flip tau=5, 10% of selected clients (1 of 10 per round)"),
           "sf30": ({"attack.malicious_fraction": 0.3}, "sign-flip tau=5, 30% of selected clients (3 of 10 per round)"),
           "bsf20": ({"attack.attack_scale": 1.0}, "norm-preserving sign-flip (tau=1: update -> -update, norm unchanged), 20% (2 of 10 per round)"),
           "lf20": ({"attack.attack_type": "label_flip"}, "label-flip data poisoning (all local labels inverted; honest-looking update norm), 20% (2 of 10 per round)")}
for order_base, atk in enumerate(ATTACKS):
    for pipe, (parent, pdesc) in PIPES.items():
        add(f"atk_{pipe}_{atk}", "A_attack", parent, f"{pdesc}; {ATTACKS[atk][1]}", ATTACKS[atk][0], BOTH5, 10 + order_base)

# ---- Family C: routing x surrogate 2x2 (the 'routing OFF, surrogate ON' cell is new; the other three cells are reused locked arms)
add("ix_routeoff_surron", "C_interaction", "reference",
    "Reference pipeline with routing OFF (uniform-random selection AND random path assignment) and surrogate imputation ON",
    {"routing.selection_policy": "uniform_random", "routing.path_policy": "random"}, BOTH5, 20)

# ---- Family B: one-factor-at-a-time sensitivity on the proposed pipeline (reference_gaussian, eps~10)
SENS = {"k1p5": ({"aggregation.distance_k": 1.5}, "MAD coefficient k=1.5"), "k3p5": ({"aggregation.distance_k": 3.5}, "MAD coefficient k=3.5"),
        "chi0": ({"failure.recovery_weight_factor": 0.0}, "surrogate coefficient chi_rec=0"),
        "chi0p25": ({"failure.recovery_weight_factor": 0.25}, "chi_rec=0.25"), "chi0p75": ({"failure.recovery_weight_factor": 0.75}, "chi_rec=0.75"),
        "alpha0p1": ({"fl.dirichlet_alpha": 0.1}, "Dirichlet alpha=0.1"), "alpha1p0": ({"fl.dirichlet_alpha": 1.0}, "Dirichlet alpha=1.0"),
        "C0p5x": ({"privacy.clip_norm": ("x", 0.5)}, "clipping threshold 0.5x the dataset reference"),
        "C2x": ({"privacy.clip_norm": ("x", 2.0)}, "clipping threshold 2x the dataset reference")}
for i, (k, (ch, d)) in enumerate(SENS.items()):
    if k.startswith("chi"):
        # In the central-DP pipeline the per-client cap (0.1) is infeasible whenever fewer than 10 updates are retained (92% of rounds), the weight
        # projection is then uniform and chi_rec is inert (verified by smoke test and arm sens_chi0_dp below), so chi_rec is varied on the non-private
        # reference pipeline, where raw weights (sample count x chi_rec) determine the aggregate.
        add(f"sens_{k}", "B_sensitivity", "reference", f"Reference pipeline without noise: {d}", ch, SENS_SEEDS, 30 + i)
    else:
        add(f"sens_{k}", "B_sensitivity", "reference_gaussian", f"Proposed pipeline (eps~10): {d}", ch, SENS_SEEDS, 30 + i)
add("sens_chi0_dp", "B_sensitivity", "reference_gaussian",
    "Proposed pipeline (eps~10) with chi_rec=0: tests whether chi_rec has any effect under the central-DP capped uniform projection (expected: none)",
    {"failure.recovery_weight_factor": 0.0}, SCALE_SEEDS, 40)

# ---- Family E: participation bias, independent vs correlated network/data (Phase 10 deltas, applied to both datasets, seeds 12-16)
P10 = {"attack.assignment": "natural_fixed_clients", "fl.client_holdout_fraction": 0.2}
for j, (pol, polcfg) in enumerate([("topk", "top_k"), ("coverage", "coverage_aware"), ("uniform", "uniform_random")]):
    for scen, coup in (("indep", 0.0), ("coup", 0.8)):
        add(f"part_{pol}_{scen}", "E_participation", "ctl_delivery_coupled",
            f"Phase-10 style: selection={polcfg}, network-data coupling={coup}, 20% client holdout, natural fixed attackers",
            {**P10, "routing.selection_policy": polcfg, "routing.network_data_coupling": coup}, BOTH5, 50 + 2 * j + (scen == "coup"))

# ---- Family D: scalability / resources (run alone, sequentially, through the timing wrapper)
SCALE = {"n25_k10": (25, 10, "N=25, 10 selected (fixed participation)"), "n25_k5": (25, 5, "N=25, 5 selected (proportional, rho=0.2)"),
         "n50_k10": (50, 10, "N=50, 10 selected (reference; fresh timing run)"), "n100_k10": (100, 10, "N=100, 10 selected (fixed participation)"),
         "n100_k20": (100, 20, "N=100, 20 selected (proportional, rho=0.2)")}
for i, (k, (n, m, d)) in enumerate(SCALE.items()):
    add(f"scale_{k}", "D_scalability", "reference_gaussian", f"Proposed pipeline (eps~10): {d}",
        {"fl.num_clients": n, "fl.clients_per_round": m}, SCALE_SEEDS, 80 + i, timed=True)
