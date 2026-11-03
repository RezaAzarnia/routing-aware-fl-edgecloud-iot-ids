# The 280-run manifest and the preprocessing audit (Phase 9D)

## 1. Why 280 runs
`docs/final_test/FINAL_TEST_MANIFEST.json` (sha256 `737b901f26ae66cc…`) lists every run whose final-test evaluation is frozen:

| Source | Datasets | Arms × seeds | Runs |
|---|---|---|---|
| Phase 6C (main experiment) | UNSW-NB15, CICIoT2023 | 24 arms × seeds 12-16 × 2 datasets | **240** (120 + 120) |
| Phase 7b follow-up, mandatory tier | UNSW-NB15 only | 8 arms × seeds 17-21 | **40** |
| **Total** | | | **280** (560 checkpoints: best + last per run) |
The optional CICIoT2023 tier of Phase 7b was never run and is excluded; the unrun Phase 8 variant is excluded. Each run contributes exactly two frozen checkpoints and the recorded calibration-partition thresholds; nothing is selected after the test.

## 2. Why 12 pairs earlier, 15 now
The frozen runs cover **15 distinct (dataset, seed) combinations**: UNSW-NB15 seeds 12-21 (10, because the group-disjoint training split depends on the seed) and CICIoT2023 seeds 12-16 (5; the CIC training file is seed-independent). The Phase 9C command `preproc-equiv` refits UNSW for all 10 pairs but CICIoT2023 only for seeds 12 and 16 by design (a refit with identical training data is redundant), i.e. **10 + 2 = 12**; the missing three (CIC seeds 13, 14, 15) were a coverage choice, not a failure. Phase 9D closed the gap and went further (`scripts/preproc_coverage_15_pairs.py`, evidence `evidence/preprocessor_coverage_15_pairs.json`):
* refit from **training data only** (`load_dataset(load_test=False)`) for the remaining pairs and comparison of every fitted parameter (feature names, imputer statistics, scaler mean/scale, one-hot categories) with the saved preprocessor → **15/15 identical**;
* every one of the **280 saved preprocessors equals the preprocessor of its (dataset, seed) pair** (same training data ⇒ same fit; **0 mismatching runs**);
* the protected-access guard recorded **no** open of a locked file (`locked_test_opened: []`).
Per-run integrity (readiness, Phase 9C): checkpoint hashes, preprocessor hash, strict `state_dict` load, output dimension = recorded encoded dimension (UNSW 192-194 depending on the seed, CIC 39), thresholds in [0,1]; 280/280 pass.
Residual limitation: `preprocessor.joblib` was never part of `COMPLETE.json`; its hash is frozen only now, and its equality with the training-time fit is established by the refit evidence above, not by a historical hash.

## 3. Tiers of the frozen evaluation (declared before any test result exists)
(`evidence/final_test_run_tiers.csv`, one row per run.)
| Tier | Content | Runs |
|---|---|---|
| **Primary** | 5 arms {reference, clean_fedavg, scenario_fedavg_topk, corrected, reference_gaussian} × 2 datasets × seeds 12-16, **best checkpoint at the primary calibration threshold**; ROC-AUC, F1, recall, FPR; the four paired contrasts below | 50 |
| **Secondary** | the other 19 Phase 6C arms (ablations, failure and natural-attacker arms, corrected_gaussian, clean_centralized, robust_random_no_imputation, scenario_fedavg_random …), last-round checkpoints, calibration operating points 1%/5%/15%, overlap-controlled subsets | 190 |
| **Exploratory** | the 40 Phase 7b runs (seeds 17-21, UNSW only; reported in full, no inferential weight) | 40 |
Primary paired contrasts (n=5, exploratory statistics, exact sign-flip p, minimum 0.0625): (1) reference − clean_fedavg; (2) reference − scenario_fedavg_topk; (3) corrected − reference; (4) reference_gaussian − reference. **All arms of every tier are reported regardless of outcome**; no run, arm, checkpoint, threshold or subset can be added, dropped or re-selected after the first result exists.
