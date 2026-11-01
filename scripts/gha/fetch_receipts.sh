#!/usr/bin/env bash
# Runs ON THE GITHUB RUNNER (planning job): download the small `receipts-*` artifacts of earlier workflow runs so the planner
# can skip runs that are already verified. Read-only (needs `actions: read`). Missing/expired artifacts simply mean "not done".
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?}"
mkdir -p receipts_in
ids=$(gh api --paginate "repos/${GITHUB_REPOSITORY}/actions/artifacts?per_page=100" \
      --jq '.artifacts[] | select(.expired == false) | select(.name | startswith("receipts-")) | .id' || true)
count=0
for id in $ids; do
  gh api "repos/${GITHUB_REPOSITORY}/actions/artifacts/${id}/zip" > "receipts_in/${id}.zip"
  unzip -oq "receipts_in/${id}.zip" -d "receipts_in/${id}"
  rm -f "receipts_in/${id}.zip"
  count=$((count + 1))
done
echo "downloaded ${count} receipt artifacts"
