"""Resumable, duplicate-safe orchestrator for the Table 4 v2 study.
Commands: preflight | run [--resume] [--only-run-ids a,b] | status | validate
Guarantees: global runner lock + per-run lock (no duplicate concurrent execution of a run id); an unfinished directory is never reused
(it is moved aside as *.incomplete.<utc>); a run is COMPLETE only if its hashed artifacts and training semantics verify (test_data_loaded=false,
30 rounds, metric-accounting invariants); state/logs live under results_table4_controlled_v2/ only (no locked directory is touched)."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t4_common import (MANIFEST, OUT_ROOT, ROOT, atomic_write_json, fingerprint, load_manifest, log, manifest_hash, now_utc, pid_alive,  # noqa: E402
                       sha256_file, sha256_text_file, verify_run_dir)


def state_dir(root: Path) -> Path:
    return root / OUT_ROOT / "_state"


def log_dir(root: Path) -> Path:
    return root / OUT_ROOT / "_logs"


def event(root: Path, kind: str, **fields) -> None:
    sd = state_dir(root)
    sd.mkdir(parents=True, exist_ok=True)
    with open(sd / "events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": now_utc(), "event": kind, **fields}) + "\n")


def _try_lock(root: Path, path: Path, payload: dict) -> bool:
    """Atomic exclusive create. A lock whose owner process is dead is stale and is removed (and logged)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                info = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                info = {}
            if pid_alive(int(info.get("pid", -1))) and int(info.get("pid", -1)) != os.getpid():
                return False
            event(root, "stale_lock_removed", lock=path.name, previous=info)
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return True
    return False


def acquire_runner_lock(root: Path) -> bool:
    return _try_lock(root, state_dir(root) / "runner.lock", {"pid": os.getpid(), "t": now_utc()})


def release_runner_lock(root: Path) -> None:
    (state_dir(root) / "runner.lock").unlink(missing_ok=True)


def acquire_run_lock(root: Path, run_id: str) -> bool:
    return _try_lock(root, state_dir(root) / "locks" / f"{run_id}.lock", {"pid": os.getpid(), "run_id": run_id, "t": now_utc()})


def release_run_lock(root: Path, run_id: str) -> None:
    (state_dir(root) / "locks" / f"{run_id}.lock").unlink(missing_ok=True)


def run_status(run: dict, manifest: dict, root: Path):
    out = root / run["out_dir"]
    if (out / "COMPLETE.json").exists():
        problems = verify_run_dir(out, run, manifest)
        return ("verified", []) if not problems else ("corrupt", problems)
    if (out / "FAILED.json").exists():
        return "failed", []
    if out.exists() and any(out.iterdir()):
        return "incomplete", []
    return "pending", []


def preflight(manifest: dict, root: Path, hash_data: bool = True):
    import yaml
    res = []

    def add(name, ok, detail=""):
        res.append((name, bool(ok), detail))
    add("manifest hash valid", manifest.get("manifest_sha256") == manifest_hash(manifest), manifest.get("manifest_sha256", "")[:16])
    fp = fingerprint(root)
    add("code fingerprint equals the manifest", fp == manifest["code_fingerprint"], f"{fp[:16]} vs {manifest['code_fingerprint'][:16]}")
    bad, unsafe = [], []
    for r in manifest["runs"]:
        p = root / r["config"]
        if not p.exists() or sha256_text_file(p) != r["config_sha256"]:
            bad.append(r["config"])
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        if (not raw["experiment"].get("validation_only") or raw["data"].get("test_csv") != "" or int(raw["fl"]["rounds"]) != int(manifest["rounds"])
                or raw["experiment"].get("output_dir") != OUT_ROOT):
            unsafe.append(r["config"])
    add(f"{len(manifest['runs'])} config hashes match", not bad, str(bad[:3]))
    add("every config is validation-only, blank test path, 30 rounds, versioned output dir", not unsafe, str(unsafe[:3]))
    add("manifest references no test file", not manifest.get("locked_test"), "locked_test is empty")
    if hash_data:
        from t4_common import sha256_gzip_content
        d = manifest["datasets"]
        add("UNSW training CSV sha256", sha256_file(root / d["unsw"]["training_csv"]) == d["unsw"]["training_sha256"])
        for split, digest in d["ciciot"]["content_sha256"].items():
            add(f"CICIoT2023 {split} content sha256", sha256_gzip_content(root / d["ciciot"]["prepared_dir"] / f"{split}.csv.gz") == digest)
    try:
        import numpy, pandas, sklearn, torch  # noqa: F401
        add("environment imports", True, f"torch {torch.__version__}")
    except Exception as exc:  # noqa: BLE001
        add("environment imports", False, repr(exc))
    free = __import__("shutil").disk_usage(root).free / 1e9
    add("free disk >= 5 GB", free >= 5, f"{free:.0f} GB")
    lock = state_dir(root) / "runner.lock"
    active = False
    if lock.exists():
        try:
            active = pid_alive(int(json.loads(lock.read_text()).get("pid", -1)))
        except Exception:  # noqa: BLE001
            active = False
    add("no other runner is active", not active)
    return res


def finalize_run(out: Path, run: dict, manifest: dict, duration: float):
    hashes = {n: sha256_file(out / n) for n in manifest["required_artifacts"] if (out / n).exists()}
    atomic_write_json(out / "COMPLETE.json", {"run_id": run["run_id"], "config_sha256": run["config_sha256"], "manifest_sha256": manifest["manifest_sha256"],
                                               "code_fingerprint": manifest["code_fingerprint"], "git_commit_at_build": manifest["git_commit_at_build"],
                                               "completed_utc": now_utc(), "duration_seconds": round(duration, 1), "artifact_sha256": hashes})
    problems = verify_run_dir(out, run, manifest)
    if problems:
        (out / "COMPLETE.json").unlink()
        atomic_write_json(out / "FAILED.json", {"reason": "post-run verification failed", "problems": problems, "t": now_utc()})
    return problems


