"""Build the Phase 7 configurations and the locked Phase 7 experiment manifest (no training).

usage: python scripts/phase7/build_phase7.py
Writes configs/phase7/*.yaml and docs/phase7/EXPERIMENT_MANIFEST.json (+ .sha256). Phase 6C files are only READ.
Unchanged comparator arms are verbatim copies of their locked Phase 6C configs (identical SHA-256, recorded as
phase6c_config_sha256); the guard arms differ only in aggregation.min_real_updates and the version labels.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import (DEFAULT_REQUIRED_ARTIFACTS, code_fingerprint, git_head, manifest_hash, now_utc,  # noqa: E402
                        sha256_text_file)

SEEDS = [17, 18, 19, 20, 21]            # confirmatory seeds, disjoint from the inspected Phase 6C seeds 12-16
ROUNDS = 30
P6C = ROOT / "configs" / "phase6c"
OUT = ROOT / "configs" / "phase7"
GLOBS = ["src/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6c/run_one.py", "scripts/phase6a/run_validation_only.py",
         "scripts/phase6b/run_variant.py", "prepare_ciciot2023.py", "configs/phase7/*.yaml"]
GUARD = 3   # median/MAD filtering cannot discriminate an outlier below 3 samples (n=2: both points equidistant from the median)

# arm -> (description, source phase6c arm, guard?, version label, role)
ARMS = {
    "reference": ("Phase 6C reference (historical comparator, unchanged)", "reference", False, None, "comparator"),
    "corrected": ("Phase 6C corrected (historical comparator, unchanged)", "corrected", False, None, "comparator"),
    "p7_corrected_guard": ("corrected + abstain when <3 real updates delivered", "corrected", True, "corrected_v3_phase7_guard", "phase7"),
    "fail0p3_reference": ("reference, explicit failure probability 0.3 (comparator)", "fail0p3_reference", False, None, "comparator"),
    "fail0p3_corrected": ("corrected, failure 0.3 (comparator)", "fail0p3_corrected", False, None, "comparator"),
    "fail0p3_p7_corrected_guard": ("corrected + guard, failure 0.3", "fail0p3_corrected", True, "corrected_v3_phase7_guard", "phase7"),
    "ctl_delivery_coupled": ("reference with packet-coupled delivery (channel-only control)", "ctl_delivery_coupled", False, None, "comparator"),
    "p7_delivery_guard": ("reference + packet-coupled delivery + guard (guard isolated from the corrected bundle)", "ctl_delivery_coupled", True,
                          "reference_v1_historical+p7_guard", "phase7"),
}
TIERS = {"unsw": "mandatory", "ciciot": "optional"}

PREREG = {
    "status": "PROPOSED - to be frozen when the user approves; Phase 6C seeds 12-16 were already inspected and motivated the guard (exploratory).",
    "confirmatory_seeds": SEEDS,
    "primary_dataset": "unsw",
    "primary_contrast": "fail0p3_p7_corrected_guard vs fail0p3_corrected (paired by seed)",
    "primary_outcomes": ["collapse count per arm (last-round AUC < 0.90 or max training loss > 100)", "paired mean difference in last-round AUC"],
    "secondary_outcomes": ["best-checkpoint AUC, F1, recall_adr, FPR", "malicious updates accepted and honest updates rejected by number of real updates",
                           "rounds abstained", "selection Gini, delay, update delivery ratio"],
    "support_rule": "guard is called supported only if (a) collapse count does not increase, (b) mean last-round AUC difference >= +0.005 with the "
                    "guarded arm better in >=4/5 seeds, and (c) best-checkpoint AUC does not fall by more than 0.002; otherwise it is reported as not supported",
    "statistics": "exact paired Wilcoxon and sign-flip tests, effect sizes, t-intervals; n=5 cannot reach p<0.05, so conclusions rest on effect size and consistency",
    "non_regression": "reference, corrected, fail0p3_*, ctl_delivery_coupled must be re-run on the new seeds with their locked Phase 6C configs",
    "final_test": "never used",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    runs, order = [], 0
    for dataset in ("unsw", "ciciot"):
        for seed in SEEDS:
            for arm, (desc, src, guard, version, role) in ARMS.items():
                src_path = P6C / f"{dataset}_{src}.yaml"
                path = OUT / f"{dataset}_{arm}.yaml"
                if not guard:
                    path.write_bytes(src_path.read_bytes())
                else:
                    cfg = yaml.safe_load(src_path.read_text(encoding="utf-8"))
                    cfg["aggregation"]["min_real_updates"] = GUARD
                    exp = cfg["experiment"]
                    exp["algorithm_version"], exp["variant_name"], exp["method_name"] = version, arm, arm
                    exp["name"] = f"phase7_{dataset}_{arm}"
                    header = (f"# PHASE 7 arm '{arm}' ({dataset}) - {desc}\n# derived from configs/phase6c/{dataset}_{src}.yaml; only change: "
                              f"aggregation.min_real_updates={GUARD} and version labels. Locked by docs/phase7/EXPERIMENT_MANIFEST.json; do not edit.\n")
                    path.write_text(header + yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
                order += 1
                runs.append({"run_id": f"{dataset}__{arm}__seed{seed}", "order": order, "dataset": dataset, "arm": arm, "seed": seed,
                             "tier": TIERS[dataset], "config": f"configs/phase7/{dataset}_{arm}.yaml",
                             "config_sha256": sha256_text_file(path),
                             "phase6c_config_sha256": sha256_text_file(src_path) if not guard else None,
                             "out_dir": f"results_phase7/{dataset}/{arm}/seed_{seed}"})
    p6c = json.loads((ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
    manifest = {
        "schema": "iot-fl/phase7-manifest/1", "created_utc": now_utc(), "git_commit_at_build": git_head(),
        "purpose": "Phase 7 minimal confirmatory matrix for the minimum-real-update guard (new seeds 17-21)",
        "code_fingerprint": code_fingerprint(ROOT, GLOBS), "code_fingerprint_globs": GLOBS,
        "seeds": SEEDS, "rounds": ROUNDS, "datasets": p6c["datasets"],
        "arms": [{"arm": a, "description": d, "role": r, "algorithm_version": v or "unchanged", "min_real_updates": GUARD if g else 0}
                 for a, (d, s, g, v, r) in ARMS.items()],
        "preregistration": PREREG, "n_runs": len(runs), "n_runs_mandatory": sum(r["tier"] == "mandatory" for r in runs), "runs": runs,
        "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS,
        "command": ["{python}", "scripts/phase6c/run_one.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "verify_training_semantics": True,
        "phase6c_reference": {"tag": "phase6c-final-results", "manifest_sha256": p6c["manifest_sha256"], "code_fingerprint": p6c["code_fingerprint"]},
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    docs = ROOT / "docs" / "phase7"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "EXPERIMENT_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (docs / "EXPERIMENT_MANIFEST.sha256").write_text(manifest["manifest_sha256"] + "\n", encoding="utf-8")
    print(f"Phase 7 manifest: {len(runs)} runs ({manifest['n_runs_mandatory']} mandatory), sha256 {manifest['manifest_sha256'][:16]}...")


if __name__ == "__main__":
    main()
