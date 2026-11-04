# Limitations and open issues

## Confirmed integrity result
No confirmed implementation or data-integrity defect: 240/240 runs verified; all config hashes and artifact SHA-256 values match the locked manifest/COMPLETE records; no run loaded test data.

## Scientific limitations (confirmed)
- 5 seeds: minimum attainable exact two-sided p is 0.0625; all p-values are exploratory, uncorrected; non-significance ≠ equivalence.
- Evidence is validation-only; the threshold is tuned toward ~0.15 FPR, so FPR carries no information between arms.
- Reference and Corrected differ in several mechanisms at once; ablations are single-factor vs Reference only (no interaction/leave-one-out from Corrected).
- Undefended FedAvg baselines diverge by design; best-checkpoint reporting hides final-round collapse.
- Network trace is identical for UNSW and CIC (same seed/policy), a single simulated network.
- CIC: labels inferred from folder names; class-stratified row sampling (not file/device-held-out); pre-dedup feature-identical rows across splits (removed afterwards); AUC ceiling ≈0.996.
- Gaussian ε is diagnostic only; no certified DP.

## Open (untested hypotheses)
- Why Corrected loses real updates (fewer kept real updates per round: 4.63 vs 5.93) and whether weaker MAD filtering with few real updates explains accepted-malicious rates (23% vs 10.5% of received); not isolated.
- Why Corrected + Gaussian has surrogate weight share 0.476 vs 0.096 for Corrected (observed, unexplained).
- `LastAccessTime` of the locked final-test files was observed newer than the file preparation time during the run; the cause was not established (no config references them; `run_one.py` asserts `test_csv==""`; cloud mode requires them absent). Verify (e.g. antivirus/indexer) before any final-test evaluation.
- Retransmissions/ARQ and routing cost are only recorded as delay, PDR, route score and retransmission rounds; no energy or per-hop cost exists.

## Unavailable measurements (not inferred)
Per-update class-level metrics; routing energy cost; per-client malicious flag in the selection-frequency tables; final-test performance.
