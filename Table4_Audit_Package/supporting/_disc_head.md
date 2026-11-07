# Table 4 discrepancies

**Important framing.** Table 4's values have no source (see `TABLE4_EVIDENCE_AUDIT.md`), so no "verified value" exists for them. "Verified value" below means the mean (SD over seeds 12–16) of the **closest executed arm of the locked validation-only study**, shown only to document where Table 4 and the executed evidence disagree. A difference is **not** an error measurement of Table 4, because the arms differ in configuration, partition and protocol. Rows for DP+FedAvg and Proposed ε≈20 are absent: no executed arm exists.

## A. Reasons that apply to the whole table (each is a documented mismatch)
| Code | Reason | Evidence |
|---|---|---|
| R1 | **No source:** no run IDs, seeds, result files, manifests or logs for any Table 4 value | `TABLE4_EVIDENCE_AUDIT.md` §2 |
| R2 | **Different evaluation partition:** Table 4 reports the official test files with a threshold from one validation set (original protocol); locked runs use the report partition of a three-way validation split, test never loaded | configs `test_csv`; README; manifests |
| R3 | **Different data split (CICIoT2023):** row-level split (940 260 / 151 362 / 300 000 rows) vs file-group-disjoint split (926 133 / 146 626 / 300 000); UNSW-NB15: validation split by random rows vs predictor-group-disjoint | manuscript l. 1352–1358; `docs/data_integrity` |
| R4 | **Baselines disable routing** (`routing.enabled=False` ⇒ random paths); the locked FedAvg/robust arms keep routed paths and only randomise selection | `src/suites.py@7c75b2d`; Phase 6C T6 matrix |
| R5 | **Unmatched network traces** in the original code (`trace_mode: sequential`); locked runs use matched traces | `src/network.py` |
| R6 | **Different code revisions:** median-bias fix, metric/threshold fix (affects thresholds equal to 1.0 and ROC ties), weight-cap and filter changes | `git diff 7c75b2d HEAD -- src` |
| R7 | **Different seeds:** planned 2–6 (no record) vs 12–16 | README; manifests |
| R8 | **Attacker assignment:** original random assignment vs exposure-controlled (20 % of selected clients) | configs |

## B. Table 4 values versus the closest executed arm (locked protocol; context only)
Mismatch codes per metric: detection (F1/AUC/FPR): R2, R3, R6, R7 (for UNSW FPR the gap is structural: test FPR 0.31–0.35 vs validation FPR capped at ≈ 0.15); network metrics of FedAvg and Robust no-DP: R4 (dominant), R5, R7; network metrics of Proposed ε≈10: R5, R7, R8 (within 0.6–9 %).

