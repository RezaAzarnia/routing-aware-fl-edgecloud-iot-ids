"""Run exactly one (dataset, arm, seed) training job in validation-only mode.

usage: python scripts/phase6c/run_one.py --config CONFIG.yaml --seed 12 --out OUTDIR
Never loads test data. The orchestrator, not this script, marks a run COMPLETE.
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "phase6a"))
sys.path.insert(0, str(ROOT / "scripts" / "phase6b"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from p6c_common import git_head, sha256_text_file  # noqa: E402
from src.config import Config  # noqa: E402
from src.experiment import run_experiment  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    raw["experiment"]["seed"] = args.seed
    raw["experiment"]["exact_output_dir"] = str(Path(args.out))
    cfg = Config()
    tmp = Path(args.out).parent / f"_cfg_{Path(args.out).name}.yaml"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = Config.from_yaml(tmp)
    tmp.unlink()
    # hard guards: training must never touch the final-test files
    assert cfg.experiment.validation_only, "Phase-6C training runs must be validation-only"
    assert cfg.data.test_csv == "", "training configs must not reference a test file"

    start, cpu = time.perf_counter(), time.process_time()
    run_dir = Path(run_experiment(cfg))
    wall, cpu_s = time.perf_counter() - start, time.process_time() - cpu

    peak_mb = float("nan")
    try:
        from run_validation_only import peak_working_set_mb
        peak_mb = peak_working_set_mb()
    except Exception:  # noqa: BLE001
        pass

    diagnostics = {}
    try:
        from run_validation_only import diagnostics as diag_fn
        diagnostics = diag_fn(run_dir, cfg)
        from run_variant import client_fairness, gini
        net = pd.read_csv(run_dir / "network_metrics.csv")
        counts = np.array([int((net["client_id"] == c).sum()) for c in range(cfg.fl.num_clients)])
        diagnostics["participation"]["selection_gini"] = gini(counts)
        diagnostics["fairness"] = client_fairness(run_dir, cfg, counts)
    except Exception as exc:  # noqa: BLE001  (diagnostics are non-fatal; the error is recorded)
        diagnostics["diagnostics_error"] = repr(exc)
    (run_dir / "phase6c_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

    record = {
        "seed": args.seed, "config": str(args.config), "config_sha256": sha256_text_file(Path(args.config)),
        "code_commit": git_head(), "wall_seconds": round(wall, 1), "cpu_seconds": round(cpu_s, 1),
        "peak_working_set_mb": round(peak_mb, 1), "python": platform.python_version(),
        "torch": torch.__version__, "numpy": np.__version__, "pandas": pd.__version__,
        "algorithm_version": cfg.experiment.algorithm_version, "variant_name": cfg.experiment.variant_name,
    }
    (run_dir / "run_record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
