"""Encrypt the TRAIN-SIDE data for storage in a PRIVATE repository (AES-256 via GnuPG, symmetric passphrase).

  * only train/validation data is packaged; the locked FINAL-TEST files are refused by name and never read;
  * nothing is uploaded by this script; it only writes data_enc/*.tar.gpg next to the repository;
  * the passphrase is read from the P6C_DATA_PASSPHRASE environment variable or asked interactively (never written to disk).
After decryption the manifest's dataset hashes (verified by the orchestrator preflight) prove the data is intact.

usage: python scripts/gha/prepare_encrypted_data.py [--out data_enc] [--root .]
       python scripts/gha/prepare_encrypted_data.py --selftest      (roundtrip with dummy data, no real data touched)
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("UNSW_NB15_testing-set.csv", "test.csv.gz", "raw_csv")
BUNDLES = {
    "unsw_train": ["data/UNSW_NB15_training-set.csv"],
    "ciciot_trainval": [
        "data/CICIoT2023/prepared_verified_v2_filegroup/train.csv.gz",
        "data/CICIoT2023/prepared_verified_v2_filegroup/validation.csv.gz",
        "data/CICIoT2023/prepared_verified_v2_filegroup/preparation_metadata.json",
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def gpg_encrypt(src: Path, dst: Path, passphrase: str) -> None:
    cmd = ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase-fd", "0", "--symmetric",
           "--cipher-algo", "AES256", "--s2k-mode", "3", "--s2k-digest-algo", "SHA512", "--s2k-count", "65011712",
           "-o", str(dst), str(src)]
    subprocess.run(cmd, input=passphrase.encode(), check=True, capture_output=True)


def gpg_decrypt(src: Path, dst: Path, passphrase: str) -> None:
    cmd = ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase-fd", "0", "--decrypt", "-o", str(dst), str(src)]
    subprocess.run(cmd, input=passphrase.encode(), check=True, capture_output=True)


def build_tar(files: list[str], root: Path, dest: Path) -> list[dict]:
    manifest = []
    with tarfile.open(dest, "w") as tar:
        for rel in files:
            if any(token in rel for token in FORBIDDEN):
                raise SystemExit(f"REFUSED: {rel} looks like a locked test or raw file")
            path = root / rel
            tar.add(path, arcname=rel)
            manifest.append({"file": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default=str(ROOT / "data_enc"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    root, out = Path(args.root), Path(args.out)
    if out.exists() and any(out.iterdir()):
        print(f"REFUSED: {out} already contains files (will not overwrite).")
        return 2
    passphrase = os.environ.get("P6C_DATA_PASSPHRASE") or getpass.getpass("Passphrase (store it as the GitHub secret P6C_DATA_PASSPHRASE): ")
    if len(passphrase) < 16:
        print("REFUSED: use a passphrase of at least 16 characters.")
        return 2
    if not os.environ.get("P6C_DATA_PASSPHRASE") and getpass.getpass("Repeat passphrase: ") != passphrase:
        print("REFUSED: passphrases differ.")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    index = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, files in BUNDLES.items():
            tar_path = Path(tmp) / f"{name}.tar"
            index[name] = build_tar(files, root, tar_path)
            enc = out / f"{name}.tar.gpg"
            gpg_encrypt(tar_path, enc, passphrase)
            index[name].append({"encrypted_file": enc.name, "encrypted_sha256": sha256(enc), "encrypted_bytes": enc.stat().st_size})
            print(f"{enc}  {enc.stat().st_size / 2**20:.1f} MB")
    (out / "INDEX.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print("Done. Nothing was uploaded. Commit data_enc/ ONLY to the PRIVATE repository, after you approve.")
    return 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "plain.bin").write_bytes(os.urandom(50_000))
        gpg_encrypt(tmp / "plain.bin", tmp / "plain.gpg", "a-long-test-passphrase-123")
        gpg_decrypt(tmp / "plain.gpg", tmp / "back.bin", "a-long-test-passphrase-123")
        assert (tmp / "back.bin").read_bytes() == (tmp / "plain.bin").read_bytes()
        try:
            gpg_decrypt(tmp / "plain.gpg", tmp / "bad.bin", "wrong-passphrase-xxxxxxxx")
        except subprocess.CalledProcessError:
            print("selftest OK (roundtrip works, wrong passphrase rejected)")
            return 0
        print("selftest FAILED: wrong passphrase was accepted")
        return 1


if __name__ == "__main__":
    sys.exit(main())
