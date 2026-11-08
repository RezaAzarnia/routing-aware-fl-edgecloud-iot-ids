"""Run scripts/phase6c/run_one.py in-process with passive wall-clock timers around the heavy components, and write timing_breakdown.json.

The timers only observe (they wrap functions and call them unchanged), so training results are identical to an untimed run. Accounting boundaries:
  local_training_s   : sum of Client.train_local wall time (all selected clients, serial execution in one process)
  server_aggregation_s: aggregate_updates (MAD distance filter / FedAvg) + capped weighting + clipping + Gaussian noise
  surrogate_recovery_s: recover_failed_update (coordinate-wise median surrogate construction)
  server_evaluation_s: Server.evaluate / Server.predict_probabilities (validation-partition scoring; not part of a deployed round)
  total_wall_s       : whole run_experiment call incl. data loading/preprocessing/partitioning and evaluation (from run_record.json)
Simulated network delay is a model output (network_metrics.csv) and is never mixed with these measured times."""
import json
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

T: dict[str, float] = {}
N: dict[str, int] = {}


def timed(fn, key):
    def wrapper(*a, **k):
        t0 = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            T[key] = T.get(key, 0.0) + time.perf_counter() - t0
            N[key] = N.get(key, 0) + 1
    return wrapper


import src.client as C  # noqa: E402
import src.experiment as E  # noqa: E402
import src.server as S  # noqa: E402

E.aggregate_updates = timed(E.aggregate_updates, "server_aggregation_s")
E.capped_normalized_weights = timed(E.capped_normalized_weights, "server_aggregation_s")
E.group_capped_normalized_weights = timed(E.group_capped_normalized_weights, "server_aggregation_s")
E.clip_update = timed(E.clip_update, "server_aggregation_s")
E.add_gaussian_noise = timed(E.add_gaussian_noise, "server_aggregation_s")
E.recover_failed_update = timed(E.recover_failed_update, "surrogate_recovery_s")
C.Client.train_local = timed(C.Client.train_local, "local_training_s")
S.Server.evaluate = timed(S.Server.evaluate, "server_evaluation_s")
S.Server.predict_probabilities = timed(S.Server.predict_probabilities, "server_evaluation_s")

if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1])
    sys.argv = [str(ROOT / "scripts" / "phase6c" / "run_one.py")] + args
    t0 = time.perf_counter()
    runpy.run_path(sys.argv[0], run_name="__main__")
    wall = time.perf_counter() - t0
    import platform
    import torch
    rec = json.loads((out / "run_record.json").read_text(encoding="utf-8")) if (out / "run_record.json").exists() else {}
    (out / "timing_breakdown.json").write_text(json.dumps({
        "seconds": {k: round(v, 3) for k, v in T.items()}, "calls": N, "process_wall_s": round(wall, 3), "run_record_wall_s": rec.get("wall_seconds"),
        "peak_working_set_mb": rec.get("peak_working_set_mb"), "cpu_seconds": rec.get("cpu_seconds"),
        "hardware": {"cpu": "Intel Core i5-14400F (10 cores / 16 threads)", "torch_intra_op_threads": torch.get_num_threads(), "device": "cpu",
                     "python": platform.python_version(), "torch": torch.__version__, "os": platform.platform()},
        "note": "timers are passive wrappers; local training is serial; network delay is simulated and reported separately in network_metrics.csv"}, indent=1), encoding="utf-8")
