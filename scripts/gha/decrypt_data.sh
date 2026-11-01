#!/usr/bin/env bash
# Runs ON THE GITHUB RUNNER: decrypt the train-side data (never the locked test files) into ./data.
# The passphrase comes from the GitHub secret via the environment and is fed through stdin (not argv).
set -euo pipefail
: "${P6C_DATA_PASSPHRASE:?secret P6C_DATA_PASSPHRASE is not set}"
[ -d data_enc ] || { echo "data_enc/ is missing from the private repository"; exit 2; }
mkdir -p data
for enc in data_enc/*.tar.gpg; do
  printf '%s' "$P6C_DATA_PASSPHRASE" | gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 --decrypt -o "${enc%.gpg}.dec" "$enc"
  tar -xf "${enc%.gpg}.dec" -C .
  rm -f "${enc%.gpg}.dec"
done
# hard guard: the locked test files must not exist on the runner
if [ -e data/UNSW_NB15_testing-set.csv ] || [ -e data/CICIoT2023/prepared_verified_v2_filegroup/test.csv.gz ] || [ -d data/CICIoT2023/raw_csv ]; then
  echo "CRITICAL: a locked test/raw file is present on the runner"; exit 3; fi
echo "train-side data decrypted: $(find data -type f | wc -l) files (no test files present)"