def cmd_run(manifest, root, resume, only, max_fail, hash_data):
    res = preflight(manifest, root, hash_data)
    for n, ok, d in res:
        print(("PASS " if ok else "FAIL ") + n + (f" [{d}]" if d else ""))
    if not all(ok for _, ok, _ in res):
        return 2
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    if only:
        unknown = set(only) - {r["run_id"] for r in runs}
        if unknown:
            print("unknown run ids", sorted(unknown)[:5])
            return 2
        runs = [r for r in runs if r["run_id"] in set(only)]
    leftovers = [r for r in runs if run_status(r, manifest, root)[0] in ("failed", "incomplete")]
    if leftovers and not resume:
        print(f"{len(leftovers)} incomplete/failed run directories exist; use --resume to preserve them and re-run those runs")
        return 2
    if not acquire_runner_lock(root):
        print("another runner is active (runner.lock); refusing to start a second one")
        return 3
    log_dir(root).mkdir(parents=True, exist_ok=True)
    consecutive = 0
    try:
        event(root, "runner_started", pid=os.getpid(), resume=resume)
        for run in runs:
            st, probs = run_status(run, manifest, root)
            if st == "verified":
                continue
            if st == "corrupt":
                print(f"CRITICAL corrupt completed run {run['run_id']}: {probs}")
                return 2
            if not acquire_run_lock(root, run["run_id"]):
                print(f"run {run['run_id']} is locked by another live process; skipping (no duplicate execution)")
                event(root, "skip_locked", run=run["run_id"])
                continue
            try:
                out = root / run["out_dir"]
                if st in ("failed", "incomplete"):
                    moved = out.with_name(out.name + f".{st}.{time.strftime('%Y%m%d-%H%M%S')}")
                    out.rename(moved)
                    event(root, "preserved_previous_attempt", run=run["run_id"], to=moved.name)
                out.mkdir(parents=True, exist_ok=False)
                cmd = [p.format(python=sys.executable, config=run["config"], seed=run["seed"], out_dir=run["out_dir"]) for p in manifest["command"]]
                lp = log_dir(root) / f"{run['run_id']}.log"
                if lp.exists():
                    lp.rename(lp.with_suffix(f".{time.strftime('%Y%m%d-%H%M%S')}.log"))
                log(f"START #{run['order']}/{len(runs)} {run['run_id']}")
                event(root, "run_started", run=run["run_id"])
                t0 = time.time()
                with open(lp, "wb") as fh:
                    rc = subprocess.Popen(cmd, cwd=root, stdout=fh, stderr=subprocess.STDOUT,
                                          env=dict(os.environ, PYTHONHASHSEED="0", PYTHONUNBUFFERED="1")).wait()
                dur = time.time() - t0
                if rc == 0:
                    problems = finalize_run(out, run, manifest, dur)
                    rc = 3 if problems else 0
                    if problems:
                        log(f"FAILED verification {run['run_id']}: {problems}")
                else:
                    atomic_write_json(out / "FAILED.json", {"exit_code": rc, "log": str(lp), "t": now_utc()})
                if rc == 0:
                    consecutive = 0
                    log(f"DONE  {run['run_id']} in {dur:.0f}s (verified)")
                    event(root, "run_completed", run=run["run_id"], seconds=round(dur, 1))
                else:
                    consecutive += 1
                    log(f"FAILED {run['run_id']} exit={rc}")
                    event(root, "run_failed", run=run["run_id"], exit_code=rc)
                    if consecutive >= max_fail:
                        print("STOPPING SAFELY after consecutive failures")
                        return 4
            finally:
                release_run_lock(root, run["run_id"])
        remaining = [r for r in runs if run_status(r, manifest, root)[0] != "verified"]
        print("ALL REQUESTED RUNS COMPLETE AND VERIFIED" if not remaining else f"{len(remaining)} requested runs remain")
        return 0 if not remaining else 1
    finally:
        release_runner_lock(root)
        event(root, "runner_stopped", pid=os.getpid())


def cmd_status(manifest, root):
    counts = {}
    for r in manifest["runs"]:
        s = run_status(r, manifest, root)[0]
        counts[s] = counts.get(s, 0) + 1
    print(counts, "of", len(manifest["runs"]))
    return 0 if counts.get("verified", 0) == len(manifest["runs"]) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["preflight", "run", "status", "validate"])
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--only-run-ids", default=None)
    ap.add_argument("--max-consecutive-failures", type=int, default=3)
    ap.add_argument("--skip-data-hash", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    manifest = load_manifest(Path(a.manifest))
    if a.command == "preflight":
        res = preflight(manifest, root, not a.skip_data_hash)
        for n, ok, d in res:
            print(("PASS " if ok else "FAIL ") + n + (f" [{d}]" if d else ""))
        return 0 if all(ok for _, ok, _ in res) else 2
    if a.command in ("status", "validate"):
        return cmd_status(manifest, root)
    only = [x for x in a.only_run_ids.split(",") if x] if a.only_run_ids else None
    return cmd_run(manifest, root, a.resume, only, a.max_consecutive_failures, not a.skip_data_hash)


if __name__ == "__main__":
    sys.exit(main())
