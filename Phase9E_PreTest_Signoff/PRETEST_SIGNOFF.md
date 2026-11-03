# Pre-test sign-off: frozen evaluation decisions (plan `final-test-eval-v2`)

Status: **frozen proposal for the owner's authorization. No final-test evaluation has been executed; no locked test file was opened, hashed, sampled or inspected in Phases 9C, 9D or 9E.** Nothing in this document depends on, or anticipates, any test result.

## 0. Pre-definition evidence (primary hypotheses and comparisons exist before any test evaluation)
* The four primary contrasts and the tier definitions were committed in `docs/final_test/FINAL_TEST_MANIFEST.json` at commit `cdd21ea` (2026-11-03 15:24 +03:30) and the file has not changed since (`git log` shows that single commit); the tiers and expected signs below were committed in `f2a3523`/this phase's commit, also before any evaluation.
* `results_final_test/` does not exist; the three protected files' last-access times (08:45:48Z, 08:45:49Z, 08:45:51Z) are unchanged after all Phase 9C-9E activity (`Phase9D_Final_Freeze/evidence/locked_file_access_times_after_9D.txt`; re-checked in 9E).
* Frozen manifest: sha256 (canonical) `737b901f26ae66cc…`; evaluation-code fingerprint `8ed4a8fe8e8fc835…`; manifest file bytes sha256 `c0f3b3d75b22a271…`.

## 1. What is evaluated: 280 runs, three tiers (full list with hashes: `PRETEST_RUN_TABLE.csv`)
| Tier | Definition | Runs |
|---|---|---|
| **Primary (50)** | Phase 6C arms `reference`, `clean_fedavg`, `scenario_fedavg_topk`, `corrected`, `reference_gaussian` × {UNSW-NB15, CICIoT2023} × seeds 12-16 | 50 |
| **Secondary (190)** | the other 19 Phase 6C arms × 2 datasets × seeds 12-16: clean_centralized, corrected_gaussian, ctl_delivery_coupled, ctl_imputation_cap010, ctl_imputation_none, ctl_imputation_postfilter, ctl_momentum0_lr0p5, ctl_momentum0_lr5p0, ctl_selection_coverage, ctl_selection_uniform, ctl_weighting_uniform, fail0p0_reference, fail0p3_corrected, fail0p3_reference, nat_corrected, nat_reference, nat_selection_uniform, robust_random_no_imputation, scenario_fedavg_random | 190 |
| **Exploratory (40)** | Phase 7b UNSW-NB15 arms (reference, corrected, p7_corrected_guard, fail0p3_reference, fail0p3_corrected, fail0p3_p7_corrected_guard, ctl_delivery_coupled, p7_delivery_guard) × seeds 17-21 | 40 |
No other run, arm, seed, checkpoint, dataset or subset can be added; the unrun Phase 8 variant and the unrun CIC tier of Phase 7b are excluded.

## 2. Frozen identities and selection rules
* **Checkpoints (2 per run, 560 total):** `best_model_state.pt` = the round recorded as `best_round`, chosen long before any test on the **selection partition** by maximum ROC-AUC; `last_model_state.pt` = round 30. SHA-256 of both and of the saved training-fitted `preprocessor.joblib` are in `PRETEST_RUN_TABLE.csv`; all are re-verified before use. No other checkpoint exists or can be used; there is no re-selection.
* **Thresholds:** recorded calibration-partition values (objective `fpr_cap`: FPR ≤ 0.15, recall ≥ 0.6): primary = `selected_operating_point.threshold` (best checkpoint) and `last_round_selection_partition.threshold` (last checkpoint); additional operating points = calibration thresholds for FPR targets 1 %, 5 %, 15 % (best checkpoint). **No threshold is recomputed, re-optimised or adjusted on test data.** Four runs have an *infeasible* calibration constraint and therefore use the recorded fallback threshold; they are flagged in the output and reported as such: UNSW `scenario_fedavg_topk` seed 14 (primary), UNSW `scenario_fedavg_random` seeds 14 and 16 (secondary), UNSW `fail0p3_corrected` seed 17 (exploratory).
* **Preprocessing:** the saved preprocessor is loaded, never refitted; 15/15 (dataset, seed) pairs equal a training-only refit and all 280 saved preprocessors equal their pair's (`Phase9D_Final_Freeze/evidence/preprocessor_coverage_15_pairs.json`).
* **Decision rule:** `score >= threshold` on raw probabilities (repaired `src/metrics.py`).

