# Safe execution plan for the one-time final-test evaluation (plan `final-test-eval-v2`) — NOT EXECUTED, NOT AUTHORIZED

Supersedes `Phase9B_Review/FINAL_TEST_PLAN_FROZEN_v2.md` (scope, statistics and limitations unchanged; this document fixes the exact mechanics). Nothing here may be run without the owner's explicit decision. No hypothetical test result is used anywhere.

## 1. Frozen inputs
* Manifest: `docs/final_test/FINAL_TEST_MANIFEST.json` (280 runs: 240 Phase 6C seeds 12-16 + 40 Phase 7b mandatory UNSW seeds 17-21; best and last checkpoints; recorded calibration-partition thresholds; preprocessor and checkpoint SHA-256; evaluation-code fingerprint; training-code lineage = git tags `phase6c-final-results`, `phase7b-final-results`). Its hash is printed by `python scripts/final_test/final_test_v2.py readiness`.
* The unrun Phase 8 variant is excluded. The optional, never-run CIC tier of Phase 7b is excluded.
* Locked-file descriptors (path, kind, SHA-256 or content SHA-256, rows) are copied from the Phase 6C manifest; the files have not been opened to create them.

## 2. Pre-conditions the owner must settle first
R6 (manuscript decisions M1-M6 closed or consciously deferred; no manuscript change after seeing results), R7 (signature below), and the OS-level recommendation: enable Windows object-access auditing on the three protected paths (or move them to an access-controlled location) so that any further read is recorded.

## 3. Exact commands (PowerShell; `$PY` = the project's Python)
```powershell
# a) no test data is read in any of these steps
& $PY scripts\final_test\final_test_v2.py readiness      --out Phase9C_Submission_Readiness\evidence\readiness_R1_R8.json
& $PY scripts\final_test\final_test_v2.py preproc-equiv  --out Phase9C_Submission_Readiness\evidence\preprocessor_equivalence.json
& $PY scripts\final_test\final_test_v2.py evaluate --preflight          # everything except the signature
& $PY -m pytest tests -q --basetemp=C:/cs/pt                             # locked-file tests are deselected; guard active
# b) owner only: create and sign the authorization
& $PY scripts\final_test\final_test_v2.py authorization-template --out C:\secure\final_test_authorization.json
#    set authorized=true, copy required_statement into statement, fill authorized_by,
#    acknowledge_no_retuning_after_test=true, acknowledge_prior_integrity_reads_disclosed=true
& $PY scripts\final_test\final_test_v2.py evaluate --dry-run --authorization C:\secure\final_test_authorization.json
# c) the one-time evaluation
& $PY scripts\final_test\final_test_v2.py evaluate --authorization C:\secure\final_test_authorization.json
# d) frozen analysis (reads result JSONs only)
& $PY scripts\final_test\analyze_final_test.py --results results_final_test --out results_final_test\ledgers
```
Environment note: authorised integrity tests that read locked files run only as `IOTFL_AUTHORIZED_FINAL_TEST_INTEGRITY=1 pytest -m authorized_integrity -o addopts=""` and open files only inside `guard.authorized(...)`.

## 4. What the evaluation does (and cannot do)
1. Refuses unless: authorization valid for this manifest hash and plan; manifest unmodified; evaluation-code fingerprint equals the frozen one; source manifests unchanged and git-tag lineage matches; every run re-verifies; output directory is new/empty and outside `results_phase*`.
2. Installs the access guard; reads each locked file **once** inside `authorized(...)`, hashes the (decompressed) content against the locked hash, parses from the same bytes.
3. For each run: re-checks checkpoint/preprocessor hashes, loads the saved preprocessor, verifies column schema, transforms, predicts with the best and last checkpoints, and applies only the recorded thresholds (primary + three calibration operating points).
4. Writes `results_final_test/{dataset}/{arm}/seed_{s}/final_test_result.json` (exclusive create) and `test_probabilities.npz`, plus an append-only `ledger.jsonl` with result hashes. No code path searches thresholds, selects checkpoints, fits transformers or retries after seeing results.
5. Result schema `final_test_result_v2`: `run_id, dataset, arm, seed, best_round, checkpoint_sha256{best,last}, preprocessor_sha256, thresholds_from_calibration_partition, calibration_reference{fpr,recall,constraint_feasible}, test_rows, test_benign, best{primary,targets{1pct,5pct,15pct}}, last{primary}, overlap_controlled{not_in_reference, unique_within_test, not_in_reference_and_unique}{rows,best_primary,last_primary}, final_test_manifest_sha256, evaluated_utc`; each metric block holds `threshold, tp, fp, fn, tn, roc_auc, pr_auc, f1, precision, recall_adr, fpr, specificity, accuracy, balanced_accuracy, loss`.
6. Expected analysis artifacts: `ledger_final_test_{per_run,arm_summary,paired_contrasts}.csv`, `ledger_fpr_shift.csv` (test minus calibration FPR; flag > 0.25 reported as a threshold-policy failure), `ledger_overlap_controlled.csv`. Primary contrasts (n=5, exploratory, minimum exact p 0.0625): Reference − clean FedAvg; Reference − undefended FedAvg top-k; Corrected − Reference; Reference+Gaussian − Reference.

## 5. Failure handling
An infrastructural failure before any result is written ⇒ fix only the infrastructure, re-freeze (new manifest hash), disclose, restart. After the first result file exists, no re-run is permitted (exclusive-create); a content-dependent change after seeing a number is forbidden.

## 6. Disclosure to carry into the paper
The test files were opened earlier by data-integrity audits and unit tests (hashes, row counts, duplicate/overlap and label-consistency counts) but never for modelling; since Phase 9C ordinary test runs cannot open them; provenance of the CICIoT2023 prepared files is unverified; overlap-controlled subsets are descriptive.
