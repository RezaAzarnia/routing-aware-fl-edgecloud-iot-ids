"""Shared helpers for the Phase-6C runner, validator and locked final-test operation."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REQUIRED_ARTIFACTS = [
    "run_record.json", "resolved_config.yaml", "round_metrics.csv", "network_metrics.csv",
    "aggregation_diagnostics.csv", "final_validation_metrics.json", "threshold_diagnostics.json",
    "run_metadata.json", "metric_accounting.json", "best_model_state.pt", "last_model_state.pt",
    "privacy_plan.json", "validation_split_info.json", "phase6c_diagnostics.json",
]


def sha256_file(path: Path, block: int = 1 << 24) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_file(path: Path) -> str:
    """Line-ending-insensitive hash (git may convert LF/CRLF between checkouts)."""
    data = Path(path).read_bytes()
    return sha256_bytes(data.replace(bytes([13, 10]), bytes([10])))


def sha256_gzip_content(path: Path, block: int = 1 << 24) -> str:
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_hash(manifest: dict) -> str:
    """Hash of the manifest content excluding its own hash field (canonical JSON)."""
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    return sha256_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_manifest(path: Path, verify: bool = True) -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if verify and manifest.get("manifest_sha256") != manifest_hash(manifest):
        raise ValueError(f"manifest hash mismatch for {path}: the manifest was modified after it was locked")
    return manifest


def atomic_write_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


CODE_GLOBS = ["src/*.py", "scripts/phase6c/p6c_common.py", "scripts/phase6c/run_one.py", "scripts/phase6c/final_test_evaluate.py",
              "scripts/phase6a/run_validation_only.py", "scripts/phase6b/run_variant.py",
              "prepare_ciciot2023.py", "configs/phase6c/*.yaml"]


def code_fingerprint(root: Path = ROOT, globs=None) -> str:
    """Content hash of the code and configurations that determine training results."""
    entries = []
    for pattern in (globs or CODE_GLOBS):
        for path in sorted(Path(root).glob(pattern)):
            if path.is_file():
                entries.append((path.relative_to(root).as_posix(), sha256_text_file(path)))
    entries.sort()
    return sha256_bytes(json.dumps(entries).encode("utf-8"))


def git_head(root: Path = ROOT) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=root).stdout.strip()


def git_dirty_tracked(root: Path = ROOT) -> list[str]:
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                         text=True, cwd=root).stdout
    return [line for line in out.splitlines() if line.strip()]


def verify_run_dir(run_dir: Path, run: dict, manifest: dict, strict_commit: bool = True) -> list[str]:
    """Return a list of problems (empty list = the run is complete and consistent)."""
    problems: list[str] = []
    run_dir = Path(run_dir)
    complete = run_dir / "COMPLETE.json"
    if not complete.exists():
        return ["COMPLETE.json missing"]
    try:
        record = json.loads(complete.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"COMPLETE.json unreadable: {exc}"]
    if record.get("run_id") != run["run_id"]:
        problems.append("run_id mismatch")
    if record.get("config_sha256") != run["config_sha256"]:
        problems.append("config hash differs from manifest")
    if record.get("manifest_sha256") != manifest["manifest_sha256"]:
        problems.append("manifest hash differs")
    if strict_commit and record.get("code_fingerprint") != manifest.get("code_fingerprint"):
        problems.append("code fingerprint differs from manifest")
    required = manifest.get("required_artifacts", DEFAULT_REQUIRED_ARTIFACTS)
    for name in required:
        path = run_dir / name
        if not path.exists():
            problems.append(f"missing artifact {name}")
            continue
        expected = record.get("artifact_sha256", {}).get(name)
        if expected and sha256_file(path) != expected:
            problems.append(f"artifact hash changed: {name}")
    if manifest.get("verify_training_semantics", True):
        try:
            meta = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
            if meta.get("test_data_loaded") is not False:
                problems.append("run_metadata says test data was loaded")
            if int(meta.get("rounds_executed", -1)) != int(manifest.get("rounds", 30)):
                problems.append(f"rounds_executed {meta.get('rounds_executed')} != {manifest.get('rounds', 30)}")
            acc = json.loads((run_dir / "metric_accounting.json").read_text(encoding="utf-8"))
            if acc.get("invariants_hold") is not True:
                problems.append("metric accounting invariants not satisfied")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"semantic check failed: {exc}")
    leaked = [p.name for p in run_dir.iterdir() if "final_test" in p.name.lower() or p.name.lower().startswith("test_pred")]
    if leaked:
        problems.append(f"test-evaluation artefacts present in a training directory: {leaked}")
    return problems


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def python_exe() -> str:
    return sys.executable
