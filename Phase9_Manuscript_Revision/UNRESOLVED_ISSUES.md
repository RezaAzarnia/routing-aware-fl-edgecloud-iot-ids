# Unresolved scientific and editorial issues (the manuscript is NOT submission-ready)

## Scientific (cannot be closed without new experiments or authorization)
1. **Gaussian path**: the group-cap variant (`p8_corrected_gaussian_groupcap`) is implemented and unit-tested but **never run**; the Gaussian gap is not separable into noise and surrogate-share effects. Optional 15-run plan (≈22 min CPU, fresh seeds 22-26): `docs/phase8/NEXT_EXPERIMENT_PLAN.md`.
2. **Cause of Corrected's instability** not isolated (bundle of five changes, single-factor ablations only from Reference; no interaction tests). The guard hypothesis (few genuine updates) was tested and not supported.
3. **Attacker model**: one attack (sign-flip ×5, 20%), no sweep (10/30%), no adaptive/bounded attacker, no attacker-controlled routing score.
4. **No sensitivity analysis** for k, λ, momentum, caps, α, failure rate beyond 0.1/0.3; no resource/energy/memory measurements; no real testbed.
5. **Oracle routing**: the router ranks on the true delivery probability; an estimation-noise variant is not simulated. One simulated trace, identical for both datasets.
6. **Correlated route-quality/label-distribution scenario** (participation bias with accuracy impact) not simulated; per-client recall shows no penalty in the tested partitions.
7. **CICIoT2023**: unverified provenance, no device holdout, strong prior shift, AUC ceiling; weak discriminative power.
8. **Final-test evaluation not performed** (locked); FPR transfer of the validation-calibrated threshold is unknown; the earlier manuscript's very high UNSW-NB15 test FPR claims are neither confirmed nor refuted.
9. **Checkpoint selection after the metric audit**: re-selection impossible (per-round states not stored); 182/240 runs have <0.001 AUC gap between best and runner-up round.
10. **Statistics**: n=5, min exact p=0.0625, no multiplicity control, seeds 12-21 all inspected (no held-out confirmation seeds); seed 17 / part of seed 18 outcomes seen before Phase 7b completed.
11. **Privacy**: no certified DP; adjacency definition, sensitivity proof for the adaptive pipeline and a valid accountant (deterministic selection) absent. The paper says so.

## Literature / editorial
12. **References**: 35 original entries exist (Crossref-verified, 3 metadata corrections) plus 16 foundational entries; verification is title/metadata level — **abstracts/full texts were not read**. Weak-support entries (not cited in the new text where unsupported): `wang2024trust`, `bayat2025qlearning`. Foundational details marked "from memory" in `bibliography/verification_report.md` (page ranges for FedAvg, Krum, Yin, Fang; author lists of Zhu&Wang, Bonawitz, Agrawal) must be checked against the publisher records. Related-work gap claims are limited to the sources examined; no systematic literature search was done.
13. **Zenodo**: the DOI cited in the old paper predates Phase 6C/7/7b/8; a new deposit is required.
14. **Declarations**: funding, competing interests, author contributions, ethics statement missing; author list/affiliations unchanged from the old manuscript (to be confirmed by the authors).
15. **Target journal template and page limits** not applied (generic `elsarticle` preprint format).
16. **Native-language/style review** of the English text not done.
17. **Figures**: regenerated from ledger CSVs as PDF/SVG; fonts in SVG are text (not outlined); colour-blind check done only by palette choice.
