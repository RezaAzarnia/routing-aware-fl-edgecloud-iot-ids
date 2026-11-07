"""Derive the new controlled-ablation configs from the locked Phase-6C reference configs (read-only)."""
import copy, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
NEW_ARMS = {
    # arm: (description, {dotted.path: value})
    "abl_reference_repro": ("reference re-run under the current code (reproducibility check)", {}),
    "abl_no_filter": ("reference with MAD distance filter disabled (plain weighted FedAvg over received+surrogate updates)",
                      {"aggregation.method": "fedavg"}),
    "abl_reference_gaussian_repro": ("reference_gaussian re-run under the current code", {}, "reference_gaussian"),
    "abl_privacy_clip_only": ("reference with central-DP clipping and per-client weight cap but zero Gaussian noise",
                              {"privacy.mode": "central_client", "privacy.noise_multiplier": 0.0,
                               "privacy.auto_calibrate_noise": False, "privacy.target_epsilon": None}),
}
def setpath(d, path, v):
    *ks, last = path.split("."); 
    for k in ks: d = d[k]
    d[last] = v
def main():
    for ds in ("ciciot", "unsw"):
        base = yaml.safe_load((ROOT / f"configs/phase6c/{ds}_reference.yaml").read_text(encoding="utf-8"))
        for arm, tup in NEW_ARMS.items():
            desc, ch = tup[0], tup[1]
            bname = tup[2] if len(tup) > 2 else "reference"
            c = copy.deepcopy(yaml.safe_load((ROOT / f"configs/phase6c/{ds}_{bname}.yaml").read_text(encoding="utf-8")))
            for p, v in ch.items(): setpath(c, p, v)
            c["experiment"].update(method_name=arm, variant_name=arm, name=f"ablation_v2_{ds}_{arm}",
                                   output_dir="results_ablation_controlled_v2/runs",
                                   algorithm_version="reference_v1_historical")
            out = ROOT / f"configs/ablation_v2/{ds}_{arm}.yaml"
            out.write_text(f"# ablation_v2 arm '{arm}' ({ds}): {desc}. Derived from configs/phase6c/{ds}_reference.yaml; changed: {ch or 'none'}\n"
                           + yaml.safe_dump(c, sort_keys=False), encoding="utf-8")
if __name__ == "__main__": main()
