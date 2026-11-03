# Phase 10 protocol amendment 1 (owner-approved, before any full run)

## Confirmed defect
In manifest v1 the global preprocessor (imputer statistics, scaler mean/scale, one-hot vocabularies) was fitted with `fit_transform` on **all** training rows, and each client's holdout was carved out **afterwards** (`src/experiment.py`: partitions → holdout). Held-out rows therefore influenced preprocessing statistics (features only, no labels). Root cause: the holdout was defined after `load_dataset`, after the fit. Zero full Phase 10 runs existed before the amendment (`results_phase10/` absent; only synthetic smoke tests).

## Correction (all default-off; historical path byte-identical)
| File | Change |
|---|---|
| `src/partitioning.py` | `group_holdout_mask` (global, predictor-group-level, seeded; replaces the per-client row split), `split_client_holdout_by_mask` (every client must keep training rows) |
| `src/data.py` | `load_dataset(..., holdout_fraction=0)`; UNSW only (CIC raises): groups = predictor vectors rounded to 6 significant digits (stricter than the dataset's exact float64 policy); mask chosen **before** fitting; preprocessor **fitted on non-holdout rows only**, holdout rows only transformed; closure loop: any training row sharing a predictor group or an encoded (model-input) vector with a held-out row moves into the holdout, refit, repeat (converged within the limit for all seeds); `DatasetBundle.holdout_mask/holdout_groups` |
| `src/experiment.py` | passes `holdout_fraction`; client train/holdout from the mask; no new random draw |
| `scripts/phase10/phase10_metrics.py` | holdout evaluation uses the same mask/preprocessor; eligibility = ≥10 attack holdout rows (defined by holdout size only); **analysis raises if the eligible client set differs across policies/scenarios within a seed**; p10/worst/mean recall computed only over eligible held-out samples |
| `scripts/phase10/preflight_real_data.py` | real-data (UNSW **training** file only, guard active) preflight |
| `scripts/phase10/build_phase10.py` | manifest v2 with an `amendment` block |

## What changed in data assignment
Per-seed holdout is global and group-wise, ≈20 % of rows (seed 24: 20.4 % after closure); it is identical for all 8 arms of a seed (policy/scenario do not enter the data path). Preprocessor fits on ≈120 k rows; one-hot dimension is 192-194 depending on the seed (as before). Training rows per client fall by the holdout; partitions (Dirichlet) are computed on all rows exactly as before. Real-data preflight (seeds 22-26): holdout group-disjoint from training rows in group and encoded space, deterministic, identical across arms, min client training rows 74-82, eligible clients 41-45 per seed (`preflight_real_data.json`).

## Manifest
v1 (superseded, kept as provenance): `docs/phase10/EXPERIMENT_MANIFEST_v1_SUPERSEDED.json`, sha256 `692630219a758854…`. v2: `docs/phase10/EXPERIMENT_MANIFEST.json`, sha256 `98ee98319055a835…` (final v2 after a metrics-script fix found by the tests; new code fingerprint; same 40 runs, seeds 22-26, policies, ρ=0/0.8, H1-H4). Hypotheses, policies, scenarios, seeds and hyper-parameters unchanged; nothing tuned on outcomes.
