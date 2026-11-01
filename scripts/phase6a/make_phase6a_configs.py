"""Generate the four prespecified Phase-6A configurations (validation-only, full scale).

Source configurations are left untouched. Differences from the source configs:
  * experiment.validation_only = true, data.test_csv = "" (test is never loaded)
  * experiment.early_stopping_patience = null (a fixed 30-round curve is required;
    best-validation checkpoint selection is retained)
  * experiment.device = cpu, seed = 2, output_dir = results_phase6a
  * data.enable_calibrated_evaluation = false (it is derived from the test file)
  * no-Gaussian variants: privacy.mode = none (no clipping, capping or noise)
Everything else (50 clients, 10/round, 30 rounds, 2 local epochs, batch 256,
lr 3e-4, MLP 128-96-64, routing, attack, failure and aggregation settings) is inherited.
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
CFG = ROOT / "configs"
SEED = 2


def load(name):
    return yaml.safe_load((CFG / name).read_text(encoding="utf-8"))


def finish(cfg, name, dp):
    cfg["data"]["test_csv"] = ""
    cfg["data"]["enable_calibrated_evaluation"] = False
    cfg["data"]["max_train_samples"] = None
    cfg["data"]["max_val_samples"] = None
    cfg["data"]["max_test_samples"] = None
    cfg["experiment"].update({
        "name": name, "method_name": "proposed_dp_original" if dp else "proposed_no_dp",
        "output_dir": "results_phase6a", "seed": SEED, "device": "cpu",
        "early_stopping_patience": None, "create_plots": False, "validation_only": True,
    })
    if not dp:
        cfg["privacy"]["mode"] = "none"
        cfg["privacy"]["auto_calibrate_noise"] = False
        cfg["privacy"]["target_epsilon"] = None
    return cfg


def write(fname, cfg, src, note):
    header = (f"# PHASE 6A (validation-only, full scale, seed {SEED}). Derived from {src}; the source file is untouched.\n"
              f"# {note}\n# See scripts/phase6a/make_phase6a_configs.py for the exact list of differences.\n")
    (CFG / fname).write_text(header + yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print("wrote", fname)


for dp in (False, True):
    tag = "dp_original" if dp else "no_dp"
    u = load("unsw_nb15_groupdisjoint_v2.yaml")
    write(f"phase6a_unsw_{tag}.yaml", finish(u, f"phase6a_unsw_{tag}", dp), "unsw_nb15_groupdisjoint_v2.yaml (from full.yaml)",
          "UNSW-NB15, group-disjoint validation; clip_norm 0.1 and target epsilon 10 as in the original config" if dp
          else "UNSW-NB15, group-disjoint validation; no Gaussian perturbation")
    c = load("ciciot2023_filegroup_v2_eps10.yaml")
    write(f"phase6a_ciciot_{tag}.yaml", finish(c, f"phase6a_ciciot_{tag}", dp), "ciciot2023_filegroup_v2_eps10.yaml (from ciciot2023_eps10.yaml)",
          "CICIoT2023 file-group protocol; clip_norm 0.05 and target epsilon 10 as in the original config" if dp
          else "CICIoT2023 file-group protocol; no Gaussian perturbation")
