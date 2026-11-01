"""Plan resumable GitHub-Actions shards for the locked Phase-6C manifest.

* A run counts as DONE only if a prior receipt exists whose manifest hash, config hash and code fingerprint
  equal the locked manifest (stale/foreign receipts are ignored, never trusted).
* Completed runs are never planned again unless explicitly listed in --rerun-ids.
* Shards are packed (in manifest order) so that estimated minutes <= --target-minutes (< GitHub's 6 h job limit).
* Spending guards: --max-shards and --max-total-minutes truncate the plan (nothing is silently dropped: the
  remaining pending runs are reported and picked up by the next dispatch).

usage: python scripts/gha/plan_shards.py --manifest M --durations D [--receipts-dir DIR] [--out plan.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import load_manifest  # noqa: E402

USD_PER_MINUTE = 0.006      # GitHub-hosted Linux 2-core, private repositories (2026 price list)
INCLUDED_FREE_MINUTES = 2000
INCLUDED_PRO_MINUTES = 3000


def read_receipts(directory: Path | None) -> list[dict]:
    receipts: list[dict] = []
    if not directory or not Path(directory).exists():
        return receipts
    for path in sorted(Path(directory).rglob("*")):
        if path.suffix not in (".jsonl", ".json") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        try:
            if path.suffix == ".jsonl":
                items = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                loaded = json.loads(text)
                items = loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            continue
        receipts.extend(i for i in items if isinstance(i, dict) and "run_id" in i)
    return receipts


def done_run_ids(manifest: dict, receipts: list[dict]) -> tuple[set[str], list[str]]:
    by_id = {r["run_id"]: r for r in manifest["runs"]}
    done, ignored = set(), []
    for rec in receipts:
        run = by_id.get(rec.get("run_id"))
        ok = (
            run is not None and rec.get("status") == "verified"
            and rec.get("manifest_sha256") == manifest["manifest_sha256"]
            and rec.get("config_sha256") == run["config_sha256"]
            and rec.get("code_fingerprint") == manifest["code_fingerprint"]
            and rec.get("seed") == run["seed"]
        )
        if ok:
            done.add(rec["run_id"])
        else:
            ignored.append(str(rec.get("run_id")))
    return done, ignored


def plan(manifest: dict, durations: dict, done: set[str], datasets, arms, seeds, only_ids, rerun_ids,
         target_minutes: float, max_shards: int, max_total_minutes: float) -> dict:
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    candidates = []
    for r in runs:
        if datasets and r["dataset"] not in datasets:
            continue
        if arms and r["arm"] not in arms:
            continue
        if seeds and r["seed"] not in seeds:
            continue
        if only_ids and r["run_id"] not in only_ids:
            continue
        if r["run_id"] in done and r["run_id"] not in rerun_ids:
            continue
        candidates.append(r)

    def est(r):
        key = f"{r['dataset']}/{r['arm']}"
        if key not in durations:
            raise KeyError(f"no duration estimate for {key}")
        return float(durations[key]) / 60.0

    shards, current, current_min = [], [], 0.0
    for r in candidates:
        minutes = est(r)
        if current and current_min + minutes > target_minutes:
            shards.append((current, current_min))
            current, current_min = [], 0.0
        current.append(r)
        current_min += minutes
    if current:
        shards.append((current, current_min))

    selected, total = [], 0.0
    for runs_, minutes in shards:
        if len(selected) >= max_shards or (selected and total + minutes > max_total_minutes):
            break
        if not selected and minutes > max_total_minutes:
            break
        selected.append((runs_, minutes))
        total += minutes
    planned_ids = {r["run_id"] for runs_, _ in selected for r in runs_}
    deferred = [r["run_id"] for r in candidates if r["run_id"] not in planned_ids]
    # a job also pays ~2-4 min of set-up (checkout, wheels from cache, data decryption, preflight)
    setup_minutes = 3.0 * len(selected)
    billed = total + setup_minutes
    return {
        "shards": [{"shard": f"s{index + 1:03d}", "run_ids": [r["run_id"] for r in runs_],
                    "est_minutes": round(minutes, 1)} for index, (runs_, minutes) in enumerate(selected)],
        "summary": {
            "manifest_runs": len(runs), "already_done": len(done), "candidates": len(candidates),
            "planned_runs": len(planned_ids), "deferred_runs": len(deferred), "n_shards": len(selected),
            "est_run_minutes": round(total, 1), "est_billed_minutes_incl_setup": round(billed, 1),
            "est_cost_if_all_billed_usd": round(billed * USD_PER_MINUTE, 2),
            "target_minutes": target_minutes, "max_shards": max_shards, "max_total_minutes": max_total_minutes,
            "included_minutes_free_plan": INCLUDED_FREE_MINUTES, "included_minutes_pro_plan": INCLUDED_PRO_MINUTES,
        },
        "deferred_run_ids": deferred,
    }


def csv(value: str):
    return {x.strip() for x in value.split(",") if x.strip()} if value else set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"))
    ap.add_argument("--durations", default=str(ROOT / "scripts" / "gha" / "durations_gha.json"))
    ap.add_argument("--receipts-dir", default=None)
    ap.add_argument("--datasets", default="")
    ap.add_argument("--arms", default="")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--run-ids", default="")
    ap.add_argument("--rerun-ids", default="")
    ap.add_argument("--target-minutes", type=float, default=240.0)
    ap.add_argument("--max-shards", type=int, default=4)
    ap.add_argument("--max-total-minutes", type=float, default=600.0)
    ap.add_argument("--out", default="plan.json")
    args = ap.parse_args()

    manifest = load_manifest(Path(args.manifest))
    durations = json.loads(Path(args.durations).read_text(encoding="utf-8"))
    receipts = read_receipts(Path(args.receipts_dir) if args.receipts_dir else None)
    done, ignored = done_run_ids(manifest, receipts)
    result = plan(manifest, durations, done, csv(args.datasets), csv(args.arms), {int(s) for s in csv(args.seeds)},
                  csv(args.run_ids), csv(args.rerun_ids), args.target_minutes, args.max_shards, args.max_total_minutes)
    result["summary"]["receipts_read"] = len(receipts)
    result["summary"]["receipts_ignored_as_stale_or_foreign"] = len(ignored)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    s = result["summary"]
    print(json.dumps(s, indent=2))
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        matrix = {"include": [{"shard": sh["shard"], "run_ids": ",".join(sh["run_ids"])} for sh in result["shards"]]}
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"matrix={json.dumps(matrix, separators=(',', ':'))}\n")
            handle.write(f"n_shards={s['n_shards']}\n")
            handle.write(f"pending={s['candidates']}\n")
            handle.write(f"deferred={s['deferred_runs']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
