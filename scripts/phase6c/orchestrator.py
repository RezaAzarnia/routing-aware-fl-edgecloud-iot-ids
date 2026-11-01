"""Phase-6C experiment orchestrator (runs on the USER's machine; never started by the agent).

Subcommands: preflight | plan | run | status | validate | aggregate
All results live in immutable per-(dataset, arm, seed) directories; a run is only trusted once its
COMPLETE.json (artifact hashes + manifest hash + code fingerprint) verifies. Verified results are never
overwritten. Final-test data is never touched here (see final_test_evaluate.py, a separate operation).
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p6c_common import (  # noqa: E402
    ROOT, atomic_write_json, code_fingerprint, load_manifest, log, manifest_hash, now_utc, pid_alive,
    sha256_file, sha256_gzip_content, sha256_text_file, verify_run_dir,
)

PRIOR_SECONDS = {"unsw": 80.0, "ciciot": 220.0}
PRIOR_FACTOR = {"clean_centralized": 3.0}


# ----------------------------------------------------------------------------- state helpers
def state_dir(root: Path) -> Path:
    return root / "results_phase6c" / "_state"


def run_status(run: dict, manifest: dict, root: Path) -> tuple[str, list[str]]:
    out = root / run["out_dir"]
    if (out / "COMPLETE.json").exists():
        problems = verify_run_dir(out, run, manifest)
        return ("verified", []) if not problems else ("corrupt", problems)
    if (out / "FAILED.json").exists():
        return "failed", []
    if out.exists() and any(out.iterdir()):
        return "incomplete", []
    return "pending", []


def event(root: Path, kind: str, **fields) -> None:
    sd = state_dir(root)
    sd.mkdir(parents=True, exist_ok=True)
    with open(sd / "events.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"t": now_utc(), "event": kind, **fields}) + "\n")


def read_lock(root: Path):
    path = state_dir(root) / "runner.lock"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"pid": -1, "corrupt": True}


def acquire_lock(root: Path) -> None:
    sd = state_dir(root)
    sd.mkdir(parents=True, exist_ok=True)
    path = sd / "runner.lock"
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            info = read_lock(root) or {}
            if pid_alive(int(info.get("pid", -1))) and int(info.get("pid", -1)) != os.getpid():
                raise SystemExit(f"CRITICAL: another runner is active (PID {info.get('pid')}). Never run two at once.")
            event(root, "stale_lock_removed", previous=info)
            path.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started": now_utc()}, handle)
        return
    raise SystemExit("CRITICAL: could not acquire the runner lock")


def release_lock(root: Path) -> None:
    (state_dir(root) / "runner.lock").unlink(missing_ok=True)
    (state_dir(root) / "active.json").unlink(missing_ok=True)


# ----------------------------------------------------------------------------- preflight
def preflight(manifest: dict, root: Path, hash_data: bool, min_free_gb: float, cloud_mode: bool = False) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def add(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    add("manifest hash valid (not modified since locking)", manifest.get("manifest_sha256") == manifest_hash(manifest), manifest.get("manifest_sha256", "")[:16])
    fp = code_fingerprint(root)
    add("code fingerprint equals the manifest", fp == manifest.get("code_fingerprint"), f"{fp[:16]} vs {str(manifest.get('code_fingerprint'))[:16]}")
    configs = {r["config"]: r["config_sha256"] for r in manifest["runs"]}
    bad = [c for c, h in configs.items() if not (root / c).exists() or sha256_text_file(root / c) != h]
    add(f"{len(configs)} configuration hashes match", not bad, f"mismatched: {bad[:3]}")
    unsafe = []
    try:
        import yaml
        for c in configs:
            raw = yaml.safe_load((root / c).read_text(encoding="utf-8"))
            if not raw["experiment"].get("validation_only") or raw["data"].get("test_csv") != "" or int(raw["fl"]["rounds"]) != int(manifest["rounds"]):
                unsafe.append(c)
    except Exception as exc:  # noqa: BLE001
        unsafe.append(repr(exc))
    add("every training config is validation-only with a blank test path", not unsafe, str(unsafe[:3]))
    try:
        import numpy, pandas, sklearn, torch, yaml  # noqa: F401,E401
        add("python environment imports (torch/numpy/pandas/sklearn/yaml)", True, f"torch {torch.__version__}, numpy {numpy.__version__}, pandas {pandas.__version__}")
    except Exception as exc:  # noqa: BLE001
        add("python environment imports", False, repr(exc))
    # datasets
    ds = manifest["datasets"]
    unsw = root / ds["unsw"]["training_csv"]
    if hash_data:
        add("UNSW training CSV sha256", unsw.exists() and sha256_file(unsw) == ds["unsw"]["training_sha256"], unsw.name)
        for split, digest in ds["ciciot"]["content_sha256"].items():
            path = root / ds["ciciot"]["prepared_dir"] / f"{split}.csv.gz"
            add(f"CICIoT2023 {split} content sha256", path.exists() and sha256_gzip_content(path) == digest, path.name)
        meta = root / ds["ciciot"]["prepared_dir"] / "preparation_metadata.json"
        add("CICIoT2023 preparation metadata sha256", meta.exists() and sha256_file(meta) == ds["ciciot"]["metadata_sha256"])
    else:
        add("dataset hashes (skipped by request)", True, "skipped")
    # locked test files: existence + size only (they are NOT read before the authorised final-test step)
    for name, info in manifest["locked_test"].items():
        path = root / info["path"]
        if cloud_mode:
            # cloud mode: the locked test data must NOT exist on this machine (cannot leak into training)
            add(f"cloud mode: locked test file ABSENT on this machine ({name})", not path.exists(), info["path"])
            continue
        ok = path.exists() and (info.get("bytes") is None or path.stat().st_size == info["bytes"])
        add(f"locked test file present ({name}); size check only, content not read", ok, info["path"])
    free = shutil.disk_usage(root).free / 2**30
    add(f"free disk >= {min_free_gb:.0f} GB", free >= min_free_gb, f"{free:.1f} GB")
    lock = read_lock(root)
    active = bool(lock) and pid_alive(int(lock.get("pid", -1))) and int(lock.get("pid", -1)) != os.getpid()
    add("no other runner is active", not active, str(lock) if lock else "no lock")
    counts = {"verified": 0, "pending": 0, "failed": 0, "incomplete": 0, "corrupt": 0}
    for run in manifest["runs"]:
        counts[run_status(run, manifest, root)[0]] += 1
    add("no corrupted completed runs", counts["corrupt"] == 0, str(counts))
    ft = root / "results_phase6c" / "_final_test"
    add("no final-test results exist yet (training stage)", not ft.exists() or not any(ft.iterdir()), str(ft))
    return results


def print_preflight(results) -> bool:
    ok_all = True
    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail and not ok else (f"  ({detail})" if detail else "")))
        ok_all &= ok
    print("PREFLIGHT: " + ("ALL CHECKS PASSED" if ok_all else "FAILED - do not start the experiments"))
    return ok_all


# ----------------------------------------------------------------------------- planning
def estimate_seconds(run: dict, manifest: dict, root: Path, measured: dict) -> float:
    key = (run["dataset"], run["arm"])
    if key in measured:
        return measured[key]
    base = PRIOR_SECONDS[run["dataset"]]
    return base * PRIOR_FACTOR.get(run["arm"], 1.0)


def measured_durations(manifest: dict, root: Path) -> dict:
    per_arm: dict = {}
    per_dataset: dict = {}
    for run in manifest["runs"]:
        c = root / run["out_dir"] / "COMPLETE.json"
        if c.exists():
            try:
                d = float(json.loads(c.read_text(encoding="utf-8")).get("duration_seconds", 0))
            except Exception:  # noqa: BLE001
                continue
            per_arm.setdefault((run["dataset"], run["arm"]), []).append(d)
            per_dataset.setdefault(run["dataset"], []).append(d)
    out = {k: sum(v) / len(v) for k, v in per_arm.items()}
    return out


def cmd_plan(manifest: dict, root: Path) -> None:
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    counts = {"verified": 0, "pending": 0, "failed": 0, "incomplete": 0, "corrupt": 0}
    todo = []
    for run in runs:
        st, _ = run_status(run, manifest, root)
        counts[st] += 1
        if st != "verified":
            todo.append(run)
    measured = measured_durations(manifest, root)
    eta = sum(estimate_seconds(r, manifest, root, measured) for r in todo)
    print(f"Experiment manifest: {manifest['manifest_sha256'][:16]}...  seeds {manifest['seeds']}  rounds {manifest['rounds']}")
    print(f"Total runs: {len(runs)}  ({len(manifest['arms'])} arms x {len(manifest['seeds'])} seeds x {len(manifest['datasets'])} datasets)")
    print(f"Status: {counts}")
    print("Queue (sequential, one run at a time):")
    for dataset in manifest["datasets"]:
        n = sum(1 for r in todo if r["dataset"] == dataset)
        print(f"  {dataset}: {n} runs to execute")
    for r in todo[:6]:
        print(f"    #{r['order']:3d} {r['run_id']}")
    if len(todo) > 6:
        print(f"    ... {len(todo) - 6} more, last: {todo[-1]['run_id']}")
    print(f"Rough ETA (CPU, from Phase-6B timings; refined as runs complete): {eta / 3600:.1f} hours")


# ----------------------------------------------------------------------------- run
def format_command(manifest: dict, run: dict, root: Path) -> list[str]:
    values = {"python": sys.executable, "config": run["config"], "seed": str(run["seed"]),
              "out_dir": run["out_dir"], "dataset": run["dataset"], "arm": run["arm"]}
    return [part.format(**values) for part in manifest["command"]]


def finalize_run(out: Path, run: dict, manifest: dict, duration: float) -> list[str]:
    hashes = {}
    for name in manifest["required_artifacts"]:
        path = out / name
        if path.exists():
            hashes[name] = sha256_file(path)
    atomic_write_json(out / "COMPLETE.json", {
        "run_id": run["run_id"], "config_sha256": run["config_sha256"], "manifest_sha256": manifest["manifest_sha256"],
        "code_fingerprint": manifest["code_fingerprint"], "completed_utc": now_utc(),
        "duration_seconds": round(duration, 1), "artifact_sha256": hashes,
    })
    problems = verify_run_dir(out, run, manifest)
    if problems:
        (out / "COMPLETE.json").unlink()
        atomic_write_json(out / "FAILED.json", {"reason": "post-run verification failed", "problems": problems, "t": now_utc()})
    return problems


def parse_run_ids(value):
    """None -> all runs; otherwise a set from a comma list or a file with one id per line."""
    if not value:
        return None
    path = Path(value)
    if path.exists():
        items = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    else:
        items = [x.strip() for x in str(value).split(",")]
    return {i for i in items if i}


def load_estimates(path):
    if not path:
        return {}
    try:
        return {k: float(v) for k, v in json.loads(Path(path).read_text(encoding="utf-8")).items() if not k.startswith("_")}
    except Exception:  # noqa: BLE001
        return {}


def cmd_run(manifest: dict, root: Path, resume: bool, max_consecutive_failures: int, args) -> int:
    marker = state_dir(root) / "MIGRATED_TO_CLOUD.json"
    if marker.exists() and not getattr(args, "cloud_mode", False):
        print(f"REFUSED: this experiment was migrated to a cloud machine ({marker}). Running it here too would duplicate the work "
              "and mix platforms. Delete the marker only if you deliberately cancel the migration.")
        return 2
    results = preflight(manifest, root, hash_data=not args.skip_data_hash, min_free_gb=args.min_free_gb,
                        cloud_mode=getattr(args, "cloud_mode", False))
    if not print_preflight(results):
        return 2
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    subset = parse_run_ids(getattr(args, "only_run_ids", None))
    if subset is not None:
        unknown = sorted(subset - {r["run_id"] for r in runs})
        if unknown:
            print(f"CRITICAL: unknown run ids requested: {unknown[:5]}")
            return 2
        runs = [r for r in runs if r["run_id"] in subset]
    budget_min = getattr(args, "stop_after_minutes", None)
    estimates = load_estimates(getattr(args, "duration_estimates", None))
    session_start = time.time()
    budget_hit = False
    # refuse to start if unresolved leftovers exist and -Resume was not given
    leftovers = [r for r in runs if run_status(r, manifest, root)[0] in ("failed", "incomplete")]
    if leftovers and not resume:
        print(f"CRITICAL: {len(leftovers)} incomplete/failed run directories exist. Use -Resume to preserve them and re-run only those.")
        return 2
    acquire_lock(root)
    logs = root / "results_phase6c" / "_logs"
    logs.mkdir(parents=True, exist_ok=True)
    consecutive = 0
    failures = 0
    done_now = 0
    try:
        event(root, "runner_started", pid=os.getpid(), resume=resume)
        for run in runs:
            st, probs = run_status(run, manifest, root)
            if st == "verified":
                continue
            if budget_min is not None and st != "corrupt":
                est_s = float(estimates.get(f"{run['dataset']}/{run['arm']}", 0.0))
                if (time.time() - session_start + est_s) / 60.0 > budget_min:
                    budget_hit = True
                    log(f"TIME BUDGET: not starting {run['run_id']} (estimated {est_s / 60:.0f} min; budget {budget_min:.0f} min)")
                    event(root, "budget_reached", next_run=run["run_id"])
                    break
            if st == "corrupt":
                print(f"CRITICAL: {run['run_id']} has a COMPLETE.json that no longer verifies: {probs}. Stopping; nothing was overwritten.")
                event(root, "critical_corrupt", run=run["run_id"], problems=probs)
                return 2
            out = root / run["out_dir"]
            if st in ("failed", "incomplete"):
                stamp = time.strftime("%Y%m%d-%H%M%S")
                preserved = out.with_name(out.name + f".{st}.{stamp}")
                out.rename(preserved)
                event(root, "preserved_previous_attempt", run=run["run_id"], to=str(preserved))
                log(f"preserved previous {st} attempt -> {preserved.name}")
            out.mkdir(parents=True, exist_ok=False)
            log_path = logs / f"{run['run_id']}.log"
            if log_path.exists():
                log_path.rename(log_path.with_suffix(f".{time.strftime('%Y%m%d-%H%M%S')}.log"))
            cmd = format_command(manifest, run, root)
            atomic_write_json(state_dir(root) / "active.json", {"run_id": run["run_id"], "order": run["order"], "started": now_utc(), "pid": os.getpid(), "cmd": cmd})
            log(f"START #{run['order']}/{len(runs)} {run['run_id']}")
            event(root, "run_started", run=run["run_id"])
            t0 = time.time()
            env = dict(os.environ, PYTHONHASHSEED="0", PYTHONUNBUFFERED="1")
            try:
                with open(log_path, "wb") as handle:
                    proc = subprocess.Popen(cmd, cwd=root, stdout=handle, stderr=subprocess.STDOUT, env=env)
                    try:
                        rc = proc.wait()
                    except KeyboardInterrupt:
                        proc.terminate()
                        try:
                            proc.wait(timeout=20)
                        except Exception:  # noqa: BLE001
                            proc.kill()
                        atomic_write_json(out / "INTERRUPTED.json", {"t": now_utc(), "run_id": run["run_id"]})
                        event(root, "interrupted", run=run["run_id"])
                        print("\nInterrupted. The unfinished run directory is kept and will be preserved on -Resume.")
                        return 130
            except OSError as exc:
                rc = 127
                atomic_write_json(out / "FAILED.json", {"reason": f"could not start: {exc!r}", "t": now_utc()})
            duration = time.time() - t0
            if rc == 0:
                problems = finalize_run(out, run, manifest, duration)
                if problems:
                    rc = 3
                    log(f"FAILED verification {run['run_id']}: {problems}")
            else:
                atomic_write_json(out / "FAILED.json", {"exit_code": rc, "log": str(log_path), "t": now_utc(), "duration_seconds": round(duration, 1)})
            if rc == 0:
                consecutive = 0
                done_now += 1
                log(f"DONE  {run['run_id']} in {duration:.0f}s (exit 0, verified)")
                event(root, "run_completed", run=run["run_id"], seconds=round(duration, 1), exit_code=0)
            else:
                consecutive += 1
                failures += 1
                log(f"FAILED {run['run_id']} exit={rc}; log: {log_path}")
                event(root, "run_failed", run=run["run_id"], exit_code=rc)
                if consecutive >= max_consecutive_failures:
                    print(f"STOPPING SAFELY: {consecutive} consecutive failures (likely a systematic problem). Inspect the logs, then use -Resume.")
                    return 4
        remaining = [r for r in runs if run_status(r, manifest, root)[0] != "verified"]
        if not remaining:
            if subset is None:
                atomic_write_json(state_dir(root) / "DONE.json", {"t": now_utc(), "runs": len(runs)})
                print(f"ALL {len(runs)} RUNS COMPLETE AND VERIFIED. Next: run the validation/aggregation command.")
            else:
                print(f"SHARD COMPLETE: all {len(runs)} requested runs are verified.")
            return 0
        if budget_hit:
            print(f"BUDGET REACHED: {done_now} completed this session, {len(remaining)} requested runs left PENDING (not started, nothing lost).")
            return 1 if failures else 0
        print(f"Finished this session: {done_now} completed, {failures} failed, {len(remaining)} remain. Use -Resume to retry the failed ones.")
        return 1 if failures else 0
    finally:
        release_lock(root)
        event(root, "runner_stopped", pid=os.getpid())


# ----------------------------------------------------------------------------- status / validate
def cmd_status(manifest: dict, root: Path) -> int:
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    counts = {"verified": 0, "pending": 0, "failed": 0, "incomplete": 0, "corrupt": 0}
    failed_ids, per_dataset = [], {}
    for run in runs:
        st, _ = run_status(run, manifest, root)
        counts[st] += 1
        per_dataset.setdefault(run["dataset"], {"verified": 0, "total": 0})
        per_dataset[run["dataset"]]["total"] += 1
        per_dataset[run["dataset"]]["verified"] += st == "verified"
        if st in ("failed", "corrupt"):
            failed_ids.append((run["run_id"], st))
    lock = read_lock(root)
    running = bool(lock) and pid_alive(int(lock.get("pid", -1)))
    active_path = state_dir(root) / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.exists() else None
    measured = measured_durations(manifest, root)
    todo = [r for r in runs if run_status(r, manifest, root)[0] != "verified"]
    eta = sum(estimate_seconds(r, manifest, root, measured) for r in todo)
    print(f"=== Phase 6C five-seed progress ({now_utc()}) ===")
    print(f"Runner process: {'RUNNING (PID %s)' % lock['pid'] if running else 'not running'}")
    print(f"Verified complete: {counts['verified']}/{len(runs)} | pending {counts['pending']} | failed {counts['failed']} | incomplete {counts['incomplete']} | corrupt {counts['corrupt']}")
    for d, v in per_dataset.items():
        print(f"  {d}: {v['verified']}/{v['total']}")
    if active and running:
        started = active.get("started")
        print(f"Active run: #{active['order']} {active['run_id']} (since {started})")
    elif active and not running:
        print(f"Last active run was {active['run_id']} (runner no longer running -> use the resume command)")
    print(f"Remaining runs: {len(todo)} | rough ETA: {eta / 3600:.1f} h")
    if failed_ids:
        print("Failures / problems:")
        for rid, st in failed_ids:
            print(f"  - {rid} [{st}]")
    ev = state_dir(root) / "events.jsonl"
    if ev.exists():
        print("Recent events:")
        for line in ev.read_text(encoding="utf-8").splitlines()[-5:]:
            print("  " + line)
    return 0


def cmd_validate(manifest: dict, root: Path) -> int:
    runs = manifest["runs"]
    counts = {"verified": 0, "pending": 0, "failed": 0, "incomplete": 0, "corrupt": 0}
    problems_all = {}
    for run in runs:
        st, probs = run_status(run, manifest, root)
        counts[st] += 1
        if probs:
            problems_all[run["run_id"]] = probs
    print(f"Expected runs: {len(runs)} | verified: {counts['verified']} | pending: {counts['pending']} | failed: {counts['failed']} | incomplete: {counts['incomplete']} | corrupt: {counts['corrupt']}")
    for rid, probs in problems_all.items():
        print(f"  PROBLEM {rid}: {probs}")
    ok = counts["verified"] == len(runs)
    print("VALIDATION: " + ("PASS - all runs complete, verified and consistent with the locked manifest" if ok else "NOT COMPLETE"))
    return 0 if ok else 1


# ----------------------------------------------------------------------------- statistics
def exact_sign_test(diffs):
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return 1.0
    k = sum(1 for x in d if x > 0)
    tail = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def exact_wilcoxon(diffs):
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return 1.0
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        avg = (i + j) / 2 + 1
        for t in range(i, j + 1):
            ranks[order[t]] = avg
        i = j + 1
    w_obs = sum(r for r, x in zip(ranks, d) if x > 0)
    total = sum(ranks)
    dist = [sum(r for r, s in zip(ranks, signs) if s) for signs in itertools.product([0, 1], repeat=n)]
    lo = sum(1 for w in dist if w <= w_obs + 1e-12) / len(dist)
    hi = sum(1 for w in dist if w >= w_obs - 1e-12) / len(dist)
    return min(1.0, 2 * min(lo, hi))


def holm(pvalues):
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted = [0.0] * len(pvalues)
    running = 0.0
    m = len(pvalues)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvalues[i])
        adjusted[i] = min(1.0, running)
    return adjusted


def load_run_metrics(run: dict, root: Path, source: str):
    import numpy as np

    out = root / run["out_dir"]
    fin = json.loads((out / "final_validation_metrics.json").read_text(encoding="utf-8"))
    rm_path = out / "round_metrics.csv"
    import pandas as pd

    rm = pd.read_csv(rm_path)
    rm = rm[rm["round"] >= 1]
    diag = json.loads((out / "phase6c_diagnostics.json").read_text(encoding="utf-8")) if (out / "phase6c_diagnostics.json").exists() else {}
    if source == "test":
        path = root / "results_phase6c" / "_final_test" / run["dataset"] / run["arm"] / f"seed_{run['seed']}" / "final_test_result.json"
        if not path.exists():
            return None
        ft = json.loads(path.read_text(encoding="utf-8"))
        best = ft["best_checkpoint"]["primary_threshold"]
        last = ft["last_checkpoint"]["primary_threshold"]
        t15 = ft["best_checkpoint"]["targets"]["15pct"]
        t5 = ft["best_checkpoint"]["targets"]["5pct"]
        t1 = ft["best_checkpoint"]["targets"]["1pct"]
    else:
        best = fin["report_partition_at_selected_threshold"]
        last = fin.get("last_round_report_partition") or {}
        t15 = fin["threshold_diagnostics"]["15pct"].get("independent_evaluation", {})
        t5 = fin["threshold_diagnostics"]["5pct"].get("independent_evaluation", {})
        t1 = fin["threshold_diagnostics"]["1pct"].get("independent_evaluation", {})
    final_loss = float(rm["mean_train_loss"].iloc[-1]) if "mean_train_loss" in rm else float("nan")
    last_auc = float(last.get("roc_auc", float("nan")))
    diverged = bool((not math.isfinite(final_loss)) or final_loss > 1e3 or (math.isfinite(last_auc) and last_auc <= 0.5 + 1e-6))
    return {
        "dataset": run["dataset"], "arm": run["arm"], "seed": run["seed"], "source": source,
        "auc_best": best.get("roc_auc"), "pr_auc_best": best.get("pr_auc"), "f1_best": best.get("f1"),
        "fpr_best": best.get("fpr"), "recall_best": best.get("recall_adr"), "precision_best": best.get("precision"),
        "auc_last": last.get("roc_auc"), "f1_last": last.get("f1"),
        "fpr_at_1pct": t1.get("fpr"), "recall_at_1pct": t1.get("recall_adr"),
        "fpr_at_5pct": t5.get("fpr"), "recall_at_5pct": t5.get("recall_adr"),
        "fpr_at_15pct": t15.get("fpr"), "recall_at_15pct": t15.get("recall_adr"),
        "best_round": fin.get("best_round"), "final_train_loss": final_loss, "diverged": diverged,
        "malicious_share_selected": (diag.get("updates", {}) or {}).get("malicious_received_total"),
        "worst_client_recall": (diag.get("fairness", {}) or {}).get("worst_client_recall"),
        "selection_gini": (diag.get("participation", {}) or {}).get("selection_gini"),
        "clients_ever_selected": (diag.get("participation", {}) or {}).get("clients_ever_selected"),
        "surrogate_weight_share": float(rm["surrogate_weight_share"].mean()) if "surrogate_weight_share" in rm else None,
        "mean_delivery_ratio": float(rm["mean_update_delivered"].mean()) if "mean_update_delivered" in rm else None,
        "bytes_on_wire": float(rm["communication_bytes_on_wire"].sum()) if "communication_bytes_on_wire" in rm else None,
    }


def cmd_aggregate(manifest: dict, root: Path, source: str, out_dir: Path) -> int:
    import numpy as np
    import pandas as pd

    rows = []
    for run in manifest["runs"]:
        if run_status(run, manifest, root)[0] != "verified":
            continue
        m = load_run_metrics(run, root, source)
        if m is not None:
            rows.append(m)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not rows:
        print("No verified runs with results for this source.")
        return 1
    table = pd.DataFrame(rows)
    table.to_csv(out_dir / f"runs_table_{source}.csv", index=False)
    metrics = ["auc_best", "pr_auc_best", "f1_best", "fpr_best", "recall_best", "auc_last", "fpr_at_1pct", "recall_at_1pct",
               "fpr_at_5pct", "recall_at_5pct", "fpr_at_15pct", "recall_at_15pct"]
    per_arm = []
    for (dataset, arm), g in table.groupby(["dataset", "arm"]):
        row = {"dataset": dataset, "arm": arm, "n_seeds": len(g), "diverged_runs": int(g["diverged"].sum())}
        for m in metrics:
            v = pd.to_numeric(g[m], errors="coerce")
            row[f"{m}_mean"], row[f"{m}_sd"], row[f"{m}_median"] = v.mean(), v.std(ddof=1) if len(v) > 1 else float("nan"), v.median()
        per_arm.append(row)
    pd.DataFrame(per_arm).to_csv(out_dir / f"arm_summary_{source}.csv", index=False)
    pairs = {a["arm"]: a["compare_with"] for a in manifest["arms"] if a["compare_with"]}
    primary = {tuple(c) for c in manifest["primary_contrasts"]}
    contrasts = []
    for dataset in manifest["datasets"]:
        for arm, ref in pairs.items():
            a = table[(table.dataset == dataset) & (table.arm == arm)].set_index("seed")
            b = table[(table.dataset == dataset) & (table.arm == ref)].set_index("seed")
            common = sorted(set(a.index) & set(b.index))
            if len(common) < 2:
                continue
            for metric in ("auc_best", "f1_best", "fpr_at_15pct", "auc_last"):
                d = [float(a.loc[s, metric]) - float(b.loc[s, metric]) for s in common
                     if pd.notna(a.loc[s, metric]) and pd.notna(b.loc[s, metric])]
                if len(d) < 2:
                    continue
                contrasts.append({
                    "dataset": dataset, "arm": arm, "versus": ref, "metric": metric, "n_pairs": len(d),
                    "mean_diff": float(np.mean(d)), "sd_diff": float(np.std(d, ddof=1)), "median_diff": float(np.median(d)),
                    "n_positive": int(sum(x > 0 for x in d)), "per_seed_diffs": json.dumps([round(x, 5) for x in d]),
                    "sign_test_p": exact_sign_test(d), "wilcoxon_exact_p": exact_wilcoxon(d),
                    "primary_family": (arm, ref) in primary and metric == "auc_best",
                })
    ctab = pd.DataFrame(contrasts)
    if len(ctab):
        ctab["holm_p_primary"] = float("nan")
        for dataset in ctab["dataset"].unique():
            mask = (ctab.dataset == dataset) & ctab.primary_family
            if mask.any():
                ctab.loc[mask, "holm_p_primary"] = holm(list(ctab.loc[mask, "wilcoxon_exact_p"]))
    ctab.to_csv(out_dir / f"paired_contrasts_{source}.csv", index=False)
    with open(out_dir / f"SUMMARY_{source}.md", "w", encoding="utf-8") as md:
        md.write(f"# Phase 6C summary ({source} metrics)\n\nRuns aggregated: {len(table)}. Diverged runs are reported, never excluded.\n\n")
        for dataset in manifest["datasets"]:
            md.write(f"## {dataset}\n\n| arm | n | AUC best (mean±sd) | AUC last (mean) | F1 best | FPR@15% | diverged |\n|---|---|---|---|---|---|---|\n")
            for r in per_arm:
                if r["dataset"] == dataset:
                    md.write(f"| {r['arm']} | {r['n_seeds']} | {r['auc_best_mean']:.4f}±{r['auc_best_sd']:.4f} | {r['auc_last_mean']:.4f} | {r['f1_best_mean']:.4f} | {r['fpr_at_15pct_mean']:.4f} | {r['diverged_runs']} |\n")
            md.write("\n")
        md.write("Paired contrasts (exact tests; with n=5 the smallest attainable two-sided p is 0.0625; no significance claim is made).\n")
    print(f"Wrote {out_dir}/runs_table_{source}.csv, arm_summary_{source}.csv, paired_contrasts_{source}.csv, SUMMARY_{source}.md")
    print(pd.DataFrame(per_arm)[["dataset", "arm", "n_seeds", "diverged_runs", "auc_best_mean", "auc_last_mean", "f1_best_mean"]].round(4).to_string(index=False))
    return 0


# ----------------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "plan", "run", "status", "validate", "aggregate"])
    parser.add_argument("--manifest", default=str(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-consecutive-failures", type=int, default=3)
    parser.add_argument("--skip-data-hash", action="store_true")
    parser.add_argument("--only-run-ids", default=None, help="comma list or file (one run id per line): run only these")
    parser.add_argument("--stop-after-minutes", type=float, default=None, help="do not START a run that would exceed this wall-clock budget")
    parser.add_argument("--duration-estimates", default=None, help="JSON {'dataset/arm': seconds} used by the time budget")
    parser.add_argument("--cloud-mode", action="store_true",
                        help="remote machine without the locked test files: requires them to be ABSENT")
    parser.add_argument("--min-free-gb", type=float, default=20.0)
    parser.add_argument("--source", choices=["validation", "test"], default="validation")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    root = Path(args.root)
    try:
        manifest = load_manifest(Path(args.manifest))
    except Exception as exc:  # noqa: BLE001
        print(f"CRITICAL: {exc}")
        return 2
    if args.command == "preflight":
        return 0 if print_preflight(preflight(manifest, root, not args.skip_data_hash, args.min_free_gb, args.cloud_mode)) else 2
    if args.command == "plan":
        cmd_plan(manifest, root)
        return 0
    if args.command == "run":
        return cmd_run(manifest, root, args.resume, args.max_consecutive_failures, args)
    if args.command == "status":
        return cmd_status(manifest, root)
    if args.command == "validate":
        return cmd_validate(manifest, root)
    return cmd_aggregate(manifest, root, args.source, Path(args.out) if args.out else root / "results_phase6c" / "_summary")


if __name__ == "__main__":
    sys.exit(main())
