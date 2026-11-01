"""Build the minimal, hash-listed transfer bundle for running the locked Phase-6C experiments on a remote Linux VM.

Included  : code (git bundle of release/phase6c; nothing is pushed to GitHub), the locked manifest/configs (inside the
            bundle), TRAIN-SIDE data only (UNSW training CSV, CICIoT2023 prepared train/validation + metadata),
            a dependency lock, and the already verified local runs (as a cross-platform reference only).
Excluded  : the LOCKED FINAL-TEST files (UNSW testing CSV, CICIoT2023 test.csv.gz) and the raw CICIoT2023 shards.
Optional  : --mark-migrated writes results_phase6c/_state/MIGRATED_TO_CLOUD.json so the local runner refuses to run
            (prevents duplicate execution on both machines). Do this only at the moment of hand-over.

usage: python scripts/cloud/make_transfer_bundle.py [--out cloud_transfer] [--mark-migrated]
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import load_manifest, now_utc, verify_run_dir  # noqa: E402

TRAIN_DATA = [
    "data/UNSW_NB15_training-set.csv",
    "data/CICIoT2023/prepared_verified_v2_filegroup/train.csv.gz",
    "data/CICIoT2023/prepared_verified_v2_filegroup/validation.csv.gz",
    "data/CICIoT2023/prepared_verified_v2_filegroup/preparation_metadata.json",
]
FORBIDDEN = ("UNSW_NB15_testing-set.csv", "test.csv.gz", "raw_csv")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "cloud_transfer"))
    parser.add_argument("--mark-migrated", action="store_true")
    parser.add_argument("--mark-only", action="store_true", help="only write the migration marker (no bundle)")
    args = parser.parse_args()
    if args.mark_only:
        manifest = load_manifest(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json")
        marker = ROOT / "results_phase6c" / "_state" / "MIGRATED_TO_CLOUD.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"t": now_utc(), "manifest_sha256": manifest["manifest_sha256"],
                                      "note": "the experiment is executed on the cloud VM; the local runner must not run it"}, indent=2), encoding="utf-8")
        print(f"MIGRATED marker written: {marker}")
        return 0
    out = Path(args.out)
    if out.exists():
        print(f"REFUSED: {out} already exists (will not overwrite a previous bundle).")
        return 2
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if dirty:
        print("REFUSED: tracked files have uncommitted changes; commit first so the bundle equals what runs locally:\n" + dirty)
        return 2
    manifest = load_manifest(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json")
    out.mkdir(parents=True)
    (out / "data").mkdir()

    # 1. code, as a git bundle (no publication)
    subprocess.run(["git", "bundle", "create", str(out / "code.bundle"), "release/phase6c"], check=True, cwd=ROOT, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "release/phase6c"], capture_output=True, text=True, cwd=ROOT).stdout.strip()

    # 2. train-side data only
    for rel in TRAIN_DATA:
        assert not any(f in rel for f in FORBIDDEN), rel
        dst = out / "data" / rel.replace("data/", "", 1)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)

    # 3. dependency lock
    lock = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    wanted = ("torch", "numpy", "pandas", "scikit-learn", "scipy", "PyYAML", "joblib", "tqdm", "matplotlib", "threadpoolctl", "pytest")
    lines = [l for l in lock.splitlines() if l.split("==")[0] in wanted]
    with open(out / "requirements-cloud-lock.txt", "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + f"\n# python {sys.version.split()[0]}\n")

    # 4. verified local runs (reference only; never merged automatically)
    ref = out / "reference_local_partial"
    verified = []
    results_root = ROOT / "results_phase6c"
    for run in manifest["runs"]:
        d = ROOT / run["out_dir"]
        if (d / "COMPLETE.json").exists() and not verify_run_dir(d, run, manifest):
            shutil.copytree(d, ref / run["out_dir"])
            verified.append(run["run_id"])
    for extra in ("_state/events.jsonl",):
        if (results_root / extra).exists():
            (ref / "results_phase6c" / "_state").mkdir(parents=True, exist_ok=True)
            shutil.copy2(results_root / extra, ref / "results_phase6c" / "_state" / "events.jsonl")

    # 5. sidecar facts + hash list
    info = {
        "created_utc": now_utc(), "branch": "release/phase6c", "commit": head,
        "manifest_sha256": manifest["manifest_sha256"], "code_fingerprint": manifest["code_fingerprint"],
        "verified_local_runs": verified, "n_verified_local_runs": len(verified),
        "excluded": "locked final-test files and raw CICIoT2023 shards are NOT in this bundle",
    }
    (out / "TRANSFER_INFO.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    sums = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
        sums.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    with open(out / "SHA256SUMS.txt", "w", encoding="utf-8", newline="\n") as handle:  # LF: must work with Linux `sha256sum -c`
        handle.write("\n".join(sums) + "\n")
    archive = out.with_suffix(".tar")
    with tarfile.open(archive, "w") as tar:
        tar.add(out, arcname="cloud_transfer")
    print(f"bundle dir : {out}\narchive    : {archive}  ({archive.stat().st_size / 2**20:.1f} MB, sha256 {sha256(archive)})")
    print(f"commit {head[:12]} | manifest {manifest['manifest_sha256'][:16]} | verified local runs included for reference: {len(verified)}")
    leaked = [p for p in out.rglob("*") if p.is_file() and any(f in p.as_posix() for f in FORBIDDEN)]
    assert not leaked, f"test/raw files leaked into the bundle: {leaked}"
    if args.mark_migrated:
        marker = results_root / "_state" / "MIGRATED_TO_CLOUD.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"t": now_utc(), "bundle": str(archive), "manifest_sha256": manifest["manifest_sha256"],
                                      "note": "the experiment is executed on the cloud VM; the local runner must not run it"}, indent=2), encoding="utf-8")
        print(f"MIGRATED marker written: {marker}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
