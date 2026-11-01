"""Verify downloaded GitHub-Actions artifacts against the locked manifest and rebuild results_phase6c/.

usage: python scripts/gha/verify_downloads.py DOWNLOAD_DIR [--extract-to .] [--manifest M]
DOWNLOAD_DIR may contain the artifacts exactly as downloaded (folders from `gh run download` or unzipped files):
any `receipts.jsonl` and `*.tar.gz` below it are discovered. Nothing in DOWNLOAD_DIR is modified; existing
result directories are never overwritten (a conflicting directory is reported).
Exit 0 only if ALL runs of the manifest are present, hash-correct and verify against the locked manifest.
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import load_manifest, sha256_file, verify_run_dir  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("download_dir")
    ap.add_argument("--extract-to", default=str(ROOT))
    ap.add_argument("--manifest", default=str(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"))
    args = ap.parse_args()
    manifest = load_manifest(Path(args.manifest))
    by_id = {r["run_id"]: r for r in manifest["runs"]}
    base = Path(args.download_dir)
    target_root = Path(args.extract_to)

    receipts: dict[str, list[dict]] = {}
    for path in sorted(base.rglob("receipts.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                rec["_source"] = str(path)
                receipts.setdefault(rec["run_id"], []).append(rec)
    tarballs: dict[str, list[Path]] = {}
    for path in sorted(base.rglob("*.tar.gz")):
        tarballs.setdefault(path.name[: -len(".tar.gz")], []).append(path)

    problems, extracted, skipped_existing, duplicates = [], 0, 0, []
    for rid, run in by_id.items():
        verified = [r for r in receipts.get(rid, []) if r.get("status") == "verified"]
        if not verified:
            problems.append(f"{rid}: no verified receipt")
            continue
        good = [r for r in verified if r.get("manifest_sha256") == manifest["manifest_sha256"]
                and r.get("config_sha256") == run["config_sha256"]
                and r.get("code_fingerprint") == manifest["code_fingerprint"] and r.get("seed") == run["seed"]]
        if not good:
            problems.append(f"{rid}: receipt does not match the locked manifest (config/manifest/code/seed)")
            continue
        if len({r["tarball_sha256"] for r in good}) > 1:
            duplicates.append(rid)
            problems.append(f"{rid}: CONFLICTING results (different tarball hashes) in several artifacts - not merged, inspect manually")
            continue
        rec = good[0]
        candidates = [p for p in tarballs.get(rid, []) if sha256_file(p) == rec["tarball_sha256"]]
        if not candidates:
            problems.append(f"{rid}: tarball missing or its sha256 differs from the receipt")
            continue
        dest = target_root / run["out_dir"]
        if dest.exists():
            if (dest / "COMPLETE.json").exists() and sha256_file(dest / "COMPLETE.json") == rec["complete_json_sha256"]:
                skipped_existing += 1
            else:
                problems.append(f"{rid}: {dest} already exists with different content - not overwritten")
                continue
        else:
            with tarfile.open(candidates[0]) as tar:
                for member in tar.getmembers():          # guard against path traversal
                    resolved = (target_root / member.name).resolve()
                    if not str(resolved).startswith(str(target_root.resolve())):
                        raise SystemExit(f"unsafe path in {candidates[0]}: {member.name}")
                tar.extractall(target_root)
            extracted += 1
        errs = verify_run_dir(dest, run, manifest)
        if errs:
            problems.append(f"{rid}: extracted run does not verify: {errs}")

    present = len(by_id) - len({p.split(":")[0] for p in problems})
    print(f"manifest runs: {len(by_id)} | verified and present: {present} | newly extracted: {extracted} | already present: {skipped_existing}")
    for p in problems[:40]:
        print("  PROBLEM", p)
    if len(problems) > 40:
        print(f"  ... {len(problems) - 40} more problems")
    ok = not problems
    print("RESULT: " + ("ALL RUNS PRESENT AND VERIFIED against the locked manifest. Next: validate_results.ps1 / orchestrator validate + aggregate."
                         if ok else "INCOMPLETE OR INCONSISTENT - see problems above (nothing was overwritten)."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