## 3. Pre-registered hypotheses and endpoints
**Primary endpoint:** ROC-AUC at the **best checkpoint** and primary threshold, per (dataset, arm, seed). **Co-reported descriptive metrics** for every run: F1, recall (attack detection rate), precision, FPR, confusion matrix, PR-AUC; FPR shift = test FPR − calibration FPR.
**Primary comparisons (4 contrasts × 2 datasets = 8; paired by seed, n = 5; Δ = first − second):**
| # | Contrast | Expected direction (declared from validation evidence, before any test result) |
|---|---|---|
| P1 | reference − clean_fedavg | Δ ≈ 0 (validation: −0.0005 UNSW, +0.0001 CIC) |
| P2 | reference − scenario_fedavg_topk | Δ > 0 (undefended attack arm) |
| P3 | corrected − reference | Δ ≤ 0 (validation: −0.0082 UNSW, −0.0003 CIC) |
| P4 | reference_gaussian − reference | Δ < 0 (validation: −0.0419 UNSW, −0.0032 CIC) |
These are directional expectations, not pass/fail success criteria: the report states, for each, whether the observed sign agrees, with mean difference, SD, 95 % t-interval, wins and exact p. **Operational flag (pre-declared):** test FPR > 0.25 at the primary threshold of any primary-tier run is reported as a failure of the validation-calibrated threshold policy; it is not repaired.
**Secondary:** every other metric, last-round checkpoints, the three operating points, secondary contrasts (pre-declared list, computed with the same `contrasts_table` function and a fixed pair list, no new analysis code): each of the ten `ctl_*` arms − reference; nat_corrected − nat_reference; fail0p3_corrected − fail0p3_reference; corrected_gaussian − corrected; corrected_gaussian − reference_gaussian; reference − scenario_fedavg_random; and overlap-controlled subsets (UNSW: test rows whose predictor vector is absent from the official training file; CIC: absent from train/validation; both: unique within test; descriptive). **Exploratory:** the 40 Phase 7b runs, reported in full without inferential weight.

## 4. Statistical procedure (identical to the validation ledgers; implemented in `scripts/final_test/analyze_final_test.py`)
Per arm: mean ± SD and every per-seed value. Per contrast: paired differences, t-based 95 % interval (df = 4), number of seeds favouring each arm, exact two-sided sign-flip permutation p. **Multiple comparisons:** no correction is applied; with n = 5 the smallest attainable exact two-sided p is 0.0625, which exceeds any adjusted threshold (Bonferroni/Holm for 8 primary comparisons: 0.05/8 = 0.00625), so **no comparison can be declared statistically significant under any correction and all inference is exploratory**; raw p-values are reported with that statement. Validation of the pipeline (this phase): `Phase9E_PreTest_Signoff/evidence/analysis_validation_dryrun.json` — the frozen analysis, fed pseudo-results built from audited **validation** metrics of the 50 primary runs, reproduces the independent validation ledger in 24/24 comparisons.

## 5. Best versus last: no favourable selection after testing
Both checkpoints are evaluated for every run and **both are reported in the same tables for every arm** (best and last AUC, F1, recall, FPR, with collapse counts for last). The **primary** statements use the best checkpoint (declared above). The last-round result is never substituted, averaged away or dropped; if best and last disagree in direction for a primary contrast the text reports both. No per-run or per-arm choice between best and last is made.

## 6. Provenance and leakage controls (all tested; see `FINAL_TEST_DECISION_PACKAGE.md`, rehearsal test `tests/test_phase9e_rehearsal.py`)
Two-fingerprint integrity gate, signed authorization bound to the manifest hash, refusal on any mismatch, locked files readable only inside `authorized(...)`, exclusive-create outputs in a new directory, no `fit`/threshold search/checkpoint selection code (AST test), hash check of the locked files **before** any prediction, saved-preprocessor schema check, write-once results (a second run is refused), preflight/dry-run reading no test data. Disclosure retained: the locked files were opened earlier by data-integrity audits and unit tests (never for modelling).

## 7. Limits that will accompany the results
UNSW test: ≈ 10.4 % of rows share a predictor vector with training rows (524 conflicting labels); CICIoT2023: prepared files byte-equivalent to a third-party release (provenance unverified), no device holdout, benign prevalence 53.9 % (train) / 3.2 % (validation) / 2.35 % (test), 19 % duplicate-feature rows inside the test file, AUC ceiling; one simulated network trace shared by both datasets; n = 5.

## 8. Sign-off record
| Item | Value |
|---|---|
| Prepared by | AI coding assistant (Claude Code), at the project owner's request; **not a signature** |
| Owner / authors' approval of this sign-off | **OPEN (R7)** — `[OWNER NAME, DATE — to be entered by the owner]` |
