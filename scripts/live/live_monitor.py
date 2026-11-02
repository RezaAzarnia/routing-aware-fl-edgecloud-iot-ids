"""READ-ONLY live monitor for the experiment runner: queue progress, the active run's per-round metrics, ETA.

usage: python scripts/live/live_monitor.py [--root R] [--results results_phase6c] [--manifest M] [--watch] [--interval 15] [--last 8]
Never writes anything. Works while a runner is active (reads live_progress.jsonl) and afterwards (shows the last run).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import pid_alive  # noqa: E402


def fmt(seconds) -> str:
    if seconds is None:
        return "--:--"
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def bar(pct: float, width: int = 30) -> str:
    filled = int(width * max(0.0, min(100.0, pct)) / 100.0)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:5.1f}%"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass          # a partially written last line is ignored
    return rows


def snapshot(root: Path, results: str, manifest_path: Path | None, last: int) -> str:
    res = root / results
    out = [f"=== IoT-FL live monitor  {time.strftime('%Y-%m-%d %H:%M:%S')} ==="]
    runs = []
    if manifest_path and manifest_path.exists():
        runs = sorted(json.loads(manifest_path.read_text(encoding="utf-8"))["runs"], key=lambda r: r["order"])
    complete = [r for r in runs if (root / r["out_dir"] / "COMPLETE.json").exists()]
    failed = [r for r in runs if (root / r["out_dir"] / "FAILED.json").exists()]
    lock_path = res / "_state" / "runner.lock"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else None
    alive = bool(lock) and pid_alive(int(lock.get("pid", -1)))
    out.append(f"Runner: {'RUNNING (PID %s)' % lock['pid'] if alive else 'not running'}")
    if runs:
        total = len(runs)
        out.append(f"Overall: {bar(100.0 * len(complete) / total)}  {len(complete)}/{total} verified complete, {len(failed)} failed")
    active_path = res / "_state" / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.exists() else None
    eta_active = None
    if active:
        run = next((r for r in runs if r["run_id"] == active["run_id"]), None)
        run_dir = root / (run["out_dir"] if run else "")
        rows = read_jsonl(run_dir / "live_progress.jsonl") if run else []
        title = f"Active run #{active['order']}: {active['run_id']}" if alive else f"Last active run: {active['run_id']} (runner stopped)"
        out.append(title)
        if rows:
            cur = rows[-1]
            eta_active = cur.get("eta_s")
            out.append(f"  {bar(cur['pct'])}  round {cur['round']}/{cur['rounds_total']}  device={cur['device']}  elapsed {fmt(cur['elapsed_s'])}  ETA {fmt(eta_active)}")
            out.append("  round |   loss |    F1  |   AUC  |  FPR   | sec/round")
            for r in rows[-last:]:
                loss = f"{r['train_loss']:.4f}" if r.get("train_loss") is not None else "   n/a"
                out.append(f"  {r['round']:5d} | {loss:>6} | {r['val_f1'] if r['val_f1'] is not None else float('nan'):.4f} | "
                           f"{r['val_roc_auc'] if r['val_roc_auc'] is not None else float('nan'):.4f} | "
                           f"{r['val_fpr'] if r['val_fpr'] is not None else float('nan'):.4f} | "
                           f"{(r['round_seconds'] if r.get('round_seconds') is not None else float('nan')):7.1f}")
        else:
            out.append("  (no per-round data yet: the run is loading data, or live logging is not enabled - use run_with_live.ps1)")
    # completed-run durations and overall ETA
    durations = {}
    recent = []
    for r in complete:
        try:
            c = json.loads((root / r["out_dir"] / "COMPLETE.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        d = float(c.get("duration_seconds", 0))
        durations.setdefault(r["dataset"], []).append(d)
        recent.append((c.get("completed_utc", ""), r, d))
    if recent:
        out.append(f"Recently completed (last {min(last, len(recent))}):")
        for _, r, d in sorted(recent, key=lambda x: x[0])[-last:]:
            try:
                fin = json.loads((root / r["out_dir"] / "final_validation_metrics.json").read_text(encoding="utf-8"))["report_partition_at_selected_threshold"]
                metrics = f"AUC {fin['roc_auc']:.4f}  F1 {fin['f1']:.4f}"
            except Exception:  # noqa: BLE001
                metrics = ""
            out.append(f"  {r['run_id']:<52s} {fmt(d)}  {metrics}")
    if runs:
        pending = [r for r in runs if r not in complete and (not active or r["run_id"] != active["run_id"])]
        est = 0.0
        for r in pending:
            ds = durations.get(r["dataset"])
            est += (sum(ds) / len(ds)) if ds else {"unsw": 90.0, "ciciot": 200.0}[r["dataset"]]
        est += eta_active or 0.0
        out.append(f"Remaining: {len(pending)} queued + active | rough overall ETA {fmt(est)} (from measured run times)")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--results", default="results_phase6c")
    ap.add_argument("--manifest", default=str(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"))
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=float, default=15)
    ap.add_argument("--last", type=int, default=8)
    args = ap.parse_args()
    root = Path(args.root)
    while True:
        text = snapshot(root, args.results, Path(args.manifest), args.last)
        if args.watch:
            os.system("cls" if os.name == "nt" else "clear")
        print(text, flush=True)
        if not args.watch:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
