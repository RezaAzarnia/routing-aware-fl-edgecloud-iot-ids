"""Generate the prespecified Phase-6B one-seed variant configurations.

Base: the Phase-6A no-Gaussian configurations. Common changes for ALL variants (so every pair is
comparable): trace_mode=matched, threshold_calibration_fraction=0.5, output_dir=results_phase6b.
Each variant then changes exactly the keys listed below. Nothing is tuned.
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
CFG = ROOT / "configs"
OUT = CFG / "phase6b"
OUT.mkdir(exist_ok=True)

VARIANTS = {
    "v0_reference_matched": {},
    "v1_no_imputation": {("failure", "recovery_enabled"): False},
    "v2_surrogate_cap_0p10": {("failure", "surrogate_total_weight_cap"): 0.10},
    "v3_uniform_random_selection": {("routing", "selection_policy"): "uniform_random"},
    "v4_coverage_aware_selection": {("routing", "selection_policy"): "coverage_aware"},
    "v5_packet_coupled_delivery": {("routing", "delivery_model"): "packet_coupled"},
    "v6_uniform_weighting": {("fl", "weighting"): "uniform"},
    "v7_gaussian_diagnostic_eps10": "DP",
    "v8_momentum0_lr0p5": {("fl", "server_momentum"): 0.0},
    "v9_momentum0_lr5p0_gain_matched": {("fl", "server_momentum"): 0.0, ("fl", "server_learning_rate"): 5.0},
}

for dataset in ("unsw", "ciciot"):
    base = yaml.safe_load((CFG / f"phase6a_{dataset}_no_dp.yaml").read_text(encoding="utf-8"))
    dp_privacy = yaml.safe_load((CFG / f"phase6a_{dataset}_dp_original.yaml").read_text(encoding="utf-8"))["privacy"]
    for name, changes in VARIANTS.items():
        cfg = yaml.safe_load(yaml.safe_dump(base))
        cfg["routing"]["trace_mode"] = "matched"
        cfg["data"]["threshold_calibration_fraction"] = 0.5
        cfg["experiment"].update({
            "name": f"phase6b_{dataset}_{name}", "method_name": name, "variant_name": name,
            "output_dir": "results_phase6b", "validation_only": True, "seed": 2,
        })
        if changes == "DP":
            cfg["privacy"] = dp_privacy
        else:
            for (section, key), value in changes.items():
                cfg[section][key] = value
        header = (f"# PHASE 6B one-seed variant '{name}' ({dataset}); base = phase6a_{dataset}_no_dp.yaml.\n"
                  f"# Common: trace_mode=matched, threshold_calibration_fraction=0.5. Variant changes: "
                  f"{'DP section of phase6a_%s_dp_original' % dataset if changes == 'DP' else {'.'.join(k): v for k, v in changes.items()} or 'none (reference under matched traces)'}\n")
        (OUT / f"{dataset}_{name}.yaml").write_text(header + yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
print("wrote", len(VARIANTS) * 2, "configs")
