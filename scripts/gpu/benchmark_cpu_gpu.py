"""End-to-end CPU vs GPU benchmark of the REAL Phase-6C training job (run_one.py), in separate Python environments.

Each case runs the unmodified job as a subprocess (process start -> exit) and records: external wall time, time before the
first round (imports + CUDA init + data loading + preprocessing + partitioning + initial evaluation), mean per-round time
and the final-reporting time. Per-round data comes from the live log. Nothing in the locked configs/manifest is touched;
temporary configs are written to the output folder.

usage: python scripts/gpu/benchmark_cpu_gpu.py --cpu-python PY --gpu-python PY --out results_gpu_bench
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    # (label, dataset, arm, rounds)
    ("unsw/reference r30 #1", "unsw", "reference", 30),
    ("unsw/reference r30 #2", "unsw", "reference", 30),
    ("ciciot/reference r30", "ciciot", "reference", 30),
    ("unsw/clean_centralized r30", "unsw", "clean_centralized", 30),
    ("ciciot/clean_centralized r3", "ciciot", "clean_centralized", 3),
]


def run_case(label, dataset, arm, rounds, device, python, out_root: Path, seed: int = 12) -> dict:
    tag = f"{dataset}_{arm}_r{rounds}_{device}_{int(time.time())}"
    run_dir = out_root / tag
    cfg = yaml.safe_load((ROOT / "configs" / "phase6c" / f"{dataset}_{arm}.yaml").read_text(encoding="utf-8"))
    cfg["fl"]["rounds"] = rounds
    cfg["experiment"]["device"] = device
    cfg_path = out_root / f"{tag}.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    env = dict(os.environ, PYTHONHASHSEED="0", IOTFL_LIVE="1", PYTHONPATH=str(ROOT / "scripts" / "live"),
               PYTHONUNBUFFERED="1")
    if device.startswith("cuda"):
        env["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    t0 = time.perf_counter()
    proc = subprocess.run([python, str(ROOT / "scripts" / "phase6c" / "run_one.py"), "--config", str(cfg_path),
                           "--seed", str(seed), "--out", str(run_dir)], capture_output=True, text=True, env=env, cwd=str(ROOT))
    wall = time.perf_counter() - t0
    result = {"case": label, "device": device, "dataset": dataset, "arm": arm, "rounds": rounds,
              "exit_code": proc.returncode, "wall_seconds": round(wall, 1), "run_dir": str(run_dir)}
    if proc.returncode != 0:
        result["stderr_tail"] = proc.stderr[-1500:]
        return result
    rows = [json.loads(l) for l in (run_dir / "live_progress.jsonl").read_text().splitlines()]
    last = rows[-1]
    per_round = [r["round_seconds"] for r in rows[1:] if r.get("round_seconds") is not None]
    result.update({
        "seconds_before_first_round": round(rows[0]["elapsed_s"], 1),
        "mean_seconds_per_round": round(sum(per_round) / len(per_round), 2),
        "seconds_after_last_round": round(wall - last["elapsed_s"], 1),
        "final_val_auc": last["val_roc_auc"], "final_val_f1": last["val_f1"], "final_train_loss": last["train_loss"],
        "device_reported": last["device"],
    })
    rec = json.loads((run_dir / "run_record.json").read_text())
    result["torch"] = rec["torch"]
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpu-python", required=True)
    ap.add_argument("--gpu-python", required=True)
    ap.add_argument("--out", default="results_gpu_bench")
    ap.add_argument("--only", default="", help="substring filter on the case label")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for label, dataset, arm, rounds in CASES:
        if args.only and args.only not in label:
            continue
        for device, python in (("cpu", args.cpu_python), ("cuda", args.gpu_python)):
            print(f"== {label} on {device} ...", flush=True)
            res = run_case(label, dataset, arm, rounds, device, python, out)
            results.append(res)
            print(json.dumps({k: v for k, v in res.items() if k not in ("run_dir", "stderr_tail")}), flush=True)
            if res["exit_code"] != 0:
                print("   FAILED:", res.get("stderr_tail", "")[-600:], flush=True)
            (out / "benchmark_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
