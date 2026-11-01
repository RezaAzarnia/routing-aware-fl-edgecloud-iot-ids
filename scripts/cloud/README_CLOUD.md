# Running the locked Phase 6C experiments on a cloud VM

Principles: the manifest (`docs/phase6c/EXPERIMENT_MANIFEST.json`, sha256 `c648b935…c1f267`) and every configuration stay byte-identical;
the locked **final-test files never leave your computer**; the experiment runs on exactly one machine; nothing is published to GitHub.

## Platform decision (important)
Completed local runs were produced on Windows/x86-64 with 10 torch threads. Floating-point results may differ slightly on Linux or with a different thread count,
and the training dynamics are sensitive to small differences (Phase 6B showed divergence/collapse in some conditions). Paired comparisons (same seed, different arm) should therefore
come from **one platform**. Default recommendation: **run all 240 on the cloud VM** and keep the 6 local runs only as a cross-platform reference
(`reference_local_partial/`). If `cloud_compat_test.sh` reports `IDENTICAL`, the verified local runs may be copied into the cloud `results_phase6c/` (the runner re-verifies them against the manifest).

## Steps
1. (local) `python scripts/cloud/make_transfer_bundle.py` → `cloud_transfer.tar` (+ sha256 printed). Contains code (git bundle), train-side data, dependency lock, verified local runs. **No test files.**
2. Create a Linux VM (Ubuntu 22.04/24.04, x86-64, ≥ 8 vCPU, 16 GB RAM, ≥ 50 GB persistent disk). Copy the tar with `scp` (encrypted in transit); compare the printed sha256.
3. (VM) `bash cloud_setup.sh cloud_transfer.tar` — verifies hashes, clones the code from the bundle, installs the locked Python/PyTorch versions, probes the machine, runs the cloud-mode preflight.
4. (VM) `bash scripts/cloud/cloud_compat_test.sh` — regression tests + one real re-run of a completed local job + comparison. Uses only train/validation data and writes to `results_cloud_compat/`.
5. (local, at hand-over, only after step 4 passed) `python scripts/cloud/make_transfer_bundle.py --mark-only` � writes `results_phase6c/_state/MIGRATED_TO_CLOUD.json`; from then on the local runner refuses to run (no duplicate execution).
6. (VM) `SYNC_TARGET=... bash scripts/cloud/cloud_run.sh` — starts detached with `--resume`; optional `iotfl-phase6c.service` restarts it after a crash/reboot.
7. Monitor: `.venv/bin/python scripts/phase6c/orchestrator.py status --cloud-mode`. When finished: `validate` and `aggregate`, download `results_phase6c/`, then run the locked final-test operation **locally** (the test files are only there).
