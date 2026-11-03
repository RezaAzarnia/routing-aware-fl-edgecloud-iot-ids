# Final-test evaluation protocol (PROPOSED; NOT EXECUTED; requires explicit authorization)

Status: the UNSW-NB15 testing CSV and the CICIoT2023 `test.csv.gz` (prepared test split) have **not** been loaded, inspected, evaluated or used for tuning in any phase. All 240 + 40 runs are `validation_only` with `test_csv: ''`.

## 0. Preconditions (must all hold before the one-time evaluation)
1. Written authorization from the project owner naming this protocol.
2. **Resolve the access-time anomaly**: Phase 6C recorded that `LastAccessTime` of the locked test files was newer than their preparation time (cause not established; no config references them; `run_one.py` asserts `test_csv==""`). Check indexer/antivirus/backup activity first and record the finding. If a read by project code cannot be excluded, the owner decides whether the files are still "locked" (a disclosure sentence must then appear in the paper).
3. Record SHA-256 of both test files and compare with `docs/data_integrity/historical_data_hashes.json` and the manifest content hashes **without opening them for modelling** (hashing is not a modelling read, but must itself be logged).
4. Freeze: git commit of the evaluation script and this plan; no code change afterwards.

## 1. Frozen implementation
- Code state: `phase7b-final-results` metric logic (single decision rule `score >= threshold` in `src/metrics.py`); the Phase 8 `preserve_surrogate_cap` flag stays off (no run used it).
- Models: the **saved checkpoints** of the Phase 6C runs (`best_model_state.pt`, `last_model_state.pt`, `preprocessor.joblib`, seeds 12-16, both datasets) and, if desired, Phase 7b runs. **No retraining** and no new seed.
- Primary arms: `reference`, `corrected`, `clean_fedavg`, `scenario_fedavg_topk`; secondary: `fail0p3_reference`, `fail0p3_corrected`, `reference_gaussian`, `corrected_gaussian`, the `ctl_*` ablations. All arms are evaluated and reported, favourable or not.

## 2. Frozen selection, calibration and threshold procedures
- Checkpoint: the round chosen on the **selection** partition (already recorded as `best_round`); last round reported alongside. No re-selection.
- Threshold: the value already chosen on the **calibration** partition under objective `fpr_cap` (FPR ≤ 0.15, recall ≥ 0.6). Re-use the recorded threshold; no re-optimisation on test data. Additional operating points (calibration FPR targets 1% and 5%, already stored in `threshold_diagnostics.json`) are applied unchanged.
- Preprocessing: the stored fitted `preprocessor.joblib` (training-fitted), applied via `transform` only.

## 3. Primary metrics and comparisons (declared in advance)
- Per arm and seed: ROC-AUC, PR-AUC, F1, recall (attack detection rate), FPR, precision, full confusion matrix at the frozen threshold; best and last.
- Primary contrasts (paired by seed, n=5, exploratory): Reference − clean FedAvg; Reference − undefended FedAvg top-k; Corrected − Reference; Gaussian cost; Phase 7b arms only if requested.
- Primary question about transfer: does the validation-calibrated FPR (~0.15) hold on test data? Report FPR shift (test − calibration) per arm and per seed; do not "fix" it.
- Success criteria: none are chosen to favour a method; the paper reports whatever occurs. Pre-declared flag: test FPR > 0.25 is reported as an operational failure of the threshold policy.

## 4. Known provenance limitations to carry into the report
UNSW-NB15: official test set has a different benign/attack mix and known label/feature caveats; predictor-vector overlap with training was audited in `docs/data_integrity/unsw_overlap_audit.json`. CICIoT2023: files byte-equivalent to a third-party release, official provenance unverified; no device holdout; benign prevalence 2.35% in the test file (3.2% validation, 53.9% training), so precision, F1 and FPR are dominated by prior shift and must be read with the confusion matrices; AUC ceiling means arms cannot be separated. The same network trace underlies both datasets.

## 5. Exact one-time procedure
1. Create branch `final-test-eval-v1` from the frozen commit; create `results_final_test/` (new, empty).
2. Run `scripts/final_test/evaluate_saved_checkpoints.py` (to be written **before** authorization and committed, not run): loads test CSV once per dataset, applies each stored preprocessor, loads checkpoints, computes the metrics above with the recorded thresholds, writes one JSON per (dataset, arm, seed) and a manifest with hashes, timestamps and the command line.
3. Execute once. If it fails for an infrastructural reason, repair only the infrastructure and re-run from scratch with a disclosure; never re-run after seeing results to change a choice.
4. Generate the tables with the same ledger scripts (new final-test ledger, original/audited kept separate), then update the manuscript section "Final-test results" without changing any validation result.
5. Re-lock: record that the test data were consumed; no further tuning is permitted on them.

## 6. Not allowed
Using test data for model selection, threshold, hyper-parameters, seeds, arms or claims; evaluating subsets chosen after seeing results; evaluating the unrun Phase 8 variant on test data before it is validated on fresh validation seeds.

## 7. Existing script warning
`scripts/phase6c/final_test_evaluate.py` already exists in the repository. It was **not** run or inspected for execution in Phase 9. Before authorization it must be reviewed against sections 1-3 (frozen thresholds, saved checkpoints, no re-optimisation); either adapt it into `scripts/final_test/evaluate_saved_checkpoints.py` or document why it is used as is.
