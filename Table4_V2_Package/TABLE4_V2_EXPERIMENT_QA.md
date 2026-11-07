# Table 4 v2: experiment QA

Scope: 40 new runs (E1-E4 x 2 datasets x seeds 12-16) plus 30 reused locked Phase 6C comparator runs, all report-partition (validation-only). Status at analysis time: 40/40 new runs verified, 0 failed, 0 incomplete.

## Automatic checks (scripts/table4_v2/analyse.py): 17 / 17 PASS

| Check | Result | Detail |
|---|---|---|
| all 40 new runs verify against the locked manifest (artifact hashes, config hash, code fingerprint, 30 rounds, test_data_loaded=false, accounting invariants) | PASS | 40/40 verified [] |
| test_data_loaded is false for all 40 new runs | PASS |  |
| reused comparator runs (30) pass the Phase 6C manifest verification | PASS | 30 runs |
| every (dataset, arm) has exactly seeds 12-16 | PASS |  |
| F1 and FPR of the 40 new runs recomputed from logged confusion counts (tp, fp, fn, tn) | PASS | max abs error 5.55e-16 |
| selected checkpoint = replay of the training rule on selection-partition ROC-AUC (improvement > 1e-4 over running best; all runs) | PASS | 0 mismatches |
| selection-partition ROC-AUC recomputed from stored predictions equals the logged value (new runs) | PASS | max abs error 1.11e-16 |
| attempted bytes from network log equals the round log | PASS | max diff 0.0 B |
| DP runs: subsampling_amplification_valid=false and epsilon_is_certified_guarantee=false (no certified DP claim) | PASS | 30 DP runs |
| t4_e3_dpfedavg_random_path: calibrated noise multiplier and planned epsilon match the target 10.0 | PASS | sigma 0.9939 |
| t4_e4_proposed_eps20: calibrated noise multiplier and planned epsilon match the target 20.0 | PASS | sigma 0.6717 |
| E1 vs routed-path FedAvg random-selection arm: identical selected clients, attackers, failure draws, client data distribution and attacker assignment (all 10 dataset-seed pairs) | PASS |  |
| E2 vs routed-path MAD-filter random-selection arm: same identity checks | PASS |  |
| E1, E2, E3 share identical network traces (random-path stream is policy-independent) | PASS |  |
| E4 vs existing Gaussian reference: identical network traces, selected clients and attackers (privacy target is the only change) | PASS |  |
| E1 path assignment differs from the routed arm (the intended single factor) | PASS |  |
| data split hash (validation_split_info.json) identical to the locked Phase 6C run of the same dataset and seed (all new runs) | PASS |  |


### Note on the checkpoint-selection check
A first execution of the analysis reported 13 mismatches for "selected checkpoint = argmax selection-partition AUC". The data were correct; the check was wrong. Training (src/experiment.py: `improved = score > best + early_stopping_min_delta`, delta 1e-4) replaces the checkpoint only when the selection AUC improves by more than 1e-4, so a later round with a smaller gain is deliberately not selected. The check now replays that exact rule, and all runs (including the 30 locked Phase 6C runs) agree. The 13 original mismatches were all of this kind. No data, run or result was changed.

## Gate list
| Gate | Evidence |
|---|---|
| 40 runs complete and independently accounted for | orchestrator `validate`: 40 verified; COMPLETE.json and hashed artifacts per run; runner event log |
| Every value traceable to run id, seed, config hash, source artifact | TABLE4_V2_PER_SEED.csv columns run_id, seed, config_sha256, code_fingerprint, manifest_sha256, out_dir; TABLE4_V2_PROVENANCE.json |
| No test data loaded | `test_data_loaded=false` in all 40 run_metadata.json; configs have no test path |
| No historical results overwritten | new outputs only under results_table4_controlled_v2/; Phase 6C, Phase 10 and ablation directories untouched; 30 reused runs re-verified against the Phase 6C manifest |
| Report partition used | all metrics from the report partition; checkpoint chosen on the separate selection partition |
| PDR vs update-delivery success distinct | separate columns (pdr_first_transmission, update_delivery_rate); table columns PDR and Deliv. |
| CIs and paired differences | per-seed differences, t-interval 4 d.f., exact sign-flip test; minimum attainable p = 0.0625 |
| Negative / inconclusive findings kept | listed below |
| Old Table 4 numbers not reused | every value recomputed from run directories; old values appear only in the impact report as the object of comparison |
| Nothing pushed | local commits only on branch table4-controlled-v2 |

## Limitations (carry into the manuscript)
1. **Five paired seeds.** The smallest possible two-sided exact sign-flip p is 0.0625, so no contrast can reach p<0.05. A consistent direction in 5/5 seeds is reported as such, not as significance. The five-seed estimates are not free of stochastic uncertainty, and small differences are not evidence of equivalence.
2. **Delivery random draws are not common random numbers across path policies.** The per-event delivery uniform follows a binomial packet draw that consumes a probability-dependent number of variates, so different path assignments do not share the same delivery uniform. This adds noise, not bias, to path-assignment contrasts. Client selection, attackers, failure draws, data partitions and link evolution are identical (verified on all 10 dataset-seed pairs).
3. **AP of reused runs is unaudited** (original run output). F1/AUC/FPR of reused runs come from the audited ledger; new runs use the corrected evaluation directly.
4. **DP epsilon is a diagnostic RDP estimate** (`subsampling_amplification_valid=false`, `epsilon_is_certified_guarantee=false`), not a certified guarantee.
5. One simulated edge-cloud network, one attack family (20% sign-flip), validation-only.
6. Network metrics are identical across aggregation / privacy variants by construction when selection and paths are matched; they are not independent evidence per arm.

## Negative and inconclusive findings (preserved)
* **Path assignment (routed vs random) has no detectable effect on detection** on either dataset: CICIoT2023 ΔAUC +0.0005 (FedAvg) and -0.0002 (MAD); UNSW +0.0006 and -0.0088; every CI includes 0. Its effect is on network metrics (random paths: delay +15.4 ms, PDR -0.087, stability -0.332, TE lower; 5/5 seeds, p = 0.0625).
* **Top-k vs uniform selection** (routed paths) improves delay, PDR, stability, TE in 5/5 seeds but not detection (CICIoT2023 ΔAUC -0.012, UNSW +0.012; CIs include 0).
* **The detection advantage over FedAvg comes from the MAD-filter aggregation**: UNSW ΔAUC +0.098 (CI 0.017 to 0.179, 5/5 seeds); CICIoT2023 +0.0025 (5/5). Not from routing.
* **FedAvg degrades at the final round under sign-flip attack** (AUC_last about 0.46-0.55 on CICIoT2023, 0.55-0.65 on UNSW); selected-checkpoint metrics hide this.
* **The DP pipeline costs detection**: reference -> reference+Gaussian eps~10 ΔAUC -0.0032 (CICIoT2023) and -0.0419 (UNSW), both 5/5 seeds. eps 10 -> 20 recovers +0.0007 (CIC) and +0.0103 (UNSW), not significant.
* "Proposed vs DP+FedAvg" is a multi-factor bundle (selection, paths, aggregation, recovery) and is descriptive only.
