# Phase 8 scientific evidence audit

Sources: existing outputs only (Phase 6C 240 runs, Phase 7b 40 runs, Phase 7b post-hoc re-evaluation); nothing retrained, nothing overwritten, final-test data untouched.
Tables: `docs/phase8/tables/` (script `scripts/phase8/phase8_tables.py`, read-only). MB = 1e6 bytes. n=5 seeds everywhere ⇒ min exact p = 0.0625: all statistics are exploratory.
Classification used below: **CONFIRMED BUG** / **DESIGN LIMITATION** / **HYPOTHESIS** / **NOT ESTABLISHED**.

## 0. Integrity baseline (verified in Phase 8)
- Phase 6C: 240/240 runs pass `verify_run_dir` against the locked manifest (hash `c648b935…`); 240/240 config hashes match. Phase 7b: 40/40 mandatory runs verified, 80/80 config hashes match. Phase 7 (old code): 13 verified runs kept as history.
- All 80 distinct Phase 6C/7/7b configs have `data.test_csv: ''` and `experiment.validation_only: true`; no test CSV is tracked by git. Final-test data were not read.
- Git tags `phase6c-final-results`, `phase7-guard-v1`, and (new, local) `phase7b-final-results` → 7e71889 freeze the three code states. Phase 7b fixed threshold implementation is preserved in `src/metrics.py`.

## A. Robust aggregation
| Item | Class | Evidence |
|---|---|---|
| MAD/median filter has no power with ≤2 genuine updates and is unreliable at 3 | DESIGN LIMITATION (confirmed) | `tables/T5b`: Phase 6C, 1-2 genuine updates: malicious accepted 12/12 (100%), honest rejected 4/102 (3.9%), 66 rounds; exactly 3: honest rejected 38.99%, malicious accepted 30.6% (130 rounds); 4-5: 25.8% / 19.8% (1132 rounds); ≥6: 1.9% / 14.1% (4672 rounds). Phase 7b shows the same pattern (3: 38.2% / 49.1%; ≥6: 5.5% / 24.1%). Even with ample updates, 14-24% of effective malicious updates are retained. |
| Behaviour when nothing survives the filter | Handled (not a bug) | `src/aggregation.py` l.80: keeps the single update with the smallest distance. Zero delivered updates ⇒ no aggregation, model and server state unchanged (`if updates and not aggregation_skipped`). Phase 7b: rounds with 0 updates give an undefined mean train loss (NaN), not divergence. |
| Cap claim "no client can dominate" | DESIGN LIMITATION | Realised `max_applied_weight_share` reaches 1.00 in `corrected` (single retained update) on both datasets (`T5a`); per-client cap 0.10 needs ≥10 retained updates. |
| Numerical stability / momentum | NOT ESTABLISHED as a defect | No inf/NaN divergence in any Phase 7b run. Large transient losses exist (Phase 7b mean over seeds of max training loss: `fail0p3_corrected` 243.9, guard 17.6, reference 2.0). Whether momentum 0.9 / lr 0.5 amplifies them is a HYPOTHESIS: `ctl_momentum0_lr0p5` (momentum 0) did not change AUC meaningfully in Phase 6C (UNSW best AUC 0.9828 vs reference 0.9838) but was not tested under 30% failures. |
| Phase 7 guard (`min_real_updates=3`) | Tested, **not supported** | Primary criterion failed (better in 3/5 seeds, needs 4/5); see `docs/phase7b/PHASE7B_CHANGELOG.md` and `T2c`. Inert in 4/5 seeds without injected failures. |

## B. Surrogate handling
- Surrogate construction (`src/recovery.py`): one coordinate-median vector copied k times; in the pre-filter reference mode each copy enters the MAD/median as an independent observation. DESIGN LIMITATION (confirmed from code; effect size not isolated).
- Verified surrogate weight shares (mean over rounds with ≥1 delivered update, 5 seeds; `T5a`):

