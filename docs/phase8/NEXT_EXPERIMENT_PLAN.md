# Next experiment plan (PROPOSED; nothing has been run; awaiting explicit authorization)

## Decision gate
**No new training is mandatory.** Existing Phase 6C (240 runs) and Phase 7b (40 runs) are sufficient to revise the manuscript with qualified claims. The optional Phase 7b CIC tier remains **STOP**: CIC is at an AUC ceiling, and the guard was inert in 4/5 UNSW seeds without injected failures.

## Optional single experiment (only if the Gaussian/privacy trade-off remains a headline claim)
**Why existing runs cannot answer it**: the Gaussian arms were run with the surrogate-cap defect (realised surrogate share 0.476 instead of ≤0.10), so the noise cost cannot be separated from the share inflation. The fix exists only in the new variant.

**Hypothesis (one)**: on UNSW with the same failures, attackers and matched network traces, preserving the collective surrogate cap in the central-DP path (`p8_corrected_gaussian_groupcap`) increases best-checkpoint ROC-AUC relative to the current `corrected_gaussian`.

**Design**: UNSW only; fresh confirmation seeds **22-26** (seeds 12-21 were inspected); 3 arms × 5 seeds = **15 runs**:
1. `corrected` (non-DP control; unchanged config),
2. `corrected_gaussian` (current implementation; unchanged config),
3. `p8_corrected_gaussian_groupcap` (`configs/phase8/unsw_p8_corrected_gaussian_groupcap.yaml`).
All other settings identical (routing `coverage_aware`, `packet_coupled`, sign-flip scale 5.0 at 20%, failure p=0.1, diagnostic ε target 10, 30 rounds, `validation_only`, CPU). Paired by seed.

**Success criteria (fixed before any run)**: supported only if ALL hold: (a) mean paired Δ best AUC (arm 3 − arm 2) ≥ +0.005 with arm 3 better in ≥4/5 seeds; (b) realised surrogate share ≤0.10 in 100% of rounds with surrogates for arm 3 (mechanistic check); (c) collapse count (last-round AUC<0.90 or max loss>100) not higher than arm 2; (d) best-checkpoint F1 not lower by more than 0.005. Otherwise report "not supported". Report best AND last round, per-seed values, exact sign-flip p (n=5 ⇒ min p 0.0625: exploratory). Gaussian ≠ certified DP; the diagnostic noise scale changes with the realised max share and must be reported.

**Cost (from recorded durations, CPU i5-14400F, sequential)**: UNSW mean 90.2 s (corrected), 84.6 s (corrected_gaussian), assumed ≈85 s for the new arm ⇒ 5 × 260 s ≈ 1,300 s ≈ **22 minutes**. An optional CIC replication would add ≈ 5 × (188 + 178 + ≈178) s ≈ 45 min (not recommended).

**Infrastructure to add after authorization**: `scripts/phase8/build_phase8.py` (locked manifest with a code fingerprint from this branch), reuse of the interruption-safe runner `scripts/phase7/run_phase7.py` (`--manifest`, `--results results_phase8`), outputs in `results_phase8/` only, resumable, verified `COMPLETE.json`, live monitoring with `scripts\live\monitor_live.ps1`.

**Authorization request**: the 15-run experiment above, ≈22 min CPU, no paid compute. Not started.
