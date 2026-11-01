# Final five-seed protocol (PRESPECIFIED — not executed)

Status of evidence: everything produced in Phase 6A/6B (seed 2) is **exploratory**. Confirmatory results come only from the seeds and arms below.
**Confirmatory seeds: 12, 13, 14, 15, 16** (never used in exploration). Seeds 2–6 of the historical manuscript may be run afterwards as a separate,
clearly labelled *historical-seed replication*; they are not used to choose anything.

## Common settings (every arm)
Datasets: UNSW-NB15 (group-disjoint train/validation, official test locked) and CICIoT2023 file-group v2 (39 features, provenance unverified, 17 rare classes
row-stratified). 50 clients, 10/round, 30 rounds, 2 local epochs, batch 256, lr 3e-4, MLP 128-96-64, Dirichlet α=0.5, 20 % sign-flip attackers (scale 5),
10 % explicit failure probability. Matched exogenous traces (`routing.trace_mode: matched`). Threshold from the predictor-group-disjoint **calibration** half
of validation (`threshold_calibration_fraction: 0.5`); model selection (best round) on the **evaluation** half; early stopping off; CPU.

## Arms
| Id | Arm | Definition |
|---|---|---|
| A1 | Centralized-clean | single client, no attack/failure/routing/DP |
| A2 | FedAvg-clean | no attack, no failure, uniform random selection, FedAvg |
| A3 | FedAvg-scenario | attack+failure, uniform random selection, FedAvg, no imputation |
| A4 | FedAvg + matched routing | A3 with deterministic top-k routing |
| A5 | **Reference** (historical proposed, no DP) | = `v0_reference_matched` |
| A6 | Reference + Gaussian (diagnostic ε) | = `v7_gaussian_diagnostic_eps10` |
| A7 | **Corrected** (prespecified on principle, not on results) | packet-coupled delivery + coverage-aware selection (penalty 0.5) + surrogate cap 0.10 |
| A8 | Corrected + Gaussian (diagnostic ε) | A7 with the A6 privacy settings |
| R1–R4 | Robust-aggregation controls | distance filter (A5), multi-Krum (f=2), trimmed mean 0.2, plain FedAvg — all under A5 conditions, no DP |
| I1–I3 | Imputation controls | none, median surrogate (A5), capped 0.10 |
| S1–S3 | Routing controls | top-k (A5), uniform random, coverage-aware |
| M1–M3 | Isolated momentum | (m=0.9, lr=0.5) vs (m=0, lr=0.5) vs (m=0, lr=5.0, gain matched) |
| N1–N8 | Network failure sensitivity | explicit failure ∈ {0, 0.1, 0.2, 0.3} × delivery model ∈ {independent_draws, packet_coupled} |

Arms that repeat a configuration (e.g. A5 = R1 = I2 = S1 = M1) are run once. A7's composition is fixed here; the individual corrections are separately
estimated by I3, S3 and the delivery-model contrast in N, so any gain of A7 can be decomposed.

## Endpoints
* **Primary (per dataset):** ROC-AUC and F1 at the calibration-selected 15 % FPR threshold, on the locked test set, one evaluation per frozen configuration.
* **Co-primary safety:** FPR and recall at calibration targets 1 % and 5 %; test FPR is reported against its calibration target (shift).
* **Secondary:** PR-AUC, worst-client recall, never-selected-client recall, selection Gini, clients ever selected, longest exclusion gap, surrogate weight share,
  honest-update rejection, malicious retention, min AUC after round 3, delivery ratio vs PDR (both definitions), bytes attempted / on-wire / delivered, wall time, peak memory.
* **UNSW additionally:** the same endpoints on the duplicate-controlled test mask (test rows whose predictor vector is absent from official training).

## Statistics
Per seed, paired differences against the reference arm on identical traces. With n = 5 report all five differences, their mean and SD, sign consistency and an exact
Wilcoxon signed-rank p (smallest attainable two-sided p = 0.0625); no significance threshold is used as a claim. Primary family of contrasts (Holm-adjusted):
A7−A5, A5−A4, A5−A3, A6−A5, A8−A7. Seed-level variability is reported, not hidden by averaging.

## Locked final-test protocol
1. Freeze configs, code commit and the datasets' hashes (`PRESPECIFICATION`-style file) **before** any test evaluation.
2. A `final_test` execution mode (to be implemented; accepts only a frozen config hash) evaluates the best-checkpoint model once on the test set using the thresholds
   already chosen on the calibration partition. No retraining, retuning or threshold change after seeing test numbers.
