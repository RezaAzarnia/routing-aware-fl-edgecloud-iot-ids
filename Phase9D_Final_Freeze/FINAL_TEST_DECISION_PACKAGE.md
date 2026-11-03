# Final-test decision package (for the project owner; one page of decisions)

**Decision status: NOT READY — technically prepared; two items require the owner (R6 manuscript/decision freeze, R7 signature). The final test has NOT been executed and no locked test file was opened in Phase 9D.**

## 1. What a final test would add (scientific benefit)
* The only evidence on **generalisation to the official test distributions** (UNSW-NB15 testing set; CICIoT2023 test split), which all current results lack.
* The only evidence on **threshold transfer**: validation-calibrated thresholds fix FPR ≈ 0.15 by construction; the test shows whether that holds (the earlier manuscript reported much higher test FPR for some configurations; this is untested here).
* Answers the first question reviewers of an IDS paper will ask; removes the "validation-only" limitation from the title/abstract framing.
* Overlap-controlled subsets (UNSW: ≈ 10.4 % of test rows share the predictor vector with training rows; CIC: 19 % duplicate-feature rows inside the test file) quantify how much of any test result is due to duplication.

## 2. What publishing validation-only results costs (limitation)
No generalisation or FPR-transfer claim is possible; the study must be framed as a controlled *simulation measurement* study, with the validation-only protocol, n=5, and one simulator as stated limits. It is honest and internally complete, but weaker for venues that expect test-set evaluation. The final test cannot be repeated after its use: it is a one-time asset.

## 3. Exact frozen primary comparisons
Primary tier = reference, clean_fedavg, scenario_fedavg_topk, corrected, reference_gaussian × {UNSW-NB15, CICIoT2023} × seeds 12-16, best checkpoint, primary threshold (50 runs); contrasts (1) reference − clean_fedavg, (2) reference − scenario_fedavg_topk, (3) corrected − reference, (4) reference_gaussian − reference; metrics ROC-AUC, F1, recall, FPR; flag: test FPR > 0.25 reported as a threshold-policy failure. Secondary: the other 19 arms, last checkpoints, operating points 1/5/15 %, overlap-controlled subsets. Exploratory: 40 Phase 7b runs. Full list: `MANIFEST_AND_PREPROCESSING_AUDIT.md` and `evidence/final_test_run_tiers.csv`. No post-test selection or selective reporting is possible: the manifest is hash-frozen, all 280 runs are evaluated and reported, results are write-once.

## 4. Models, checkpoints, preprocessing compatibility
280 runs / 560 checkpoints (best at the recorded `best_round`, last at round 30) with recorded calibration-partition thresholds; saved training-fitted preprocessors **loaded, never refitted**; 15/15 (dataset, seed) pairs verified identical to a training-only refit and all 280 saved preprocessors equal their pair's; strict state-dict load and dimension checks pass for all 560 checkpoints (`evidence/readiness_R1_R8.json`, `preprocessor_coverage_15_pairs.json`).

## 5. Expected outputs and statistics
`results_final_test/{dataset}/{arm}/seed_{s}/final_test_result.json` (+ `test_probabilities.npz`), `ledger.jsonl`; then `analyze_final_test.py` → per-run, arm-summary, paired-contrast (mean, SD, t-CI, wins, exact sign-flip p; n=5 ⇒ min p 0.0625; exploratory; no multiplicity correction), FPR-shift and overlap-controlled ledgers. Schema and commands: `Phase9C_Submission_Readiness/FINAL_TEST_SAFE_EXECUTION_PLAN.md`.

## 6. Data-leakage safeguards
Two-fingerprint integrity gate (frozen evaluation code + git-tag training lineage), signed authorization bound to the manifest hash and plan, exclusive-create outputs outside all historical results trees, AST-tested absence of any fit/threshold search/checkpoint selection, saved-preprocessor schema check, runtime access guard (locked files can be opened only inside `authorized(...)`; ordinary test runs cannot open them), `--preflight` and `--dry-run` that read no test data. Disclosure retained: the locked files were opened earlier by data-integrity audits and unit tests (hashes, row counts, duplicate/overlap and label-consistency counts), never for modelling; timestamps are consistent with that and cannot prove otherwise.

## 7. R1-R8 status (evidence in `Phase9C_Submission_Readiness/FINAL_TEST_READINESS_REPORT.md`)
| R | Status |
|---|---|
| R1 evaluation script, two fingerprints, repaired metrics | **PASS** |
| R2 preprocessor equivalence before test is opened (now 15/15 pairs, 280/280 runs) | **PASS** |
| R3 outputs outside historical trees | **PASS** |
| R4 overlap control for both datasets; frozen analysis and schema | **PASS** |
| R5 locked-file access control (software); OS-level auditing recommended | **PASS (software)** |
| R6 manuscript/decisions frozen (M1-M6) | **OPEN — requires authors** |
| R7 owner's signed authorization | **OPEN — requires owner** |
| R8 final tag + signed dry-run | **OPEN** (preflight passes; the tag and signed dry-run follow the owner's decision) |

## 8. Decision
**NOT READY** until R6, R7 and R8 are completed. **GO condition:** the authors decide to include test evidence, finish M1-M4, the owner signs the authorization for manifest `737b901f…`, a final tag is created and `evaluate --dry-run` passes. **Alternative (also legitimate):** submit as a validation-only measurement study and keep the test files locked.

## 9. What the owner must decide
(a) Run the final test, or publish validation-only. (b) If run: sign the authorization (statement + acknowledgements) and enable OS-level file auditing. (c) Agree that no manuscript change follows the test result except adding the final-test section.
