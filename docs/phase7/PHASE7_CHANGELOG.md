# Phase 7 changelog (branch `research/phase7-algorithm-improvement`)

Phase 6C is preserved at git tag `phase6c-final-results` (commit 3029c6c); its manifest, configs and `results_phase6c/` are untouched. Nothing here uses or reads final-test data. No manuscript change. No training was run beyond smoke tests.

## 1. Audit findings (classified; evidence = Phase 6C recorded results + code)

**Confirmed implementation bugs that invalidate Phase 6C results: none found.** Core metrics, three-way split (calibration / selection / report), checkpoint selection and deterministic seeding behave as documented.

| # | Class | Finding | Evidence / location |
|---|---|---|---|
| 1 | Methodological inconsistency (confirmed) | Under Gaussian/DP aggregation the surrogate cap (0.10) is **not enforced**: the DP path re-projects weights with `max_client_weight_share=0.1`, which is infeasible for ≤10 updates (cap<1/n) and degenerates to uniform weights. Realised surrogate share in `corrected_gaussian` is 0.479 (max 0.80) vs 0.097 in `corrected`; strict cap infeasible in 70% of rounds. `surrogate_cap_applied=True` is logged anyway. | `src/experiment.py:938-992`, `src/privacy.py:149-187`; round_metrics of corrected_gaussian (UNSW) |
| 2 | Algorithm-design limitation (confirmed) | Median/MAD distance filter has no discriminative power with n<3 real updates and degrades with small n: UNSW defended arms, honest rejected / malicious accepted: n=1-2: 0% / 100% (5/5); n=3: 22% / 41%; n=4-5: 15% / 25%; n≥6: 2% / 19%. There is no minimum-sample guard. | `src/aggregation.py:72-83`; aggregation_diagnostics (830 rounds containing attackers; 1-2: all 5 malicious updates accepted) |
| 3 | Algorithm-design limitation (confirmed) | Surrogates are one coordinate-median vector copied k times (`src/recovery.py:24`); in the reference they enter the MAD as k independent observations (shrinking MAD) and carry 22% of the weight. | `src/experiment.py:842-867`; identical rows in aggregation_diagnostics |
| 4 | Methodological confound (confirmed) | Reference and Corrected are **not compared under the same effective channel**: `independent_draws` decides delivery with a Bernoulli draw unrelated to packets received (`src/network.py:241-247`), while `packet_coupled` requires all packets: update-delivery ratio 0.848 (Reference) vs 0.626 (Corrected). The Corrected deficit therefore mixes algorithm and harsher channel. | `tables/aggregate_metrics.csv` (update_delivery_ratio), network.py |
| 5 | Algorithm-design limitation (confirmed) | Deterministic top-k routing starves clients: Gini 0.73, ≈27 of 50 clients never selected; coverage-aware selection gives Gini 0.49 / 8 never selected. | all_runs selection_gini_recomputed |
| 6 | Unproven hypothesis | Corrected instability is driven by real-update starvation (packet-coupled delivery lowers real updates; fewer updates ⇒ unstable MAD and heavy weight concentration). Evidence is correlational: Corrected-family rounds have ≤2 real updates in 6.2% (Reference 0%), ≤3 in 14.3% (2.5%), max weight share >0.5 in 29% (4.6%), loss ×3 next round in 33/435 (8/435); within Corrected, loss growth vs received updates ρ=−0.11 (p=0.02), vs max weight share ρ≈0.01 (n.s.). Single-factor controls did not isolate it (`ctl_weighting_uniform`, `ctl_delivery_coupled` etc. show no clear effect). | Phase 6C round_metrics, UNSW |
| 7 | Expected trade-off | Gaussian perturbation costs AUC (−0.042 UNSW, −0.003 CIC). ε≈10 is a diagnostic RDP value, `subsampling_amplification_valid=false`, **not certified DP**. | `privacy_plan.json` |
| 8 | Reporting / data limitation | CIC AUC ceiling (≈0.996); split not device/file held-out; network trace identical across datasets. Best-checkpoint reporting hides last-round collapse (report both). | provenance + handoff reports |

Not found: checkpoint-selection leakage (selection partition ≠ report partition), threshold leakage (separate calibration partition), final-test access.

## 2. Code change (minimal, default-off)

`aggregation.min_real_updates` (int, default **0 = historical behaviour**). When >0 and the number of *delivered real* updates in a round is between 1 and `min_real_updates − 1`, the round **abstains**: no surrogates, no filter/aggregation, no server step (momentum velocity untouched, no DP step consumed). The global model is unchanged; the round is logged with `aggregation_skipped=1`. Rationale: a median/MAD rule needs ≥3 samples to tolerate one outlier (finding 2); averaging 1–2 unvetted updates under a 20% attacker rate is unsafe. Value 3 is the mathematical minimum, not tuned on results.
Files: `src/config.py` (field + validation), `src/experiment.py` (3 guarded lines + one new `round_metrics` column `aggregation_skipped`, 0 for all historical arms).
Deliberately **not** changed (no justified, interpretable fix yet): the MAD scale/threshold, surrogate generation, weight cap in the DP path (finding 1, only documented), selection policy, routing score. Reference and Corrected remain as historical comparators; new variants carry new names (`p7_corrected_guard`, `fail0p3_p7_corrected_guard`, `p7_delivery_guard`).

## 3. Verification (cheap tests only)
- `tests/test_phase7_guard.py` (6 tests): guard off ≡ guard never-binding (bitwise round metrics and model bytes); abstains exactly when 0<received<m (no surrogates, kept=0, zero server step); abstaining every round freezes the model; determinism; invalid value rejected; Phase 6C lock reproducible from the tag.
- Regression vs the Phase 6C tag (git worktree, synthetic data, reference and corrected configs): 81 numeric round-metric columns **identical** and `best`/`last` model bytes **identical**; only the new `aggregation_skipped` column is added.
- `tests/test_phase7_manifest.py` (2 tests): manifest locked, seeds 17-21 disjoint from 12-16, comparators are verbatim Phase 6C configs (same SHA-256), guard arms differ only by the guard.
- Real-config smoke (UNSW `fail0p3_p7_corrected_guard`, 4 rounds, seed 17): rounds with 1 and 2 received updates abstained, model unchanged, live log written.
- Fingerprint tests of Phase 6C (`test_phase6c_lock`, `test_live_logging`) now verify the locked tree from the git tag (Phase 7 intentionally changes `src/`, so the Phase 6C fingerprint `1273afef…` is no longer the working-tree fingerprint; the Phase 7 manifest has its own, `docs/phase7/EXPERIMENT_MANIFEST.json`).
- Full suite: 129 passed + the two fingerprint tests fixed + 8 new tests.

## 4. New tooling
`scripts/phase7/build_phase7.py` (configs + locked manifest), `scripts/phase7/run_phase7.py` (resumable sequential runner, dry-run by default, `results_phase7/`, own lock, verification, live logging), `configs/phase7/`, `docs/phase7/`.

## 5. Scientific stance
The guard is justified on mathematical grounds and is expected to help only in the minority of rounds with ≤2 real updates (6% of Corrected rounds); it may therefore change little. Whether it removes the Corrected instabilities is an **open, pre-registered question** for seeds 17-21 (see plan). If it does not, the correct conclusion is that Corrected's deficit has another cause or is an inherent trade-off, and no further algorithm change should be made without new evidence.
