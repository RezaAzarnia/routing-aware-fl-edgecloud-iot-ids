"""Run one experiment config in-process and record wall time / CPU time / peak memory."""
import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import Config  # noqa: E402
from src.experiment import run_experiment  # noqa: E402


def peak_working_set_mb() -> float:
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = PMC()
    counters.cb = ctypes.sizeof(PMC)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return float("nan")
    return counters.PeakWorkingSetSize / 2**20


def main(config_path: str, seed: int) -> None:
    cfg = Config.from_yaml(config_path)
    cfg.experiment.seed = seed
    start, cpu = time.perf_counter(), time.process_time()
    run_dir = run_experiment(cfg)
    usage = {"config": config_path, "seed": seed, "wall_seconds": round(time.perf_counter() - start, 2),
             "cpu_seconds": round(time.process_time() - cpu, 2),
             "peak_working_set_mb": round(peak_working_set_mb(), 1), "device": cfg.experiment.device}
    (Path(run_dir) / "resource_usage.json").write_text(json.dumps(usage, indent=2), encoding="utf-8")
    print(json.dumps(usage))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
