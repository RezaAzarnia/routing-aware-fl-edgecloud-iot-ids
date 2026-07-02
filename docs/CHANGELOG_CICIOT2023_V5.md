# CICIoT2023 V5 changes

- Added dataset dispatcher while preserving the original UNSW-NB15 loader.
- Added explicit CICIoT2023 train/validation/test loader.
- Added chunked raw-shard preparation with deterministic shard-level split.
- Added binary-label conversion while preserving original attack names.
- Added reproducible training balancing and natural validation/test category sampling.
- Added preparation metadata, label-count files, and source-shard manifest.
- Disabled test-derived calibration for CICIoT2023; validation is explicit.
- Added CICIoT2023 preflight, pilot, clip-screen, five-seed, baseline, ablation, and sweep configs/BAT files.
- Added CICIoT2023 loader unit test.
- Added `baselines_only` suite to avoid rerunning Proposed Full unnecessarily.
- Verified original and new tests: 22 passed.
- Verified an end-to-end synthetic CICIoT2023-like preparation and experiment run.
