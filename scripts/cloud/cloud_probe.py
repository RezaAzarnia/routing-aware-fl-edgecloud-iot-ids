"""Probe a candidate cloud VM (CPU, RAM, disk, Python stack) against the Phase-6C requirements. Read-only.

usage: python scripts/cloud/cloud_probe.py [--lock cloud_transfer/requirements-cloud-lock.txt] [--min-ram-gb 12] [--min-disk-gb 30]
"""
import argparse
import importlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--lock", default="requirements-cloud-lock.txt")
parser.add_argument("--min-ram-gb", type=float, default=12)
parser.add_argument("--min-disk-gb", type=float, default=30)
parser.add_argument("--min-cpus", type=int, default=4)
parser.add_argument("--path", default=".")
args = parser.parse_args()


def ram_gb() -> float:
    try:
        if platform.system() == "Linux":
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 2**20
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("tp", ctypes.c_ulonglong)] + [("x", ctypes.c_ulonglong)] * 6
        s = MS(); s.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return s.tp / 2**30
    except Exception:  # noqa: BLE001
        return float("nan")


report = {"platform": platform.platform(), "python": platform.python_version(), "machine": platform.machine(),
          "cpus": os.cpu_count(), "ram_gb": round(ram_gb(), 1), "free_disk_gb": round(shutil.disk_usage(args.path).free / 2**30, 1)}
checks = []


def add(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})


add(f"CPUs >= {args.min_cpus}", (os.cpu_count() or 0) >= args.min_cpus, str(os.cpu_count()))
add(f"RAM >= {args.min_ram_gb} GB", report["ram_gb"] >= args.min_ram_gb, str(report["ram_gb"]))
add(f"free disk >= {args.min_disk_gb} GB", report["free_disk_gb"] >= args.min_disk_gb, str(report["free_disk_gb"]))
add("x86-64 CPU (the local results were produced on x86-64)", report["machine"].lower() in ("x86_64", "amd64"), report["machine"])
add("Python 3.11", sys.version_info[:2] == (3, 11), report["python"])
lock = Path(args.lock)
names = {"PyYAML": "yaml", "scikit-learn": "sklearn"}
if lock.exists():
    for line in lock.read_text().splitlines():
        if "==" not in line or line.startswith("#"):
            continue
        pkg, want = line.split("==")
        mod = names.get(pkg, pkg.replace("-", "_").lower())
        try:
            have = getattr(importlib.import_module(mod), "__version__", "?")
            add(f"{pkg}=={want}", str(have).split("+")[0] == want, str(have))
        except Exception as exc:  # noqa: BLE001
            add(f"{pkg}=={want}", False, repr(exc))
try:
    import torch
    report["torch_threads_default"] = torch.get_num_threads()
    report["torch_cuda"] = torch.cuda.is_available()
    add("PyTorch is a CPU build or CUDA is not used (runs are device=cpu)", True, f"cuda={torch.cuda.is_available()}")
except Exception as exc:  # noqa: BLE001
    add("PyTorch importable", False, repr(exc))
for forbidden in ("data/UNSW_NB15_testing-set.csv", "data/CICIoT2023/prepared_verified_v2_filegroup/test.csv.gz"):
    add(f"locked test file absent: {Path(forbidden).name}", not (Path(args.path) / forbidden).exists())
report["checks"] = checks
report["all_pass"] = all(c["pass"] for c in checks)
print(json.dumps(report, indent=2))
sys.exit(0 if report["all_pass"] else 1)