| arm | UNSW | CIC |
|---|---|---|
| reference | 0.221 | 0.208 |
| corrected | 0.096 | 0.097 |
| reference_gaussian | 0.306 | 0.304 |
| **corrected_gaussian** | **0.476** | **0.480** |
The previously reported ≈0.479 (corrected_gaussian) vs 0.097 (corrected) is **reproduced** (0.476-0.480 vs 0.096-0.097).
- **CONFIRMED BUG (Gaussian path only): the collective surrogate cap is not enforced under central-DP aggregation.** `corrected_gaussian` is configured with `failure.surrogate_total_weight_cap=0.10`, which scales surrogate weights before aggregation (`src/experiment.py` ~l.943-956). The central-DP branch then re-projects the retained weights with `capped_normalized_weights(…, 0.10)`; with fewer than 10 retained updates the cap is infeasible (1/n > 0.10) and the projection is exactly uniform, discarding the scaling. The strict cap is infeasible in 71% (UNSW) / 79% (CIC) of `corrected_gaussian` rounds and 91%/93% of `reference_gaussian` rounds. `surrogate_cap_applied=True` is nevertheless logged. Non-DP `corrected` is unaffected (0.096).
- Historical consequence: Gaussian-arm comparisons (UNSW best AUC 0.9406 vs corrected 0.9756, i.e. −0.035) mix the noise cost with an inflated surrogate share. How much of the gap is due to the share is NOT ESTABLISHED. The non-Gaussian conclusions (reference/corrected/ablations) are not affected by this defect.
- Fix: new default-off variant (`privacy.preserve_surrogate_cap`), see CODE_CHANGELOG #1 and ALGORITHM_DECISION.

## C. Routing and delivery
- Top-k starvation (`T4`, UNSW, 5 seeds): selection Gini 0.731, 27.2 of 50 clients never selected (top-k/reference); coverage-aware 0.486 / 8.0; uniform 0.205 / 0. CONFIRMED (design limitation of deterministic top-k).
- Participation vs accuracy: mean recall of never-selected clients 0.975 vs 0.976 for selected clients (reference); worst-client recall 0.957 (reference), 0.945 (corrected), (clients with ≥50 attack rows). No measurable recall penalty from starvation on these partitions ⇒ the fairness cost is a participation/coverage cost, not (here) an accuracy cost. The correlated route-quality/label-distribution scenario suggested by the review was NOT tested.
- Attacker exposure: with `assignment: exposure_controlled` the malicious share of selected clients is 0.200 for every policy by construction, so exposure cannot differ across routing policies in these arms. In natural-attacker arms: top-k 0.195, uniform 0.188. The routing security score has no access to attacker identity (no reference in `src/network.py`), so "security-aware routing" has **no demonstrated attacker-avoidance effect**.
- Packet PDR vs update delivery (`T3`, UNSW): reference: PDR 0.851, update delivered 0.848, received (after explicit failures) 0.750, because independent-draw delivery is unrelated to packets received. Packet-coupled `corrected`: PDR (first transmission) 0.834 but delivered 0.626, received 0.557; `ctl_delivery_coupled` 0.680/0.601. Reference and Corrected therefore do not face the same effective channel (CONFIRMED confound, already in the Phase 7 audit); `ctl_delivery_coupled` isolates it: best AUC 0.9789 vs reference 0.9838 (the channel alone costs ≈0.005; the rest of the corrected deficit (0.9756) is another factor, NOT isolated).
- Communication accounting: `communication_bytes` = update payload of every selected client = 300 × 174,520 B = **52.36 MB** (uplink) for all arms. Delivered payload: reference 44.40 MB, corrected 32.78 MB, scenario_fedavg_random 40.80 MB. On-wire bytes including retransmission: corrected 62.94 MB. Downlink broadcast is not counted. Differences in "communication cost" reported in the manuscript cannot come from payload size.
- Information available at selection: `update_round()` evolves link state, then ranking and selection use that state; delivery is drawn later from a separate event RNG. No future delivery outcome is used. However the ranking uses the **true** link stability, which is also the delivery probability (`expected_pdr = stability`): an oracle on the success probability (no measurement noise, no estimation delay). DESIGN LIMITATION to be stated.

## D. Privacy
- Noise placement: after filtering (un-clipped updates), the retained updates are clipped to `clip_norm`, weights capped/normalised, averaged, then Gaussian noise with std = z × clip_norm × (realised max weight share) × adjacency_factor is added to the aggregate (`src/experiment.py` ~l.958-1000). The scale depends on the realised max share, which is data-dependent (filter outcome). The server sees unperturbed individual updates (trusted-server assumption).
- Not valid for a formal claim: selection is deterministic (not Poisson, q=0.2 only as an RDP approximation), filtering/weighting are data-dependent and not accounted for; each run's `privacy_plan.json` records `subsampling_amplification_valid=false`.
- Statements in `main.tex`: l.1066-1076 and l.2540 correctly call ε-hat an estimate, "not a formal end-to-end guarantee". Remaining risk: abstract "provides an estimated central-DP budget", title "Secure", "privacy-aware" naming. No statement of certified DP found in the repository or the Phase 6C/7 reports.
- Required wording: ε is a diagnostic accountant value for a hypothetical sampled Gaussian mechanism; adjacency, observable outputs and the actual sensitivity proof are not provided.