3. UNSW: official 82 332-row test file + duplicate-controlled sensitivity mask. CICIoT2023: the file-group test file (300 000 rows, 2.35 % benign).
4. If any frozen run fails, the failure is reported; it is not re-run with changed settings.

## Preconditions (blockers before execution)
* Implement the `final_test` mode and its config-hash lock (engineering; no scientific change).
* Decide whether to keep deterministic routing / the Gaussian claims as scoped in `PRIVACY_FEASIBILITY.md`.
* Decide the CIC feature set and official-provenance requirement.
* Decide whether the MAD filter should exclude surrogate rows (a design change; currently documented defect).

## Resource plan (from measured one-seed runs)
UNSW ≈ 1–1.5 min/run, CIC ≈ 3–4 min/run (CPU). ≈ 40 distinct arms × 5 seeds ≈ 200 runs per dataset: UNSW ≈ 3–5 h, CIC ≈ 10–13 h; memory ≤ 3 GB.

---
## Finalization review after the Phase 6B one-seed controls (amendments, still NOT locked)

Findings that changed the protocol (measured, `docs/phase6b/`):
1. **Attacker exposure is a first-order confound.** Under deterministic top-k, the share of selections that are malicious has mean 21 % (= chance) but SD 0.093 vs 0.019 for
   random selection across 200 seeds; seed 2 (used in 6B) is the maximum (48 %, 22/30 majority-attacker rounds), where the median-based filter breaks down, the model diverges
   (training loss up to ~8e4) and collapses to a constant predictor (AUC 0.500). One-seed differences among variants in that regime are not interpretable.
   * **Amendment A:** every run records `malicious_share_of_selections` and the number of majority-attacker rounds; they are reported as covariates for every contrast.
   * **Amendment B (new arm, requires implementation + freeze before use):** a selection-independent attacker assignment (a client is malicious in round t with probability 0.2 from a
     per-(seed, round, client) stream) so that all selection policies face the same expected exposure. Without it, selection-policy contrasts are confounded.
   * **Amendment C:** divergence (final-round AUC = 0.5 or non-finite loss) is a *reported outcome* (failure rate per arm), never an exclusion; paired summaries use medians and the sign
     test in addition to means.
2. **Confirmatory-seed exposure (selection-only calculation, no outcomes):** top-k malicious share for seeds 12–16 = 0.233, 0.190, 0.217, 0.127, 0.210 (no majority-attacker rounds); the seeds are kept.
3. **Model-selection optimism:** selecting the best of 30 rounds on the evaluation half inflates AUC by 0.16 (UNSW) and 0.39 (CIC) on average relative to the mean of the last five rounds.
   * **Amendment D:** all development metrics are labelled *selection-partition* metrics; confirmatory reporting uses the locked test set only, and last-round and last-5-round values are reported
     next to the best-checkpoint value.
4. **Threshold independence:** on UNSW the evaluation FPR at the 15 % calibration target averages 0.169 (shift up to +0.027); on CIC it matches (0.146), but calibration and evaluation halves share capture files.
   * **Amendment E:** report evaluation-vs-calibration FPR shift per run; CIC thresholds are described as not capture-independent.
5. **Robust-filter / surrogate defect:** identical surrogate copies can collapse the MAD (documented, tested). Rounds with surrogate share ≥ 0.5 occur (up to 8/30 under uniform random selection at 31 % failures).
   * **Amendment F:** report rounds with surrogate share ≥ 0.5 and zero retained real updates; the design option "exclude surrogate rows from the filter statistics" is a Phase-6C decision
     and only enters the confirmatory set if implemented and frozen first.
6. **Weight cap:** retained updates average 7.7–8.6 (< 10) so a 0.1 cap is infeasible in every round; sample-proportional weights give a mean maximum share of 0.28–0.43. The manuscript must not state a 0.1 cap for the non-DP path.
7. **Gaussian learning is trace-dependent** (6A: AUC 0.954/0.982; 6B matched traces: 0.833/0.852 with AUC<0.9 in 28/30 rounds). Confirmatory A6/A8 results are the only admissible evidence; the 6A/6B numbers are not.
8. **Routing's network benefit is real and consistent** (200-seed simulation: delivery 0.839 vs 0.778 uniform random; delay 72 vs 79 ms; under packet-coupled delivery 0.635 vs 0.529 with 19–31 % extra bytes on the wire).
   Contrast N-arms must therefore be run with both delivery models and the delivered-update count reported as a mediator.

Status: amendments A, C–F are reporting rules (no code needed beyond logging already present). **B and the `final_test` mode require implementation; the protocol cannot be locked until they exist and are frozen.**
