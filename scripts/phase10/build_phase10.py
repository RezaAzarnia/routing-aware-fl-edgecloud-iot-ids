"""Build the Phase 10 configurations and the locked, SEPARATE Phase 10 manifest (no training).
usage: python scripts/phase10/build_phase10.py     (reads Phase 6C configs/manifest only; writes configs/phase10/ and docs/phase10/)

Matrix: 4 selection policies x 2 network scenarios x 5 fresh seeds (22-26), UNSW-NB15 only, train/validation data only = 40 runs.
All arms share: Reference-style aggregation (MAD filter + momentum, pre-filter surrogates), packet-coupled delivery with <=2 retransmissions, matched traces,
20% sign-flip attackers assigned to a FIXED client set (natural_fixed_clients, so exposure depends on the policy and is measurable; the set is drawn from a
seed-only stream independent of the network and the policy), explicit failure 0.1, 30 rounds, and a 20% per-client holdout never used for training.
Policies: oracle_topk (historical top_k), oracle_coverage (historical coverage_aware, lambda 0.5), uniform (uniform_random), history_ucb (NEW, non-oracle UCB1 baseline).
Scenarios: independent (historical network<->data independence) and coupled (network_data_coupling = 0.8: minority-class share correlates with worse links).
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import DEFAULT_REQUIRED_ARTIFACTS, code_fingerprint, git_head, manifest_hash, now_utc, sha256_text_file  # noqa: E402

SEEDS = [22, 23, 24, 25, 26]            # fresh: seeds 12-21 were all inspected
COUPLING = 0.8
HOLDOUT = 0.2
POLICIES = {"oracle_topk": "top_k", "oracle_coverage": "coverage_aware", "uniform": "uniform_random", "history_ucb": "history_ucb"}
SCENARIOS = {"independent": 0.0, "coupled": COUPLING}
BASE = ROOT / "configs" / "phase6c" / "unsw_ctl_delivery_coupled.yaml"
OUT = ROOT / "configs" / "phase10"
GLOBS = ["src/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6c/run_one.py", "scripts/phase10/phase10_metrics.py", "configs/phase10/*.yaml"]

PREREG = {
    "status": "FROZEN BEFORE ANY RUN. Independent protocol: NOT part of the Phase 9E final-test hypotheses; touches no Phase 6C/7b/9E artifact.",
    "novelty_claim": "none. history_ucb is a standard UCB1-style historical-feedback baseline; the study measures the cost of the oracle-delivery assumption.",
    "primary_hypotheses": [
        {"id": "H1", "contrast": "history_ucb - oracle_topk", "scenario": "independent", "metric": "update_delivery_ratio", "expected": "negative (non-oracle ranking delivers fewer updates)"},
        {"id": "H2", "contrast": "history_ucb - oracle_topk", "scenario": "independent", "metric": "gini", "expected": "negative (history_ucb explores every client; participation is more equal)"},
        {"id": "H3", "contrast": "oracle_topk - uniform", "scenario": "coupled", "metric": "p10_client_recall", "expected": "negative (starving unreliable clients hurts their held-out recall when connectivity correlates with minority-class share)"},
        {"id": "H4", "contrast": "history_ucb - oracle_topk", "scenario": "coupled", "metric": "p10_client_recall", "expected": "positive"},
    ],
    "secondary": "all other pairwise policy contrasts per scenario for update_delivery_ratio, pdr, delay, gini, never_selected, max_selection_gap, malicious_share_of_selected, "
                 "worst/mean client holdout recall, best/last AUC and F1; policy x scenario interactions (difference of paired differences)",
    "statistics": "paired by seed (n=5): mean difference, SD, d_z, t-based 95% CI (df=4), seeds favouring each arm, exact sign-flip p (min 0.0625). No multiplicity correction; "
                  "with n=5 no contrast can be significant under any correction: ALL statements are exploratory; effect sizes and consistency (5/5 seeds) are the evidence.",
    "interpretation_limits": "single simulated network family; one coupling strength (0.8) and one coupling mechanism; UNSW-NB15 only; held-out client recall is measured on each client's "
                             "own holdout (same distribution), not on independent devices; simulation, not deployment. A null or opposite result is reported as such. "
                             "The oracle-gap result would quantify the manuscript's largest simulator limitation; it does not establish a new routing algorithm.",
    "validity_notes": "client-level recall without a holdout is not validly measurable (Phase 6C client_level_recall scores training data); the holdout fixes this only for Phase 10 runs",
    "validation_only": True, "final_test": "never used",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    runs, order, arms = [], 0, []
    for scen, strength in SCENARIOS.items():
        for pol, selection in POLICIES.items():
            arm = f"{pol}__{scen}"
            cfg = json.loads(json.dumps(base))
            cfg["routing"].update({"selection_policy": selection, "network_data_coupling": strength})
            cfg["fl"]["client_holdout_fraction"] = HOLDOUT
            cfg["attack"]["assignment"] = "natural_fixed_clients"
            e = cfg["experiment"]
            e.update({"algorithm_version": "reference_v1_historical+phase10_scenario", "variant_name": arm, "method_name": arm, "name": f"phase10_unsw_{arm}", "output_dir": "results_phase10"})
            path = OUT / f"unsw_{arm}.yaml"
            header = (f"# PHASE 10 arm '{arm}' (unsw). Derived from configs/phase6c/unsw_ctl_delivery_coupled.yaml; changes: routing.selection_policy={selection}, "
                      f"routing.network_data_coupling={strength}, fl.client_holdout_fraction={HOLDOUT}, attack.assignment=natural_fixed_clients, version labels.\n"
                      "# Locked by docs/phase10/EXPERIMENT_MANIFEST.json; do not edit.\n")
            path.write_text(header + yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
            arms.append({"arm": arm, "policy": pol, "selection_policy": selection, "scenario": scen, "network_data_coupling": strength})
            for seed in SEEDS:
                order += 1
                runs.append({"run_id": f"unsw__{arm}__seed{seed}", "order": order, "dataset": "unsw", "arm": arm, "seed": seed, "tier": "mandatory",
                             "config": f"configs/phase10/unsw_{arm}.yaml", "config_sha256": sha256_text_file(path), "phase6c_config_sha256": None,
                             "out_dir": f"results_phase10/unsw/{arm}/seed_{seed}"})
    p6c = json.loads((ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
    manifest = {"schema": "iot-fl/phase10-manifest/1", "created_utc": now_utc(), "git_commit_at_build": git_head(),
                "purpose": "Phase 10: cost of the oracle-delivery assumption and a correlated network/data scenario (4 policies x 2 scenarios x seeds 22-26)",
                "code_fingerprint": code_fingerprint(ROOT, GLOBS), "code_fingerprint_globs": GLOBS, "seeds": SEEDS, "rounds": 30, "datasets": {"unsw": p6c["datasets"]["unsw"]},
                "arms": arms, "preregistration": PREREG, "n_runs": len(runs), "n_runs_mandatory": len(runs), "runs": runs, "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS,
                "command": ["{python}", "scripts/phase6c/run_one.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"], "verify_training_semantics": True,
                "separation": {"phase6c_manifest_sha256": p6c["manifest_sha256"], "phase9e_frozen_tag": "phase9e-frozen",
                               "note": "independent protocol; not added to the Phase 9E final-test hypotheses; no final-test data"}}
    manifest["manifest_sha256"] = manifest_hash(manifest)
    docs = ROOT / "docs" / "phase10"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "EXPERIMENT_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (docs / "EXPERIMENT_MANIFEST.sha256").write_text(manifest["manifest_sha256"] + "\n", encoding="utf-8")
    print(f"Phase 10 manifest: {len(runs)} runs, sha256 {manifest['manifest_sha256'][:16]}...")


if __name__ == "__main__":
    main()
