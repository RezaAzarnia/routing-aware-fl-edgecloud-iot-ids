# Privacy-claim feasibility assessment (Phase 6B) — no certified epsilon is reported

## Categories kept separate
| | Mechanism | Status |
|---|---|---|
| A | No Gaussian perturbation | Baseline; no privacy claim. |
| B | Existing central Gaussian noise on the clipped, weight-capped aggregate | **Empirical / diagnostic epsilon only.** |
| C | A DP-compatible variant (specified below) | Specification only; not implemented, no epsilon reported. |

## Why B cannot be presented as a certified guarantee (measured / tested)
1. **Selection is not Poisson subsampling.** Deterministic top-k routing selected 3 clients in 30/30 rounds and never selected 24 of
   50 (Phase 6A). The accountant assumes q = 10/50 = 0.2. With the same noise multiplier (0.994) and q = 1 the same RDP routine gives
   ε ≈ 41.9 instead of 10.0. Without amplification, ε = 10 would need a noise multiplier of ≈ 3.12 (≈ 3.1× more noise) and ε = 20 ≈ 1.78
   (`noise_multiplier_requirements.json`).
2. **Data-dependent robust filtering.** The distance filter keeps/rejects clients using statistics of *all* updates; changing one client can change
   which other clients are rejected, so the influence of one client on the release is not bounded by `clip × weight`.
3. **Surrogate imputation.** The coordinate median is recomputed when one client is added/removed, so the aggregate changes beyond
   `clip × max_weight_share` (`test_surrogate_imputation_violates_the_assumed_add_remove_sensitivity`: 100/100 random trials violate it).
4. **Adaptive, data-dependent weights.** Weights are proportional to local sample counts and renormalised over the *retained* updates;
   a strict cap of 0.1 is mathematically impossible when fewer than 10 updates are retained (observed 6–9; `weight_cap_infeasible_strict`).
5. **Adjacency.** The configuration uses `adjacency_factor = 1.0`; with replace-one adjacency the sensitivity is 2·clip·w.
6. A surrogate majority can also collapse the MAD filter and discard all real updates (documented defect, tested).

## Category C — formal specification of a DP-compatible mechanism
* **Adjacency:** add/remove of one client's entire local dataset (user-level).
* **Participation:** each client is included in round t independently with probability q, drawn from *secret* randomness independent of the data
  and of the route state (Poisson sampling). Route quality may only enter if it defines fixed, data-independent probabilities; deterministic top-k
  selection is excluded (no amplification, q = 1 accounting would apply).
* **Per-client contribution:** Δ_i clipped to norm C.
* **Aggregation:** fixed-denominator sum  Ĝ = (1/(qN)) Σ_{i∈S_t} Clip_C(Δ_i) + N(0, σ²C²/(qN)² I) — weights are public constants, not sample counts.
* **Failures / missing updates:** dropped (variant A); any substitute must be a function of already-released (noised) quantities only (post-processing).
  Coordinate-median surrogates computed from private updates are excluded.
* **Robustness:** the data-dependent distance filter is excluded from the private path (clipping provides bounded influence). A robust aggregator can
  only be used if applied to the already-noised release (post-processing) or if its sensitivity is separately bounded.
* **Server momentum / learning rate:** post-processing, no extra cost.
* **Accountant:** RDP of the Poisson-subsampled Gaussian (integer-order formula already in `src/privacy.py`) composed over T = 30 releases, converted to (ε, δ).

## Feasibility verdict
A valid proof and implementation are **feasible only for the restricted variant C** above, which is a different algorithm (random secret sampling,
clipping-only, no surrogate, no data-dependent filter). The proposed routing-aware robust method, as implemented, is **not covered** by any
accounting. Recommended manuscript scoping: describe the Gaussian step as an *empirical noise-injection defence with a diagnostic RDP estimate
that assumes Poisson sampling*, state that deterministic routing, data-dependent filtering and surrogate imputation are outside the analysis, and make
no certified-DP claim. Variant C was **not implemented** in Phase 6B (a design decision for the authors).
