# Five-seed confirmatory protocol — FINAL (locked by `docs/phase6c/EXPERIMENT_MANIFEST.json`)

Manifest SHA-256: `c648b93590494fcf260d5f143fe30eabbec28ee61c6b782dbe5f8550e0c1f267`.
Anything not stated here is defined by the configurations in `configs/phase6c/` (48 files, hashed in the manifest).
The Phase 6A/6B one-seed results (seed 2) are **exploratory**; only the runs below are confirmatory. The earlier
draft of this document remains in Git history (commit `5cdeca6`).

## 1. Seeds
**12, 13, 14, 15, 16** (never used in exploration). The same seed gives the same exogenous traces in every arm
(`routing.trace_mode: matched`: every network, failure, selection and attacker draw is derived from (seed, round, client)).
Seeds 2–6 of the historical manuscript may be run later as a separately labelled replication; they are not part of this protocol.

## 2. Datasets (hash-locked; verified by preflight)
| | UNSW-NB15 | CICIoT2023 |
|---|---|---|
| training source | official `UNSW_NB15_training-set.csv` sha256 `bec7dd5e…0648fa` | `prepared_verified_v2_filegroup` (file-group protocol), train content sha256 `a1f372de…629384`, validation `8636b822…39408f` |
| validation pool | carved from the official training file with a **predictor-group-disjoint** split (7 folds, seed-dependent), then a **three-way** predictor-group-disjoint split into calibration / selection / report thirds | explicit prepared validation file (146 626 rows), then the same three-way split |
| locked test | official `UNSW_NB15_testing-set.csv` (82 332 rows) sha256 `734fe664…c0a559` | prepared `test.csv.gz` (300 000 rows, 2.35 % benign), content sha256 `1ae0ecc4…d45c8ce` |
| features | encoded (194) | 39 (raw source is byte-equivalent to a third-party release; **official UNB provenance unverified**) |
Known limitations (reported, not fixed): 17 rare CIC classes remain row-stratified (no capture independence); thresholds on CIC are not capture-independent
(all three validation thirds share capture files); UNSW test has 10.4 % predictor-identical overlap with training (handled by the sensitivity mask below).

## 3. Common training settings (every arm)
50 clients, 10 per round, 30 rounds, 2 local epochs, batch 256, lr 3e-4, MLP 128-96-64, Dirichlet α = 0.5 (min 100 samples/client), server lr 0.5 /
momentum 0.9 (except the momentum controls), distance filter k = 2.5, sign-flip attackers (scale 5, fraction 0.2), explicit failure probability 0.1 + simulated
delivery failure, recovery weight factor 0.5, routing weights (0.4, 0.3, 0.3), 3 edges, CPU, early stopping **off**, `validation_only` (the test files are never read).
Gaussian arms use the original settings (clip 0.1 UNSW / 0.05 CIC, target ε 10, `max_client_weight_share` 0.1) and report ε only as a **diagnostic RDP estimate**.

## 4. Arms (24 per dataset, 5 seeds → 240 runs: 120 UNSW + 120 CICIoT2023)
| Group | Arm | Definition | Version |
|---|---|---|---|
| baseline | clean_centralized | 1 client, clean data, momentum 0 | reference_v1 |
| baseline | clean_fedavg | FedAvg, no attack/failure/routing | reference_v1 |
| baseline | scenario_fedavg_random | FedAvg under attack+failure, uniform random selection, no imputation | reference_v1 |
| baseline | scenario_fedavg_topk | same with deterministic top-k routing | reference_v1 |
| baseline | robust_random_no_imputation | distance filter, uniform selection, no imputation | reference_v1 |
| main | **reference** | original method (top-k, filter, pre-filter median imputation) | reference_v1_historical |
| main | reference_gaussian | reference + Gaussian (diagnostic ε) | reference_v1_historical |
| main | **corrected** | coverage-aware selection (penalty 0.5) + packet-coupled delivery (2 retransmissions) + real-only filter with post-filter surrogates + collective surrogate cap 0.10 | corrected_v2_phase6c |
| main | corrected_gaussian | corrected + Gaussian (diagnostic ε) | corrected_v2_phase6c |
| control | ctl_selection_uniform / ctl_selection_coverage | reference with one selection change | reference_v1 |
| control | ctl_imputation_none / ctl_imputation_cap010 / ctl_imputation_postfilter | reference with one imputation change | reference_v1 |
| control | ctl_delivery_coupled | reference with packet-coupled delivery | reference_v1 |
| control | ctl_momentum0_lr0p5 / ctl_momentum0_lr5p0 | isolated momentum controls (second keeps the steady-state gain lr/(1−m) = 5) | reference_v1 |
| control | ctl_weighting_uniform | reference with uniform client weights | reference_v1 |
| natural_assignment | nat_reference / nat_selection_uniform / nat_corrected | **separate experiment**: historical naturally-assigned fixed malicious clients | as named |
| failure_sensitivity | fail0p0_reference / fail0p3_reference / fail0p3_corrected | explicit failure probability 0.0 / 0.3 | as named |

