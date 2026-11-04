"""Verify a handoff folder independently of the original project (no experiment folders, no training).

usage: python verify_handoff.py --handoff <dir> [--regenerate]
Checks: checksums.sha256, 240 runs / 2x120 / 5 seeds / 24 arms, all runs verified, no test data, hash match,
and (with --regenerate) re-runs statistical_analysis.py and generate_figures.py into a temp copy and compares the tables.
"""
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
import pandas as pd

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

ap = argparse.ArgumentParser(); ap.add_argument("--handoff", default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--regenerate", action="store_true")
a = ap.parse_args(); H = Path(a.handoff); bad = []
for line in (H / "provenance" / "checksums.sha256").read_text().splitlines():
    digest, rel = line.split("  ", 1)
    if not (H / rel).exists() or sha(H / rel) != digest: bad.append("checksum:" + rel)
runs = pd.read_csv(H / "tables" / "all_runs.csv"); inv = pd.read_csv(H / "provenance" / "run_inventory.csv")
checks = {"240 runs": len(runs) == 240, "120 per dataset": runs.groupby("dataset").size().eq(120).all(), "24 arms": runs.arm.nunique() == 24,
          "seeds 12-16": sorted(runs.seed.unique()) == [12, 13, 14, 15, 16], "each arm x dataset has 5 seeds": runs.groupby(["dataset", "arm"]).size().eq(5).all(),
          "all verified": bool(inv.verified.all()) and len(inv) == 240, "config hashes match": bool(inv.config_hash_match.all()),
          "no test data loaded": not runs.test_data_loaded.any(), "validation_only": set(runs.protocol) == {"validation_only"}}
for k, v in checks.items():
    print(("PASS " if v else "FAIL ") + k)
    if not v: bad.append(k)
if a.regenerate:
    t = Path(tempfile.mkdtemp()); shutil.copytree(H, t / "h", ignore=shutil.ignore_patterns("figures"))
    for s in ("statistical_analysis.py", "generate_figures.py"):
        r = subprocess.run([sys.executable, str(t / "h" / "scripts" / s), "--handoff", str(t / "h")], capture_output=True, text=True)
        if r.returncode: bad.append(s + ": " + r.stderr[-300:])
    for n in ("aggregate_metrics.csv", "paired_comparisons.csv", "ablation_results.csv"):
        x, y = pd.read_csv(H / "tables" / n), pd.read_csv(t / "h" / "tables" / n)
        if not x.equals(y): bad.append("regenerated differs: " + n)
    if len(list((t / "h" / "figures" / "PNG").glob("*.png"))) != 12: bad.append("figures != 12")
    print("regeneration test in", t)
print("VERIFY OK" if not bad else "VERIFY FAILED: " + "; ".join(bad)); sys.exit(1 if bad else 0)
