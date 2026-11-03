# Phase 7b changelog (branch `research/phase7b-threshold-fix`, commit 9df1849 + this doc)

## Pause
The Phase 7 runner had already stopped (no process, no lock; log ends in `KeyboardInterrupt` during seed-18 `fail0p3_p7_corrected_guard`). **Preserved untouched: 13 verified Phase 7 runs + 1 incomplete directory (never deleted)** in `results_phase7/`; all 240 Phase 6C runs untouched. Git tags: `phase6c-final-results` (3029c6c), `phase7-guard-v1` (c64aff2).

## Bug (confirmed)
`select_decision_threshold` (src/metrics.py) picks a threshold on RAW scores and counts `score >= threshold`; `binary_classification_metrics` clipped scores to [1e-7, 1-1e-7] BEFORE the comparison. A selected threshold of exactly 1.0 (possible when the net saturates to float 1.0) therefore predicted nothing: false F1 = precision = recall = FPR = 0 (observed: `fail0p3_p7_corrected_guard` seed 17: 4,885 saturated scores, tp=fp=0). Clipping also created artificial ROC ties.
**Fix:** one rule, `raw score >= threshold` (scores only clipped to [0,1], a no-op for valid probabilities); the 1e-7 clip is applied only inside the log-loss (loss values unchanged). Threshold selection logic, constraints, calibration/report separation and training code are untouched. File changed: `src/metrics.py` (only source file).

## Tests
`tests/test_phase7b_threshold.py` (14 tests: saturated scores, threshold 1.0 and 0.0, ties, confusion-matrix agreement between selector and evaluator, calibration->report application, raw-score AUC, loss equals historical clipped log-loss, ordinary scores unchanged). 4 of them FAIL on the old code and pass on the fix. Full suite: **148 passed**. Fingerprint tests now verify frozen Phase 6C / Phase 7 code from the git tags.

## Training equivalence (old Phase 7 code vs Phase 7b)
Synthetic end-to-end runs (reference, corrected, corrected+guard under failures; old code via git worktree): all 37 training-side columns, `last_model_state.pt` bytes and validation AUC identical (max diff 0). Only evaluation-side numbers (threshold-dependent metrics, tie-affected AUC) can differ. Hence training is unchanged; evaluation of saved checkpoints can be repaired post hoc.

## Affected runs (separate files in `posthoc_threshold_fix/`; historical results unchanged)
Saved best/last checkpoints of all 240 Phase 6C + 13 Phase 7 runs were re-evaluated on the report partition (threshold re-selected on the calibration partition only; thresholds reproduced within 4e-3, i.e. float/batching noise).
- **Best-checkpoint metrics:** max |ΔAUC| = 0.0037 (mean 4e-5); |ΔF1| ≤ 0.001 in all 240 Phase 6C runs. Conclusions unchanged.
- **Last-round metrics:** 12 of 240 Phase 6C runs change by >1e-3 AUC (7 by >0.01); 9 change F1 (8 by >0.05). Largest: CIC `scenario_fedavg_topk` s12 last AUC 0.5000 -> 0.3118 (collapsed model's ties were hiding inverted ranking); `fail0p3_corrected` (CIC s13) last F1 0.0000 -> 0.9861 and `corrected` (UNSW s16) 0.0000 -> 0.8872 (the same threshold-1.0 defect in Phase 6C); UNSW `nat_corrected` s16 last AUC 0.5574 -> 0.7923. UNSW `corrected` mean last F1 0.7584 -> 0.9358; Reference arms unchanged. Phase 6C best-checkpoint F1 was never 0.
- **Phase 7 (old code):** `fail0p3_p7_corrected_guard` s17 best/last F1 0.0000 -> 0.8607; others unchanged to 4 decimals except corrected s17 last AUC 0.8662 -> 0.8757.
- **Checkpoint SELECTION:** training is identical, but best-round choice used the clipped AUC and per-round states were not saved, so re-selection cannot be reproduced post hoc. Round-to-round AUC gaps are tiny (best vs second-best round differs by <1e-3 in 182/240 Phase 6C runs), so some `best_round` choices may change under the repaired AUC (expected effect on reported best-checkpoint AUC is small: <=0.0037 for the saved checkpoints, unverified for alternatives). Phase 6C retraining is **not required for its conclusions** but its last-round F1/AUC for the 12 listed runs must be quoted from the corrected file; a full Phase 6C re-run (11.4 h) remains optional.
- **Phase 7 runs:** the 13 old runs cannot join the confirmatory analysis (different locked code). They are kept as historical, and **all Phase 7 runs are re-run under Phase 7b** (training bitwise equivalent, so this also gives a direct old-vs-new check).

## Phase 7b protocol
Manifest `docs/phase7b/EXPERIMENT_MANIFEST.json` (sha256 c5cb3735…, code fingerprint e93182e4…): identical design, seeds 17-21 and byte-identical configs as Phase 7; results in `results_phase7b/`. Disclosure: seed-17 (and part of seed-18) Phase 7 outcomes were seen while diagnosing the bug; the pre-registered criteria are unchanged and nothing was tuned. Mandatory tier = 40 UNSW runs (~1 h); CIC tier optional.
