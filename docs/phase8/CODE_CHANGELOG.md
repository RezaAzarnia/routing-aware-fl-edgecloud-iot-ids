# Phase 8 code changelog (branch `research/phase8-evidence-repair`, base 7e71889)

Historical code states are frozen by git tags: `phase6c-final-results`, `phase7-guard-v1`, `phase7b-final-results` (→ 7e71889, created in Phase 8, local only).
No result file, manifest or Phase 6C/7/7b config was modified. Reference, Corrected and Guard are unchanged.

## 1. Collective surrogate cap preserved in the central-DP path (CONFIRMED BUG → new default-off variant)
- Defect: with `central_client` privacy the per-client projection `capped_normalized_weights(…, 0.10)` is infeasible for <10 retained updates and becomes uniform, discarding `failure.surrogate_total_weight_cap`; realised surrogate share in `corrected_gaussian` 0.476 (UNSW) / 0.480 (CIC) vs 0.096 / 0.097 without DP (see SCIENTIFIC_EVIDENCE_AUDIT §B).
- Change: `src/privacy.py` `group_capped_normalized_weights()` (surrogate group receives min(raw share, cap); per-client cap applied inside each group; realised max share returned so the diagnostic noise scale stays consistent); `src/config.py` `privacy.preserve_surrogate_cap: bool = False`; `src/experiment.py` one guarded branch.
- Default off ⇒ every historical arm is bit-identical (tested end to end).
- New named variant (configs only, NOT run, NOT locked): `configs/phase8/{unsw,ciciot}_p8_corrected_gaussian_groupcap.yaml` (differ from the Phase 6C `corrected_gaussian` configs only by names, `output_dir: results_phase8` and the flag).
- Tests: `tests/test_phase8_group_cap.py` (7): flag default; old projection documented (surrogate share 0.5); cap enforced (≤0.10); smaller share not inflated; reduces to the old function without a mixed population; edge cases (1 real + 1 surrogate, invalid inputs); end-to-end smoke (flag omitted ≡ flag False bitwise over all numeric round metrics; flag True ⇒ surrogate share ≤0.10 whereas the historical path exceeds it).
- Historical effect: only `reference_gaussian` / `corrected_gaussian` (4 of 48 arm-datasets) are affected; their Gaussian-vs-non-Gaussian gap is not purely a noise cost. Conclusions on non-DP arms unchanged. Effect size of the fix: NOT established (no new training).

## 2. Test-infrastructure fix
`tests/test_phase7_manifest.py`: the Phase 7b manifest fingerprint is now verified from the frozen tag `phase7b-final-results` (as already done for Phase 6C and Phase 7), because Phase 8 legitimately changes `src/`. Consequence: resuming Phase 7b runs requires checking out that tag (the runner pre-flight compares the working-tree fingerprint).

## 3. Read-only audit tooling
`scripts/phase8/phase8_tables.py` (no training; writes `docs/phase8/tables/`):
T1 Phase 6C original vs audited by arm · T2a-c Phase 7b per-run, arm summary, paired contrasts (mean, SD, dz, t-interval, exact sign-flip p) · T3 communication (attempted / delivered / on-wire MB) and delivery vs PDR · T4 selection fairness, worst-client recall, attacker exposure · T5a surrogate weight shares and strict-cap infeasibility, T5b MAD behaviour by number of genuine updates · T6 baseline configuration matrix (UNSW configs).
Original metric tables are untouched; audited values live in separate files (`posthoc_threshold_fix/*` from Phase 7b and `docs/phase8/tables/*`).

## 4. Verified, no change needed
Preprocessing fit on training only (`src/data.py`); group-disjoint three-way split; empty-retained-set and zero-update behaviour; threshold single decision rule (Phase 7b).

## 5. Not changed on purpose
MAD scale/threshold, surrogate generation, selection policy, routing score, guard, default behaviour of every historical arm, logging columns (no new columns were needed; `surrogate_weight_share` already records the realised share).
## 6. Test status
Full suite: 155 passed (148 from Phase 7b + 7 new), run with `--basetemp=C:/cs/p8`.