## E. Verification of the ten evidence items (Stage 5)
1. **Old vs audited metrics**: `T1` (arm means) and `posthoc_threshold_fix/phase6c_posthoc_with_deltas.csv` (per run). Original tables untouched.
2. **Threshold correction / last round**: the bug only affects a threshold of exactly 1.0 and ROC ties. Phase 6C: 12 runs change last-round values (e.g. UNSW nat_corrected AUC 0.8893 → 0.9368 mean, CIC fail0p3_corrected 0.9760 → 0.9767); Phase 7b: 1200 per-round records, 0 inconsistencies between reported FPR and confusion matrices; 8 rounds with threshold 1.0, 7 of them predict positives, the 8th (`fail0p3_corrected` seed 17 round 26, calibration recall 0, FPR 0) predicts none, consistent with the rule.
3. **Checkpoint selection**: best-round selection used the old AUC; per-round model states were not stored, so re-selection is not reproducible. Maximum |ΔAUC| at the selected checkpoint is 0.0037 (UNSW corrected) and ≤0.0002 elsewhere; gaps between the best and second-best round are <0.001 in 182 of 240 runs, so some selections may differ — NOT ESTABLISHED whether any changed.
4. **Routing compared under compatible conditions**: only controls that vary one factor are comparable: `ctl_selection_uniform` (best AUC 0.9815), `ctl_selection_coverage` (0.9829), `reference` top-k (0.9838), all with independent-draw delivery and the same recovery. Differences ≤0.002 AUC; no significant routing-policy effect on detection (n=5). `scenario_fedavg_topk` 0.8870 vs `scenario_fedavg_random` 0.8752 compare different baselines (no robust filter) and are far below robust arms.
5. **Fairness/coverage/exposure**: §C and `T4`.
6. **Surrogate weight and retained real updates**: §B, `T5a`, `T5b`; retained-update counts per round are in `aggregation_diagnostics.csv`.
7. **Packet delivery vs successful FL updates**: §C and `T3`.
8. **Preprocessing fitted on training data only**: verified in code (`src/data.py` `fit_transform` on train, `transform` on validation/calibration/report). Per-run `preprocessor.joblib` is saved.
9. **CICIoT2023 split-independence limitations**: Phase 6C CIC uses `prepared_verified_v2_filegroup` (capture-group aware, content hashes in the manifest); train/validation/test = 926,133 / 146,626 / 300,000 rows; benign prevalence 53.9% / 3.2% / 2.35% (strong prior shift); official provenance unverified ("byte-equivalent to a third-party release"); there is no device-held-out split; predictor-identical rows are group-disjoint but cross-class conflicts exist in the source (`docs/data_integrity/ciciot2023_source_audit.json`); AUC ceiling ≈0.996 so CIC cannot discriminate between most arms. The manuscript still describes the older row-level split.
10. **Improvement claims vs comparable baselines**: see MANUSCRIPT_REVISION_ROADMAP, claim matrix.

## F. What the data support (headline numbers, Phase 6C, best checkpoint, report partition, audited)
UNSW AUC: clean_centralized 0.991, clean_fedavg 0.984, reference 0.9838, corrected 0.9756, fail0p3_reference 0.9821, fail0p3_corrected 0.9643, reference_gaussian 0.9419, corrected_gaussian 0.9406, scenario_fedavg_topk 0.887, scenario_fedavg_random 0.875. CIC AUC: all robust arms 0.9930-0.9963 (ceiling); scenario_fedavg_topk 0.981. Reference is the best (or tied) federated robust arm; corrected never exceeds reference significantly and is less stable. Phase 7b (UNSW, seeds 17-21, last-round AUC): reference 0.966±0.026, corrected 0.950±0.043, guard 0.969±0.012; fail0p3: reference 0.976±0.006, corrected 0.840±0.227, guard 0.926±0.064.
