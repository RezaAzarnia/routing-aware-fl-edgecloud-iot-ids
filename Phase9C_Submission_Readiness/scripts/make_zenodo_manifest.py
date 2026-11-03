"""Build ZENODO_RELEASE_MANIFEST.json: the list of files proposed for a Zenodo release with SHA-256 hashes. Read-only; creates NO archive and uploads NOTHING.
Included: git-tracked source, configs, manifests, tests, docs, figures, ledgers and tables. Excluded by construction: datasets (data/), raw run folders (results_*),
untracked archives, scratch files, credentials. Locked final-test files are never touched (the hashing only reads git-tracked files).
python Phase9C_Submission_Readiness/scripts/make_zenodo_manifest.py [--out PATH]"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_PREFIXES = ("data/", "results_", "Phase6C_Final_Handoff", "posthoc_threshold_fix/_tmp")
EXCLUDE_SUFFIXES = (".zip", ".joblib", ".pt", ".npz", ".env", ".pem", ".key")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "Phase9C_Submission_Readiness" / "ZENODO_RELEASE_MANIFEST.json"))
    args = ap.parse_args()
    files, skipped = [], []
    for rel in git("ls-files").splitlines():
        if rel.startswith(EXCLUDE_PREFIXES) or rel.endswith(EXCLUDE_SUFFIXES) or "secret" in rel.lower() or "token" in rel.lower():
            skipped.append(rel)
            continue
        p = ROOT / rel
        if p.is_file():
            files.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha(p)})
    out = {"purpose": "Proposed contents of a Zenodo release (NOT created, NOT uploaded)", "git_head_at_generation": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
           "tags": git("tag").splitlines(), "n_files": len(files), "total_bytes": sum(f["bytes"] for f in files), "n_excluded": len(skipped),
           "excluded_rule": {"prefixes": EXCLUDE_PREFIXES, "suffixes": EXCLUDE_SUFFIXES},
           "regenerate_at_release": "run this script on the final tagged commit; the git_head_at_generation must equal the release tag",
           "files": files}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{len(files)} files, {out['total_bytes'] / 1e6:.1f} MB, {len(skipped)} excluded -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
