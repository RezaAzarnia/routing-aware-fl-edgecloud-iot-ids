#!/usr/bin/env bash
# Phase 6C cloud VM setup (Ubuntu 22.04/24.04, x86-64). Run on the VM, in the folder that contains cloud_transfer.tar.
# usage: bash cloud_setup.sh <path-to>/cloud_transfer.tar   (does NOT start any experiment)
set -euo pipefail
TAR="${1:?usage: cloud_setup.sh cloud_transfer.tar}"
WORK="${WORK:-$HOME/iotfl}"
mkdir -p "$WORK" && cd "$WORK"

echo "== 1. unpack and verify hashes"
tar -xf "$TAR" -C "$WORK"
( cd "$WORK/cloud_transfer" && sha256sum -c SHA256SUMS.txt )
if find "$WORK/cloud_transfer" -name 'UNSW_NB15_testing-set.csv' -o -name 'test.csv.gz' -o -name raw_csv | grep -q .; then
  echo "CRITICAL: locked test/raw files found in the bundle"; exit 2; fi

echo "== 2. code from the git bundle (no GitHub needed)"
rm -rf "$WORK/repo"
git clone -q "$WORK/cloud_transfer/code.bundle" "$WORK/repo" -b release/phase6c
cd "$WORK/repo"
git config core.autocrlf false
echo "commit: $(git rev-parse HEAD)"; grep -h '"commit"' "$WORK/cloud_transfer/TRANSFER_INFO.json"

echo "== 3. data (train side only)"
mkdir -p data/CICIoT2023/prepared_verified_v2_filegroup
cp "$WORK/cloud_transfer/data/UNSW_NB15_training-set.csv" data/
cp "$WORK/cloud_transfer/data/CICIoT2023/prepared_verified_v2_filegroup/"* data/CICIoT2023/prepared_verified_v2_filegroup/

echo "== 4. Python 3.11 environment with the locked versions"
if ! command -v uv >/dev/null; then curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; fi
uv python install 3.11
uv venv --python 3.11 .venv
# CPU-only PyTorch wheel index; every other package from PyPI
uv pip install --python .venv/bin/python --extra-index-url https://download.pytorch.org/whl/cpu -r "$WORK/cloud_transfer/requirements-cloud-lock.txt"
.venv/bin/python scripts/cloud/cloud_probe.py --lock "$WORK/cloud_transfer/requirements-cloud-lock.txt" || { echo "PROBE FAILED: fix the listed items before continuing"; exit 3; }

echo "== 5. locked-manifest preflight in CLOUD MODE (requires the test files to be absent)"
.venv/bin/python scripts/phase6c/orchestrator.py preflight --cloud-mode
echo "SETUP OK. Next: bash scripts/cloud/cloud_compat_test.sh   (still no experiment started)"
