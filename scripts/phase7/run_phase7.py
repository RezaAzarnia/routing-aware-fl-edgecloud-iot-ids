"""Resumable sequential runner for the Phase 7 matrix. DRY RUN unless --execute is given.

usage:
  python scripts/phase7/run_phase7.py plan                         # queue + time estimate, nothing starts
  python scripts/phase7/run_phase7.py status                       # verified / pending counts
  python scripts/phase7/run_phase7.py run --execute [--resume] [--include-optional] [--only-run-ids a,b] [--stop-after-minutes N]
Runs are sequential, one immutable directory each (results_phase7/...), verified before they count as complete.
Existing incomplete directories are moved to results_phase7/_attempts/, never deleted. Phase 6C results are never touched.
Live per-round progress: set IOTFL_LIVE=1 and PYTHONPATH=scripts/live (done automatically by this runner).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import (atomic_write_json, code_fingerprint, load_manifest, now_utc, pid_alive, sha256_file,  # noqa: E402
                        sha256_text_file, verify_run_dir)

MANIFEST = ROOT / "docs" / "phase7" / "EXPERIMENT_MANIFEST.json"
RES = ROOT / "results_phase7"
STATE = RES / "_state"
FALLBACK_SECONDS = {"unsw": 90.0, "ciciot": 215.0}      # measured Phase 6C means (reference-type runs)


def status_of(run, manifest):
    out = ROOT / run["out_dir"]
    if (out / "COMPLETE.json").exists():
        return "corrupt" if verify_run_dir(out, run, manifest) else "verified"
    if (out / "FAILED.json").exists():
        return "failed"
    return "incomplete" if out.exists() else "pending"


def estimates():
    """Mean seconds per (dataset, base arm) from the verified Phase 6C COMPLETE records."""
    p6c = json.loads((ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
    acc = {}
    for r in p6c["runs"]:
        c = ROOT / r["out_dir"] / "COMPLETE.json"
        if c.exists():
            acc.setdefault((r["dataset"], r["arm"]), []).append(float(json.loads(c.read_text())["duration_seconds"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


BASE = {"p7_corrected_guard": "corrected", "fail0p3_p7_corrected_guard": "fail0p3_corrected", "p7_delivery_guard": "ctl_delivery_coupled"}


def est(run, table):
    return table.get((run["dataset"], BASE.get(run["arm"], run["arm"])), FALLBACK_SECONDS[run["dataset"]])


def preflight(manifest):
    problems = []
    fp = code_fingerprint(ROOT, manifest["code_fingerprint_globs"])
    if fp != manifest["code_fingerprint"]:
        problems.append(f"code fingerprint differs from the Phase 7 manifest ({fp[:12]} vs {manifest['code_fingerprint'][:12]}): rebuild deliberately")
    for run in manifest["runs"]:
        p = ROOT / run["config"]
        if not p.exists() or sha256_text_file(p) != run["config_sha256"]:
            problems.append(f"config hash mismatch: {run['config']}")
            break
    import yaml
    for run in manifest["runs"][:: max(1, len(manifest["runs"]) // 20)]:
        raw = yaml.safe_load((ROOT / run["config"]).read_text(encoding="utf-8"))
        if not raw["experiment"].get("validation_only") or raw["data"].get("test_csv") != "":
            problems.append(f"{run['config']} is not validation-only / has a test path")
    ds = manifest["datasets"]
    if sha256_file(ROOT / ds["unsw"]["training_csv"]) != ds["unsw"]["training_sha256"]:
        problems.append("UNSW training CSV hash differs")
    lock = STATE / "runner.lock"
    if lock.exists():
        info = json.loads(lock.read_text())
        if pid_alive(int(info.get("pid", -1))) and int(info["pid"]) != os.getpid():
            problems.append(f"another Phase 7 runner is active: {info}")
    if (ROOT / "results_phase6c" / "_state" / "runner.lock").exists():
        info = json.loads((ROOT / "results_phase6c" / "_state" / "runner.lock").read_text())
        if pid_alive(int(info.get("pid", -1))):
            problems.append("the Phase 6C runner is still active")
    return problems


def select(manifest, args):
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    if not args.include_optional:
        runs = [r for r in runs if r["tier"] == "mandatory"]
    if args.only_run_ids:
        keep = set(args.only_run_ids.split(","))
        runs = [r for r in runs if r["run_id"] in keep]
    return runs


def cmd_plan(manifest, args):
    table, runs = estimates(), select(manifest, args)
    todo = [r for r in runs if status_of(r, manifest) != "verified"]
    total = sum(est(r, table) for r in todo)
    print(f"Phase 7 manifest {manifest['manifest_sha256'][:16]}...  selected {len(runs)} runs, {len(todo)} still to run")
    for ds in ("unsw", "ciciot"):
        sub = [r for r in todo if r["dataset"] == ds]
        if sub:
            print(f"  {ds}: {len(sub)} runs, ~{sum(est(r, table) for r in sub) / 3600:.2f} h")
    print(f"  total estimated {total / 3600:.2f} h (CPU, sequential; from verified Phase 6C durations)")
    for r in todo[:8]:
        print(f"    #{r['order']:3d} {r['run_id']}")
    if len(todo) > 8:
        print(f"    ... {len(todo) - 8} more")
    return 0


def cmd_status(manifest, args):
    counts = {}
    for r in manifest["runs"]:
        counts[status_of(r, manifest)] = counts.get(status_of(r, manifest), 0) + 1
    print(counts, "of", len(manifest["runs"]))
    return 0


def cmd_run(manifest, args):
    problems = preflight(manifest)
    for p in problems:
        print("PREFLIGHT FAIL:", p)
    if problems:
        return 2
    runs, table = select(manifest, args), estimates()
    todo = [r for r in runs if status_of(r, manifest) in ("pending", "incomplete", "failed")] if args.resume or True else []
    if any(status_of(r, manifest) == "corrupt" for r in runs):
        print("CRITICAL: a completed run fails verification; refusing to continue.")
        return 3
    cmd_plan(manifest, args)
    if not args.execute:
        print("\nDRY RUN: nothing started. Add --execute to train.")
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    atomic_write_json(STATE / "runner.lock", {"pid": os.getpid(), "started": now_utc()})
    deadline = time.time() + args.stop_after_minutes * 60 if args.stop_after_minutes else None
    failures = 0
    env = dict(os.environ, PYTHONHASHSEED="0", IOTFL_LIVE="1", PYTHONUNBUFFERED="1",
               PYTHONPATH=str(ROOT / "scripts" / "live") + os.pathsep + os.environ.get("PYTHONPATH", ""))
    try:
        for run in todo:
            if deadline and time.time() + est(run, table) > deadline:
                print("time budget reached: not starting", run["run_id"])
                break
            out = ROOT / run["out_dir"]
            if out.exists():
                dest = RES / "_attempts" / f"{run['run_id']}_{time.strftime('%Y%m%d-%H%M%S')}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(out), str(dest))
            atomic_write_json(STATE / "active.json", {"run_id": run["run_id"], "order": run["order"], "started": now_utc(), "pid": os.getpid()})
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, str(ROOT / "scripts" / "phase6c" / "run_one.py"), "--config", str(ROOT / run["config"]),
                   "--seed", str(run["seed"]), "--out", str(out)]
            print(f"[{time.strftime('%H:%M:%S')}] START {run['run_id']}", flush=True)
            t0 = time.perf_counter()
            log = (RES / "_logs"); log.mkdir(parents=True, exist_ok=True)
            with open(log / f"{run['run_id']}.log", "w", encoding="utf-8") as fh:
                code = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=str(ROOT)).returncode
            dur = time.perf_counter() - t0
            probs = []
            if code == 0:
                hashes = {n: sha256_file(out / n) for n in manifest["required_artifacts"] if (out / n).exists()}
                atomic_write_json(out / "COMPLETE.json", {"run_id": run["run_id"], "config_sha256": run["config_sha256"],
                                  "manifest_sha256": manifest["manifest_sha256"], "code_fingerprint": manifest["code_fingerprint"],
                                  "completed_utc": now_utc(), "duration_seconds": round(dur, 1), "artifact_sha256": hashes})
                probs = verify_run_dir(out, run, manifest)
                if probs:
                    (out / "COMPLETE.json").unlink()
            if code != 0 or probs:
                atomic_write_json(out / "FAILED.json", {"exit_code": code, "problems": probs, "t": now_utc()})
                failures += 1
                print(f"[{time.strftime('%H:%M:%S')}] FAILED {run['run_id']} exit={code} {probs}", flush=True)
                if failures >= 3:
                    print("3 consecutive failures: stopping.")
                    return 4
            else:
                failures = 0
                print(f"[{time.strftime('%H:%M:%S')}] DONE  {run['run_id']} {dur:.0f}s", flush=True)
    finally:
        (STATE / "runner.lock").unlink(missing_ok=True)
        (STATE / "active.json").unlink(missing_ok=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["plan", "status", "run"])
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--resume", action="store_true", help="accepted for clarity: runs are always resumable (verified runs are skipped)")
    ap.add_argument("--include-optional", action="store_true", help="also run the optional CICIoT2023 tier")
    ap.add_argument("--only-run-ids", default=None)
    ap.add_argument("--stop-after-minutes", type=float, default=None)
    ap.add_argument("--manifest", default=None, help="manifest to use (default: Phase 7); Phase 7b: docs/phase7b/EXPERIMENT_MANIFEST.json")
    ap.add_argument("--results", default=None, help="results folder (default: results_phase7); Phase 7b: results_phase7b")
    args = ap.parse_args()
    global MANIFEST, RES, STATE
    if args.manifest:
        MANIFEST = (ROOT / args.manifest) if not Path(args.manifest).is_absolute() else Path(args.manifest)
    if args.results:
        RES = ROOT / args.results
        STATE = RES / "_state"
    manifest = load_manifest(MANIFEST)
    return {"plan": cmd_plan, "status": cmd_status, "run": cmd_run}[args.command](manifest, args)


if __name__ == "__main__":
    sys.exit(main())