Algorithm versions: **reference_v1_historical** reproduces the historical algorithm exactly (verified: all 67 numeric round-metric columns identical to Phase 6A);
**corrected_v2_phase6c** = the corrected variant above. Both are preserved and recorded in every run's `run_metadata.json`.

## 5. Attacker-assignment policy
Primary experiment (all arms except `nat_*`): **exposure-controlled** — in every round exactly `round(0.2 × selected)` of the *selected* clients (2 of 10) are attackers, drawn
from a (seed, round) stream, so every selection policy faces identical attacker exposure (the Phase 6B diagnostic showed top-k exposure ranging 7–48 % across seeds, seed 2 being the worst of 200).
Natural assignment (historical fixed set) is run only in the three `nat_*` arms and is labelled as a separate experiment; its exposure is reported as a covariate.

## 6. Validation protocol, checkpoint selection and thresholds
The validation pool is split three ways (predictor-group-disjoint, label-stratified): **calibration** (decision thresholds only), **selection** (per-round ROC-AUC → best checkpoint, no early stopping),
**report** (never used for any decision; logged every round for transparency). Threshold selection: FPR cap 0.15 with min recall 0.6 per round on the calibration partition; diagnostic thresholds at FPR targets 1 %, 5 %, 15 %.
Reported per run: best checkpoint **and** last-round model (to expose selection optimism). Final model files: `best_model_state.pt`, `last_model_state.pt`.

## 7. Handling of divergent runs
A run is *diverged* if its final training loss is non-finite or > 1e3 or its last-round report AUC ≤ 0.5. Diverged runs are **reported (count per arm) and never excluded or re-run**;
paired summaries include them and add the median and an exact sign test.

## 8. Endpoints and statistics
* **Primary (per dataset):** ROC-AUC and F1 at the calibration-selected threshold on the locked test set (best checkpoint), one evaluation per run.
* **Co-primary safety:** FPR and recall at calibration targets 1 % and 5 %; test FPR vs its calibration target.
* **Secondary:** PR-AUC, last-checkpoint metrics, worst-client recall, selection Gini, clients ever selected, surrogate weight share, delivery ratio, bytes on wire, divergence rate; UNSW also on the duplicate-controlled mask.
* **Comparisons:** paired by seed (identical traces) against the arm named in `compare_with`. Primary family (Holm-adjusted, per dataset, AUC): corrected−reference, reference−scenario_fedavg_topk,
  reference−scenario_fedavg_random, reference_gaussian−reference, corrected_gaussian−corrected. With n = 5 the smallest attainable exact two-sided p is 0.0625: results are reported as effect sizes and per-seed differences, not as significance claims.
  Validation-stage numbers are *selection-partition/report-partition development metrics*; confirmatory claims use test metrics only.

## 9. Final-test access (separate operation)
`scripts/phase6c/final_test_evaluate.py` is **never** called by the runner. It requires: a verified manifest hash; every one of the 240 runs complete and verified; an unchanged code/config fingerprint; a signed authorization file
(`authorized: true`, exact statement, name, no-retuning acknowledgement, manifest hash); test files whose sha256 equal the locked values; and evaluates each run **once** (exclusive file creation + ledger).
Thresholds are those chosen on the calibration partition during training. Nothing is retrained or retuned after the test is read.

## 10. Weight cap and privacy statements (carried into every run's metadata)
* A strict per-client weight cap c is mathematically infeasible whenever fewer than 1/c updates are retained (max weight ≥ 1/n); the effective cap is max(c, 1/n). Requested, minimum feasible, effective and actual maxima are logged each round. The manuscript must not claim a strict 0.1 cap.
* The Gaussian step is an empirical defence. ε is a diagnostic RDP estimate that assumes Poisson sampling, which is not satisfied (deterministic or fixed-size selection, data-dependent filtering, surrogate imputation); **no certified differential-privacy guarantee is claimed.**

## 11. Remaining limitations
Single machine CPU determinism only; CIC official provenance and capture independence unverified; surrogate imputation is not recovery of private information; packet-coupled delivery parameters are a priori assumptions;
the privacy accounting is outside any proof (see `docs/phase6b/PRIVACY_FEASIBILITY.md`); `clean_centralized` on CICIoT2023 is the slowest arm.

## 12. Resources (rough; refined by the runner as runs complete)
≈ 10–12 hours sequentially on CPU for all 240 runs, ≤ 3 GB RAM, a few GB of disk.
