# Unresolved scientific limitations and open items

1. **Adaptive attackers not evaluated** (reviewer comment 12 remains PARTIAL). Only static sign-flip, norm-preserving sign-flip and label-flip attacks; the latter two are harmless in this setup, and MAD keeps ≈79–80 % of norm-preserving flips.
2. **No formal differential privacy.** ε values are diagnostic RDP estimates under an assumed Poisson-subsampling model; release-based vs attempted-round estimates are reported (9.86/9.43 vs 9.9993 with abstention).
3. **Surrogate benefit not demonstrated.** Surrogates carry ≈30 % of the DP-pipeline weight, 2.8 % of rounds are surrogate-only; imputation ON vs OFF shows no detectable detection gain. Mechanism unmeasured (aggregate-direction differences were never logged).
4. **Clean-data parity.** Without an attack the proposed pipeline is indistinguishable from FedAvg; MAD rejects 5–7 % of honest updates.
5. **Fairness result is unfavourable to "fairer selection".** Uniform selection did not improve worst-client held-out recall (UNSW −0.138 [−0.260, −0.015], 5/5 seeds lower; interval unadjusted, exact p = 0.0625); it increased surrogate-only rounds to 38–41 %.
6. **Resolution:** n = 5 (CICIoT2023 sensitivity and all scalability n = 3). About 1,700 unadjusted comparisons; 338 intervals exclude 0; no significance claim.
7. **Protocol separation:** CICIoT2023 participation exists only under the SUPP_V2 client holdout; not comparable to earlier CICIoT2023 runs.
8. **Disclosed design caveat:** the coupled-network driver uses holdout labels in link quality (max |Δ| all-rows vs training-only 0.027, CIC seed 12).
9. **Data provenance:** CICIoT2023 files are byte-equivalent to a third-party release; official UNB provenance unverified. Reserved test sets were never evaluated.
10. **Costs:** wall-clock/CPU from a shared host; bytes simulated.
11. **Seeds of existing Figs 3–6 unresolved** (`FIGURES_3_6_SEED_PROVENANCE.md`).
12. **Bibliography:** structurally consistent (35/35), but 22 of 35 entries have neither DOI nor URL and no claim-level verification was done (`BIBLIOGRAPHY_VERIFICATION.md`).
13. **Archive:** Zenodo v1.0.4 and v.1.0.5 exist; neither contains the supplementary experiments; no new release was made.
14. **Author declarations missing** from the manuscript: funding, competing interests, CRediT author contributions, ethics/data-use statement — not invented here.
15. Reused Phase 6C detection metrics rely on the audited ledger (AP unaudited). Phase 6C `ctl_imputation_*` evidence is on the Phase 6C protocol, not Table 4 v2.
