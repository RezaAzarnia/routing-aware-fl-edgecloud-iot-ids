# Final-test evaluation plan, frozen v2 (supersedes Phase 9 draft; NOT EXECUTED, not authorized)

Status: **FROZEN AS A PROPOSAL.** It becomes executable only after (i) the readiness conditions R1-R8 below are met and (ii) the project owner signs the authorization file required by the evaluation script. No test data, test-set statistic or hypothetical test result is used anywhere in this plan or in the manuscript.

## 1. Models, seeds, checkpoints (exact scope)
* **Primary set (P):** the 240 completed Phase 6C runs (24 arms × seeds 12-16 × {UNSW-NB15, CICIoT2023}); for each run both `best_model_state.pt` (round recorded in `final_validation_metrics.json::best_round`, chosen on the selection partition) and `last_model_state.pt` (round 30). SHA-256 of every checkpoint file and `preprocessor.joblib` is recorded in each run's `COMPLETE.json` and re-verified before use.
* **Secondary set (S, optional, separate manifest):** the 40 mandatory Phase 7b UNSW-NB15 runs (8 arms × seeds 17-21), same rules.
* No retraining, no new seed, no checkpoint other than the two named per run, no arm excluded after the fact. The unrun Phase 8 variant (`p8_corrected_gaussian_groupcap`) is **excluded** (it has no validated checkpoints).

## 2. Frozen procedures
* **Checkpoint rule:** best = recorded `best_round` (no re-selection); last = round 30. Both reported for every run.
* **Threshold rule:** the thresholds already stored in the run records, all chosen on the calibration partition (objective `fpr_cap`, FPR ≤ 0.15, recall ≥ 0.6, ties by F1, balanced accuracy, closeness to 0.5): `selected_operating_point.threshold` (best), `last_round_selection_partition.threshold` (last), and the three operating points `threshold_diagnostics.{1pct,5pct,15pct}.calibration_partition.threshold`. Post-hoc audit showed recomputed thresholds equal the recorded ones for the audited checkpoints (differences ≤4e-3 are float noise); recorded values are used. No threshold is recomputed or re-optimised with test data.
* **Preprocessing:** the training-fitted preprocessor, loaded from the hash-verified `preprocessor.joblib` (or, if refitted, proven identical on the validation partition *before* the test file is opened).
* **Decision rule:** `score >= threshold` on raw probabilities (repaired `src/metrics.py`); AUC on raw scores.

## 3. Metrics and analyses (declared before execution)
* Per (dataset, arm, seed, checkpoint): ROC-AUC, PR-AUC, F1, recall (attack detection rate), precision, FPR, specificity, confusion matrix at each frozen threshold; the FPR shift (test − calibration).
* Aggregation: mean ± SD over 5 seeds, per-seed values, no omissions.
* **Primary contrasts (paired by seed, exploratory, n=5, exact sign-flip p, t-CI):** (1) Reference − clean FedAvg; (2) Reference − undefended FedAvg top-k; (3) Corrected − Reference; (4) Reference_gaussian − Reference. Secondary: ablation `ctl_*` vs Reference; 30%-failure and natural-attacker arms; Phase 7b guard contrasts if set S is run.
* **Operational flag declared in advance:** test FPR at the primary threshold above 0.25 is reported as a failure of the validation-calibrated threshold policy (not repaired).
* No multiplicity correction; every inference exploratory; minimum exact p = 0.0625.
* **Overlap-controlled sensitivity analyses (descriptive, not selecting):** UNSW-NB15 — the subset of test rows whose predictor vector does not occur in the official training file (73,791 of 82,332 rows; 8,541 test rows, 10.4 %, are predictor-identical to training rows, 524 of them with a conflicting binary label; `docs/data_integrity/unsw_overlap_audit.json`); CICIoT2023 — the subset of unique feature vectors within the test file (242,854 unique of 300,000 rows; 57,146 duplicate-feature rows; zero predictor-vector overlap with train or validation; `docs/data_integrity/audit_prepared_verified_v2_filegroup.json`).

## 4. Provenance limitations that must travel with the results
* UNSW-NB15: official train/test files differ in label mix and carry duplicate/conflicting records; ~10 % of test rows share the predictor vector with training rows.
* CICIoT2023: prepared files are byte-equivalent to a third-party release; official provenance unverified; labels inferred from file/class folder names; no device identifiers (capture-group, not device, holdout); benign prevalence 53.9 % (train) / 3.2 % (validation) / 2.35 % (test) — extreme prior shift, so precision, F1 and FPR must be read with confusion matrices; AUC ceiling ≈0.996.
* The same simulated network trace underlies both datasets.
* The locked test files were read by earlier integrity audits and unit tests (see `LASTACCESSTIME_FORENSICS.md`); they were never used for modelling.

## 5. Readiness conditions (all must be true; currently FAIL)
| # | Condition | Status |
|---|---|---|
| R1 | Evaluation script revised: repaired metric environment, new final-test manifest/fingerprint on a frozen commit (audit B1) | OPEN |
| R2 | Preprocessor equality verified before test is opened (B2) | OPEN |
| R3 | Output directory `results_final_test/` outside historical results (B3) | OPEN |
| R4 | CIC within-test overlap-controlled subset and analysis script written and frozen (B5, B6) | OPEN |
| R5 | Locked-file access control/auditing in place; data-reading unit tests no longer open the locked files (forensics) | OPEN |
| R6 | Manuscript blockers M1-M6 closed or consciously deferred (see `PUBLICATION_READINESS.md`) so that the paper does not change after seeing results | OPEN |
| R7 | Owner signs the authorization file for the new manifest hash | OPEN |
| R8 | Frozen commit + tag created and recorded; `--dry-run` passes | OPEN |

## 6. Exact one-time procedure (after R1-R8)
1. Tag the frozen commit `final-test-eval-v1`; write the new manifest (run list, checkpoint/preprocessor hashes, thresholds, test-file hashes, evaluation-tree fingerprint).
2. `python scripts/final_test/evaluate_saved_checkpoints.py --dry-run` (reads no test data).
3. Execute once with the signed authorization. Infrastructure-only failure ⇒ repair the failing infrastructure and restart from scratch with a disclosure; any content-dependent change after seeing a number is forbidden.
4. Run the frozen analysis script; add a "Final-test results" section; do **not** alter any validation-based statement.
5. Record consumption of the test data; no further tuning on it.

## 7. Expected output artifacts
`results_final_test/{dataset}/{arm}/seed_{s}/final_test_result.json` (exclusive-create), `results_final_test/ledger.jsonl` (result hashes), `final_test_manifest.json`, `ledger_final_test_per_run.csv`, `ledger_final_test_arm_summary.csv`, `ledger_final_test_paired_contrasts.csv`, `ledger_fpr_shift.csv`, `ledger_overlap_controlled.csv`, `final_test_report.md` (all arms, favourable or not), and a regenerated figure/table set kept separate from the validation ones.
