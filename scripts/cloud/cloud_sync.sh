#!/usr/bin/env bash
# Copy results to a second, independent location every SYNC_INTERVAL seconds. Never deletes anything at the destination.
# SYNC_TARGET forms:  /mnt/volume/path (second disk)  |  user@host:/path (rsync over SSH)  |  rclone:remote:bucket/path
set -uo pipefail
cd "$(dirname "$0")/../.."
INTERVAL="${SYNC_INTERVAL:-600}"
TARGET="${SYNC_TARGET:?set SYNC_TARGET}"
while true; do
  if [[ "$TARGET" == rclone:* ]]; then
    rclone copy results_phase6c "${TARGET#rclone:}" --exclude "*.tmp" --transfers 4 || echo "rclone failed $(date)"
  else
    rsync -a --exclude '*.tmp' results_phase6c/ "$TARGET"/ || echo "rsync failed $(date)"
  fi
  echo "synced $(date -u +%FT%TZ)"
  [ -f results_phase6c/_state/DONE.json ] && { echo "all runs done; final sync complete"; exit 0; }
  sleep "$INTERVAL"
done
