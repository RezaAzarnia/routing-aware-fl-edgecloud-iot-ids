# Static, read-only audit of `scripts/phase6c/final_test_evaluate.py` (205 lines)

Method: source reading only; the script was **not executed**, no `--dry-run` either, and no test file was opened. Related code read: `src/data.py` (`load_dataset`, `load_and_preprocess_unsw/ciciot2023`, `_split_calibration_protocol`, `_sanitize_frame`), `scripts/phase6c/orchestrator.py` (`preflight`, `run_status`), `scripts/phase6c/p6c_common.py`, `tests/test_phase6c_final_test.py`.

## A. What the script guarantees (verified in code)
| Property | Evidence in code | Verdict |
|---|---|---|
| No test-based tuning of thresholds | thresholds are taken from the run record: `best_thr = fin["selected_operating_point"]["threshold"]`, `last_thr = fin["last_round_selection_partition"]["threshold"]`, `targets = {k: v["calibration_partition"]["threshold"]}`; all written before any test access (calibration partition) | PASS |
| No checkpoint selection on test data | checkpoints are fixed files `best_model_state.pt` / `last_model_state.pt` (hashed into the result: `checkpoint_sha256`); no loop over rounds or models | PASS |
| No fitting on test data | `load_dataset(..., load_test=True)`: the preprocessor is `fit_transform(train_features)` only (`src/data.py` ~l.350, ~l.528); test goes through `transform`; `_sanitize_frame` is element-wise (inf→NaN), no statistic computed from test | PASS |
| No test-derived split | `enable_calibrated_evaluation: false` in every resolved config ⇒ `_split_calibration_protocol` returns `raw_test` unchanged (`src/data.py` l.213-215); `max_test_samples: null` ⇒ no subsampling | PASS |
| Test labels used only for metrics | `y = bundle.y_test` → `metrics_at(y, prob, fixed_threshold)` and the duplicate-controlled subset; no optimisation | PASS |
| One-time, no overwrite | `open(result_path, "x")` (exclusive create), per-run existing result ⇒ skipped, append-only `ledger.jsonl` with result hashes | PASS |
| Authorization gate | requires an authorization JSON naming this manifest hash, the exact statement, `authorized_by`, and the no-retuning acknowledgement; otherwise exit code 2 | PASS |
| Preconditions | manifest hash verified (`load_manifest`), code fingerprint equals manifest, every run `verified`, test-file SHA-256 equals the manifest value, no prior result | PASS |
| No hidden data access before authorization | order in `main()`: template/refuse → authorization check → fingerprint → run status → `--dry-run` exit → `test_file_problems` (the first function that reads test file content, via `sha256_file` / `sha256_gzip_content`) → `load_dataset(..., load_test=True)` | PASS (first test read happens only after authorization) |
| Dry-run reads no test data | returns before `test_file_problems`; unit test `test_phase6c_final_test.py` deletes the test CSV and checks the dry run still passes | PASS |

## B. Defects / blockers found (none is a leak; several make the script unfit to run as is)
| # | Finding | Severity | Required action |
|---|---|---|---|
| B1 | **Metric code mismatch.** `metrics_at` calls `src.metrics.binary_classification_metrics` from whatever tree is checked out. The fingerprint gate forces the **Phase 6C code tree** (`CODE_GLOBS` includes `src/*.py` and this script) — on the present branches (`src/` changed in Phase 7b/8) the script would **REFUSE**; on the Phase 6C tag it would run the **defective metric** (clipping before thresholding ⇒ a threshold of exactly 1.0 predicts nothing, artificial AUC ties). | **Blocker** | New final-test manifest/fingerprint on a frozen commit that contains the repaired metric; or an explicitly documented evaluation with audited metrics. |
| B2 | **Preprocessor re-fit, not loaded.** The script rebuilds the data bundle (refitting the preprocessor on the training rows) instead of loading the saved `preprocessor.joblib`. Equality with the preprocessor used in training is assumed, not checked. | Major | Before any test read: refit on training data (no test) and verify equality with the hash-recorded saved preprocessor (e.g., transformed validation-partition matrix identical to the stored one); abort if not. |
| B3 | **Output location.** Writes to `results_phase6c/_final_test/`, inside the historical results tree whose immutability is a stated project rule. | Moderate | Write to a new top-level `results_final_test/`. |
| B4 | **Scope.** The manifest covers only Phase 6C (240 runs). Phase 7b runs (new seeds 17-21, repaired metric) are outside it. | Moderate | Decide scope in the frozen plan; if included, a separate 7b manifest. |
| B5 | **Overlap control only for UNSW-NB15**, and only as predictor-vector set membership (`duplicate_controlled`); none for CICIoT2023 (whose test has 57,146 feature-only duplicate rows inside itself and zero predictor-vector overlap with train/validation per the audit). | Moderate | Add CIC within-test duplicate-controlled subset (unique feature vectors) as a pre-declared descriptive analysis. |
| B6 | No analysis script (paired statistics, FPR shift); the script only emits per-run JSON. | Moderate | Write and freeze the analysis script before authorization; same statistics as the validation ledgers. |
| B7 | Metrics from `binary_classification_metrics` include a clipped-loss; AUC is on raw scores (after repair). Fine, but PR-AUC/ROC-AUC tie handling should be stated. | Minor | State in plan. |
| B8 | Torch `load_state_dict(torch.load(path))` without `weights_only=True`. | Minor | Use `weights_only=True` or `map_location="cpu"`; hash already recorded. |
| B9 | The script reads the training/validation data again per `(dataset, seed)` (necessary for the preprocessor). Reading the 926k-row CIC training file ×5 is slow but not a defect. | Info | — |

## C. Verdict
The script contains **no test-based tuning, fitting, threshold optimisation, checkpoint selection or hidden early access**. It is nevertheless **not ready to execute** because of B1 (defective or refused metric environment) and B2 (unverified preprocessor equality); B3-B6 should be fixed in the same revision. These changes touch only an evaluation script, not training algorithms.
