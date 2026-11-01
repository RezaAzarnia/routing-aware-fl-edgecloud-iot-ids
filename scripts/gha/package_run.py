"""Package VERIFIED runs into deterministic tar.gz files with a receipt (config hash, commit, seed, metrics, checksum).

usage: python scripts/gha/package_run.py --run-ids a,b,c --out gha_out [--manifest M] [--root R]
Only runs whose COMPLETE.json verifies against the locked manifest are packaged; others are listed in the
receipts file with status 'not_verified' (and are NOT counted as done by the planner).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import load_manifest, now_utc, sha256_file, verify_run_dir  # noqa: E402


def deterministic_targz(src: Path, arcname: str, dest: Path) -> None:
    with open(dest, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for path in sorted(p for p in src.rglob("*") if p.is_file()):
                    info = tar.gettarinfo(str(path), arcname=f"{arcname}/{path.relative_to(src).as_posix()}")
                    info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
                    with open(path, "rb") as handle:
                        tar.addfile(info, handle)


def metrics_summary(run_dir: Path) -> dict:
    try:
        fin = json.loads((run_dir / "final_validation_metrics.json").read_text(encoding="utf-8"))
        best = fin["report_partition_at_selected_threshold"]
        last = fin.get("last_round_report_partition") or {}
        return {"best_round": fin.get("best_round"),
                "report_auc_best": best.get("roc_auc"), "report_f1_best": best.get("f1"), "report_fpr_best": best.get("fpr"),
                "report_auc_last": last.get("roc_auc")}
    except Exception as exc:  # noqa: BLE001
        return {"metrics_error": repr(exc)}


def package(manifest: dict, root: Path, run_ids: list[str], out: Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    by_id = {r["run_id"]: r for r in manifest["runs"]}
    receipts = []
    commit = os.environ.get("GITHUB_SHA", "")
    runner = {"os": platform.platform(), "python": platform.python_version(), "cpus": os.cpu_count(),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
              "runner_name": os.environ.get("RUNNER_NAME")}
    for rid in run_ids:
        run = by_id[rid]
        run_dir = root / run["out_dir"]
        problems = verify_run_dir(run_dir, run, manifest) if run_dir.exists() else ["run directory missing"]
        receipt = {"run_id": rid, "dataset": run["dataset"], "arm": run["arm"], "seed": run["seed"],
                   "config_sha256": run["config_sha256"], "manifest_sha256": manifest["manifest_sha256"],
                   "code_fingerprint": manifest["code_fingerprint"], "git_commit": commit, "runner": runner,
                   "packaged_utc": now_utc()}
        if problems:
            receipt.update({"status": "not_verified", "problems": problems})
        else:
            tar_path = out / f"{rid}.tar.gz"
            deterministic_targz(run_dir, run["out_dir"], tar_path)
            complete = json.loads((run_dir / "COMPLETE.json").read_text(encoding="utf-8"))
            receipt.update({
                "status": "verified", "tarball": tar_path.name, "tarball_sha256": sha256_file(tar_path),
                "tarball_bytes": tar_path.stat().st_size, "run_duration_seconds": complete.get("duration_seconds"),
                "complete_json_sha256": sha256_file(run_dir / "COMPLETE.json"), **metrics_summary(run_dir),
            })
            (out / f"{rid}.tar.gz.sha256").write_text(f"{receipt['tarball_sha256']}  {tar_path.name}\n", encoding="utf-8")
        receipts.append(receipt)
    with open(out / "receipts.jsonl", "a", encoding="utf-8", newline="\n") as handle:
        for rec in receipts:
            handle.write(json.dumps(rec) + "\n")
    return receipts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--run-ids", required=True, help="comma list or file")
    ap.add_argument("--out", default="gha_out")
    args = ap.parse_args()
    manifest = load_manifest(Path(args.manifest))
    value = args.run_ids
    ids = [l.strip() for l in Path(value).read_text().splitlines()] if Path(value).exists() else value.split(",")
    ids = [i.strip() for i in ids if i.strip()]
    unknown = [i for i in ids if i not in {r["run_id"] for r in manifest["runs"]}]
    if unknown:
        print(f"unknown run ids: {unknown[:3]}")
        return 2
    receipts = package(manifest, Path(args.root), ids, Path(args.out))
    ok = sum(r["status"] == "verified" for r in receipts)
    print(f"packaged {ok} verified runs, {len(receipts) - ok} not verified (not packaged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
