"""Build the Phase-6C configurations and the immutable experiment manifest.

usage: python scripts/phase6c/build_manifest.py
Writes configs/phase6c/*.yaml, docs/phase6c/EXPERIMENT_MANIFEST.json and EXPERIMENT_MANIFEST.sha256.
The manifest is locked by its own hash; any later edit is detected by every consumer.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p6c_common import (  # noqa: E402
    DEFAULT_REQUIRED_ARTIFACTS, code_fingerprint, git_head, manifest_hash, now_utc, sha256_file,
)

SEEDS = [12, 13, 14, 15, 16]
DATASETS = ["unsw", "ciciot"]
ROUNDS = 30
CFG_DIR = ROOT / "configs" / "phase6c"
FG = "data/CICIoT2023/prepared_verified_v2_filegroup"

REF, COR = "reference_v1_historical", "corrected_v2_phase6c"


def clean(c):
    c["routing"]["enabled"] = False
    c["failure"]["enabled"] = False
    c["failure"]["recovery_enabled"] = False
    c["attack"]["attack_type"] = "none"
    c["attack"]["malicious_fraction"] = 0.0
    c["privacy"].update({"mode": "none", "auto_calibrate_noise": False, "target_epsilon": None})
    c["aggregation"]["method"] = "fedavg"


def scenario_fedavg(c, policy):
    c["routing"]["selection_policy"] = policy
    c["aggregation"]["method"] = "fedavg"
    c["failure"]["recovery_enabled"] = False


def corrected(c):
    c["routing"]["selection_policy"] = "coverage_aware"
    c["routing"]["delivery_model"] = "packet_coupled"
    c["aggregation"]["surrogate_handling"] = "post_filter_real_only"
    c["failure"]["surrogate_total_weight_cap"] = 0.10


def setp(section, key, value):
    def f(c):
        c[section][key] = value
    return f


def compose(*fns):
    def f(c):
        for fn in fns:
            fn(c)
    return f


def centralized(c):
    clean(c)
    c["fl"].update({"num_clients": 1, "clients_per_round": 1, "partition": "iid", "server_momentum": 0.0})


# arm id -> (group, description, algorithm_version, modifier, uses_dp, natural_assignment, compare_with)
ARMS = [
    ("clean_centralized", "baseline", "single client, clean data (upper reference)", REF, centralized, False, False, None),
    ("clean_fedavg", "baseline", "FedAvg, no attack/failure/routing", REF, clean, False, False, None),
    ("scenario_fedavg_random", "baseline", "FedAvg under attack+failure, uniform random selection, no imputation", REF,
     lambda c: scenario_fedavg(c, "uniform_random"), False, False, None),
    ("scenario_fedavg_topk", "baseline", "FedAvg under attack+failure, deterministic top-k routing, no imputation", REF,
     lambda c: scenario_fedavg(c, "top_k"), False, False, None),
    ("robust_random_no_imputation", "baseline", "distance filter, uniform random selection, no imputation", REF,
     compose(setp("routing", "selection_policy", "uniform_random"), setp("failure", "recovery_enabled", False)), False, False, None),
    ("reference", "main", "original method (top-k, filter, pre-filter median imputation), no Gaussian", REF, lambda c: None, False, False, None),
    ("reference_gaussian", "main", "reference + Gaussian perturbation (diagnostic epsilon only)", REF, lambda c: None, True, False, "reference"),
    ("corrected", "main", "coverage-aware + packet-coupled delivery + real-only filter + post-filter surrogates capped at 0.10", COR, corrected, False, False, "reference"),
    ("corrected_gaussian", "main", "corrected + Gaussian perturbation (diagnostic epsilon only)", COR, corrected, True, False, "corrected"),
    ("ctl_selection_uniform", "control", "reference with uniform random selection", REF, setp("routing", "selection_policy", "uniform_random"), False, False, "reference"),
    ("ctl_selection_coverage", "control", "reference with coverage-aware selection", REF, setp("routing", "selection_policy", "coverage_aware"), False, False, "reference"),
    ("ctl_imputation_none", "control", "reference without imputation", REF, setp("failure", "recovery_enabled", False), False, False, "reference"),
    ("ctl_imputation_cap010", "control", "reference with surrogate share capped at 0.10", REF, setp("failure", "surrogate_total_weight_cap", 0.10), False, False, "reference"),
    ("ctl_imputation_postfilter", "control", "reference with real-only filter and post-filter surrogates", REF, setp("aggregation", "surrogate_handling", "post_filter_real_only"), False, False, "reference"),
    ("ctl_delivery_coupled", "control", "reference with packet-coupled delivery", REF, setp("routing", "delivery_model", "packet_coupled"), False, False, "reference"),
    ("ctl_momentum0_lr0p5", "control", "reference with server momentum 0 (lr 0.5)", REF, setp("fl", "server_momentum", 0.0), False, False, "reference"),
    ("ctl_momentum0_lr5p0", "control", "reference with momentum 0 and gain-matched lr 5.0", REF,
     compose(setp("fl", "server_momentum", 0.0), setp("fl", "server_learning_rate", 5.0)), False, False, "reference"),
    ("ctl_weighting_uniform", "control", "reference with uniform client weights", REF, setp("fl", "weighting", "uniform"), False, False, "reference"),
    ("nat_reference", "natural_assignment", "reference, naturally assigned fixed malicious clients", REF, lambda c: None, False, True, None),
    ("nat_selection_uniform", "natural_assignment", "uniform random selection, natural attackers", REF, setp("routing", "selection_policy", "uniform_random"), False, True, "nat_reference"),
    ("nat_corrected", "natural_assignment", "corrected method, natural attackers", COR, corrected, False, True, "nat_reference"),
    ("fail0p0_reference", "failure_sensitivity", "reference, explicit failure probability 0.0", REF, setp("failure", "client_failure_probability", 0.0), False, False, "reference"),
    ("fail0p3_reference", "failure_sensitivity", "reference, explicit failure probability 0.3", REF, setp("failure", "client_failure_probability", 0.3), False, False, "reference"),
    ("fail0p3_corrected", "failure_sensitivity", "corrected, explicit failure probability 0.3", COR,
     compose(corrected, setp("failure", "client_failure_probability", 0.3)), False, False, "fail0p3_reference"),
]

# contrasts forming the Holm-adjusted primary family
PRIMARY_CONTRASTS = [
    ["corrected", "reference"], ["reference", "scenario_fedavg_topk"], ["reference", "scenario_fedavg_random"],
    ["reference_gaussian", "reference"], ["corrected_gaussian", "corrected"],
]


def build_config(dataset, arm):
    arm_id, group, desc, version, modifier, dp, natural, _ = arm
    base = yaml.safe_load((ROOT / "configs" / f"phase6a_{dataset}_no_dp.yaml").read_text(encoding="utf-8"))
    cfg = yaml.safe_load(yaml.safe_dump(base))
    cfg["routing"]["trace_mode"] = "matched"
    cfg["data"]["threshold_calibration_fraction"] = 0.0
    cfg["data"]["validation_three_way"] = True
    cfg["attack"]["assignment"] = "natural_fixed_clients" if natural else "exposure_controlled"
    modifier(cfg)
    if dp:
        dp_privacy = yaml.safe_load((ROOT / "configs" / f"phase6a_{dataset}_dp_original.yaml").read_text(encoding="utf-8"))["privacy"]
        cfg["privacy"] = dp_privacy
    cfg["experiment"].update({
        "name": f"phase6c_{dataset}_{arm_id}", "method_name": arm_id, "variant_name": arm_id,
        "algorithm_version": version, "output_dir": "results_phase6c", "validation_only": True, "device": "cpu",
        "early_stopping_patience": None, "create_plots": False, "save_probabilities": True,
    })
    cfg["data"]["test_csv"] = ""
    return cfg


def main() -> None:
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "phase6c").mkdir(parents=True, exist_ok=True)
    arms_meta, runs = [], []
    config_hashes = {}
    for dataset in DATASETS:
        for arm in ARMS:
            cfg = build_config(dataset, arm)
            path = CFG_DIR / f"{dataset}_{arm[0]}.yaml"
            header = (f"# PHASE 6C confirmatory arm '{arm[0]}' ({dataset}) - {arm[2]}\n"
                      f"# algorithm_version={arm[3]} group={arm[1]}. Locked by docs/phase6c/EXPERIMENT_MANIFEST.json; do not edit.\n")
            path.write_text(header + yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
            config_hashes[(dataset, arm[0])] = sha256_file(path)
    arms_meta = [{"arm": a[0], "group": a[1], "description": a[2], "algorithm_version": a[3],
                  "uses_gaussian": bool(a[5]), "natural_attacker_assignment": bool(a[6]), "compare_with": a[7]} for a in ARMS]
    hist = json.loads((ROOT / "docs" / "data_integrity" / "historical_data_hashes.json").read_text(encoding="utf-8"))
    fg_meta = json.loads((ROOT / FG / "preparation_metadata.json").read_text(encoding="utf-8"))
    order = 0
    for dataset in DATASETS:
        for seed in SEEDS:
            for arm in ARMS:
                order += 1
                rid = f"{dataset}__{arm[0]}__seed{seed}"
                runs.append({
                    "run_id": rid, "order": order, "dataset": dataset, "arm": arm[0], "seed": seed,
                    "config": f"configs/phase6c/{dataset}_{arm[0]}.yaml",
                    "config_sha256": config_hashes[(dataset, arm[0])],
                    "out_dir": f"results_phase6c/{dataset}/{arm[0]}/seed_{seed}",
                })
    manifest = {
        "schema": 1,
        "created_utc": now_utc(),
        "purpose": "Phase 6C confirmatory five-seed experiments (training stage; final test locked)",
        "git_commit_at_build": git_head(),
        "code_fingerprint": code_fingerprint(),
        "seeds": SEEDS,
        "rounds": ROUNDS,
        "datasets": {
            "unsw": {
                "training_csv": "data/UNSW_NB15_training-set.csv",
                "training_sha256": hist["unsw"]["UNSW_NB15_training-set.csv"]["sha256"],
                "validation_protocol": "group_disjoint train/validation, then three-way calibration/selection/report",
            },
            "ciciot": {
                "prepared_dir": FG,
                "content_sha256": {k: v for k, v in fg_meta["split_content_sha256"].items() if k in ("train", "validation")},
                "metadata_sha256": sha256_file(ROOT / FG / "preparation_metadata.json"),
                "feature_count": 39,
                "provenance": "byte-equivalent to a third-party release; official UNB provenance unverified",
            },
        },
        "locked_test": {
            "unsw": {"path": "data/UNSW_NB15_testing-set.csv", "kind": "csv",
                     "sha256": hist["unsw"]["UNSW_NB15_testing-set.csv"]["sha256"],
                     "bytes": hist["unsw"]["UNSW_NB15_testing-set.csv"]["bytes"],
                     "rows": 82332, "duplicate_mask_reference": "data/UNSW_NB15_training-set.csv"},
            "ciciot": {"path": f"{FG}/test.csv.gz", "kind": "gzip_csv",
                       "content_sha256": fg_meta["split_content_sha256"]["test"], "rows": 300000},
        },
        "arms": arms_meta,
        "primary_contrasts": PRIMARY_CONTRASTS,
        "n_runs": len(runs),
        "runs": runs,
        "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS,
        "command": ["{python}", "scripts/phase6c/run_one.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "verify_training_semantics": True,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    out = ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.sha256").write_text(manifest["manifest_sha256"] + "\n", encoding="utf-8")
    print(f"configs: {len(config_hashes)} | runs: {len(runs)} | manifest sha256 {manifest['manifest_sha256']}")


if __name__ == "__main__":
    main()
