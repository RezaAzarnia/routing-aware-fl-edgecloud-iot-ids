# Claim vs evidence matrix (validation-only evidence, 5 seeds, exploratory statistics)

| # | Possible manuscript claim | Verdict | Evidence (source: tables/aggregate_metrics.csv, paired_comparisons.csv) |
|---|---|---|---|
| 1 | Robust distance-filter aggregation protects FL-IDS against 20% sign-flip attackers | **Supported** | Undefended top-k FedAvg last-round AUC 0.604 (UNSW) / 0.500 (CIC) vs Reference 0.983 / 0.996; filter rejects 394/440 received malicious updates (89.5%) |
| 2 | Under attack the defended method matches clean FedAvg | **Supported, not proof of equivalence** | Δ best AUC +0.0005 UNSW (p=0.81), −0.0001 CIC; CI [−0.002, +0.003] |
| 3 | The corrected algorithm improves detection over the reference | **Not supported (contradicted)** | Δ best AUC −0.0090 UNSW (0/5 seeds better, p=0.0625), −0.0003 CIC |
| 4 | The corrected algorithm is more stable/resilient | **Not supported (contradicted)** | Last-round collapses in Corrected family: nat_corrected s16 0.557, fail0p3_corrected s13 0.770; Reference arms never collapsed |
| 5 | Routing-aware / top-k selection improves accuracy over random selection | **Not supported** | Reference vs uniform selection Δ −0.0023 (UNSW; Reference better 4/5, p=0.125), −0.0001 CIC |
| 6 | Coverage-aware selection improves fairness | **Supported (participation)** | Gini 0.73 → 0.49 (uniform 0.21); never-selected clients 27 → 8 of 50; no AUC cost (Δ −0.0009) |
| 7 | Packet-coupled delivery / ARQ improves resilience or delivery | **Not supported** | ctl_delivery_coupled Δ AUC −0.0050 UNSW, −0.0003 CIC (0/5, p=0.0625); update delivered 0.626 (Corrected) vs 0.848 (Reference); delay 268 vs 77 ms |
| 8 | Surrogate imputation improves resilience | **Not supported / inconclusive** | No-imputation control Δ −0.0016 UNSW, −0.0001 CIC (Reference slightly better, p>0.05); at f=0.3 Reference surrogate share 0.47 with negligible AUC change |
| 9 | Method tolerates client/network failures | **Supported for Reference only** | fail0p3_reference Δ −0.0017 (p=0.125); Corrected at f=0.3 degrades at last round |
| 10 | Gaussian perturbation gives measurable privacy with small accuracy cost | **Weakened**: cost measured, privacy not certified | AUC −0.042 UNSW, −0.003 CIC; ε≈10 is a diagnostic RDP estimate only; subsampling amplification invalid for deterministic selection |
| 11 | Certified / formal differential privacy | **Remove** | `epsilon_is_certified_guarantee=false`, `subsampling_amplification_valid=false` |
| 12 | High CIC accuracy shows strong generalization | **Not supported** | AUC≈0.996 ceiling for all protected arms; split limitations (labels from folders, row sampling, no device hold-out) |
| 13 | Results hold on locked final-test data | **Unproven** | Final-test never evaluated; do so only after explicit authorization |
| 14 | Statistical significance of any contrast | **Cannot be claimed** | n=5 ⇒ minimum exact p=0.0625; no multiplicity correction |
