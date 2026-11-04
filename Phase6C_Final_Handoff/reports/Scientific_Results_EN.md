# Phase 6C — Scientific Results (English)

All numbers are computed from `tables/all_runs.csv` (source: the 240 verified run folders). Metrics are on the **report partition** of a three-way, group-disjoint validation split (calibration -> threshold; selection -> best checkpoint; report -> numbers below). **No locked final-test data were used** (`test_data_loaded=False` in all 240 runs, protocol `validation_only`). "Best" = report-partition metrics at the checkpoint chosen on the selection partition; "Last" = round 30.

## 1. Completion and integrity
240/240 runs verified (120 UNSW-NB15, 120 CICIoT2023; 24 arms x seeds 12-16). For every run: `COMPLETE.json` present, no `FAILED.json`, `config_sha256` equals the locked manifest (`c648b935...f267`), code fingerprint equals the manifest (`1273afef...`), and every artifact SHA-256 listed in `COMPLETE.json` was recomputed and matched. No duplicate/unexpected run folders; no non-finite core metrics. Details: `provenance/verification.json`, `run_inventory.csv`.

## 2. Main results (5 seeds, mean ± SD, best-checkpoint AUC; last-round AUC in brackets)
| Arm | UNSW AUC | UNSW F1 | UNSW recall_adr | CIC AUC | CIC F1 |
|---|---|---|---|---|---|
| Clean centralized | .9911±.0005 [.9912] | .962 | .989 | .9974±.0002 [.9973] | .995 |
| Clean FedAvg | .9843±.0029 [.9825] | .954 | .973 | .9962±.0004 [.9960] | .993 |
| FedAvg random, attack, no defence | .8752±.0863 [.6568] | .722 | .636 | .9930±.0015 [.5516] | .990 |
| FedAvg top-k, attack, no defence | .8870±.0856 [.6043] | .771 | .700 | .9813±.0211 [.5002] | .979 |
| Robust random, no imputation | .9825±.0018 [.9771] | .953 | .971 | .9962±.0003 [.9958] | .993 |
| **Reference** | .9838±.0029 [.9826] | .954 | .975 | .9962±.0003 [.9960] | .993 |
| **Corrected** | .9749±.0069 [.9669] | .948 | .964 | .9960±.0003 [.9949] | .993 |
| Reference + Gaussian | .9419±.0166 [.9285] | .901 | .878 | .9930±.0014 [.9931] | .991 |
| Corrected + Gaussian | .9405±.0221 [.8890] | .897 | .871 | .9939±.0010 [.9939] | .991 |

FPR is 0.14-0.15 for essentially every arm (threshold rule), so FPR is not a discriminating quality measure. All 24 arms, per-seed values, min/max: `tables/aggregate_metrics.csv`.

## 3. Reference vs Corrected (paired by seed)
| | Δ AUC (Corr−Ref) mean | 95% t-CI | seeds Corrected better | exact Wilcoxon p | d_z |
|---|---|---|---|---|---|
| UNSW best | −0.0090 | [−0.0163, −0.0016] | 0/5 | 0.0625 | −1.51 |
| UNSW last | −0.0157 | [−0.0447, +0.0133] | 0/5 | 0.0625 | −0.67 |
| CIC best | −0.0003 | [−0.0007, +0.0001] | 1/5 | 0.1875 | −0.83 |
| CIC last | −0.0011 | [−0.0025, +0.0004] | 1/5 | 0.1875 | −0.93 |
Natural attackers (UNSW): Δ best −0.0144 (1/5 better, p=0.31), Δ last −0.0926. Failure 0.3 (UNSW): Δ best −0.0183 (0/5, p=0.0625), Δ last −0.0885; CIC last Δ −0.0198 (0/5).
**Reading:** Corrected is not better anywhere; Reference is better or equal in every contrast. With n=5 the smallest attainable exact p is 0.0625, so no p<0.05 claim is possible; the consistent sign (5/5 on UNSW) and effect size are *exploratory* evidence. Differences on CIC are within noise.
Reference and Corrected differ in several mechanisms simultaneously (coverage-aware selection, packet-coupled delivery with ARQ, real-only filter, post-filter surrogates, surrogate cap 0.10) — it is **not** a single-factor comparison.
Mechanism evidence (UNSW): real updates kept per round 4.63 vs 5.93 (Δ −1.29, 5/5), surrogate weight share 0.096 vs 0.221, mean PDR 0.834 vs 0.851, mean delay 267.6 vs 76.6 ms (5/5). Malicious updates accepted per run: 8.2 vs 6.2 (not significant, p=0.31); of malicious updates *received*, the filter accepted 10.5% (Reference, 46/440) vs 23% (Corrected, 72/312) across 10 runs. These are correlations, not isolated causes.

## 4. Controlled ablations (Reference baseline; Δ best AUC, UNSW / CIC)
uniform selection −0.0023 / −0.0001; coverage selection −0.0009 / −0.0001; no imputation −0.0016 / −0.0001; surrogate cap 0.10 −0.0003 / 0.0000; real-only + post-filter −0.0017 / −0.0001; packet-coupled delivery −0.0050 / −0.0003 (CIC 0/5, p=0.0625); uniform weights −0.0038 / −0.0003; momentum0 lr0.5 −0.0010 / 0.0000; momentum0 lr5.0 −0.0041 / −0.0036 (last-round collapse: 3/5 CIC runs diverged). No single factor reproduces the Corrected deficit (−0.0090); the existing ablations cannot attribute it (interactions untested). Figure 12.

## 5. Robustness to malicious clients (20% sign-flip)
Undefended FedAvg collapses: last-round AUC 0.657/0.604 (UNSW) and 0.552/0.500 (CIC); 18 of these 20 runs reach loss >100 (UNSW random: 3/5; the other three arm-datasets 5/5), and all 20 end with last-round AUC ≤0.80. All 10 undefended arm-datasets accept 100% of received malicious updates (e.g. 440/440). The MAD distance filter with server momentum (Robust-random, Reference) restores AUC to 0.98 (UNSW) / 0.996 (CIC) and rejects 89.5% of received malicious updates (Reference 394/440). Reference vs undefended top-k: Δ best AUC +0.0968 (5/5, p=0.0625); last-round Δ +0.378. Note: no "clean FedAvg vs Reference" gap: Δ best AUC −0.0005, p=0.81 (not evidence of equivalence).

## 6. Routing and selection
Evidence that routing/selection *policy* improves detection is **absent**: Reference (deterministic top-k) vs uniform-random selection (`ctl_selection_uniform`) Δ best AUC −0.0023 (UNSW, Reference better in 4/5; p=0.125), −0.0001 (CIC). Top-k is the least fair policy: selection Gini 0.73 (27 of 50 clients never selected on average) vs 0.49 (coverage-aware; 8 never) vs 0.21 (uniform; 0). Coverage-aware selection fixes participation fairness without a measurable AUC change (Δ −0.0009, p=0.44). Natural vs exposure-controlled attacker assignment: Reference Δ +0.0004 (UNSW), +0.0001 (CIC), p>0.3.
Network: mean PDR 0.851 (top-k) vs 0.782 (uniform) vs 0.834 (coverage/Corrected). Failure sensitivity (Reference): f=0.0 Δ +0.0003, f=0.3 Δ −0.0017 (UNSW, p=0.125) — learning is insensitive to failures up to 0.3 for Reference; Corrected at f=0.3 degrades at the last round. The simulated network trace depends only on seed/policy, so CIC and UNSW network numbers are identical (difference 0.0): they are not independent evidence. Retransmissions exist only in packet-coupled arms (≈1.8 rounds/event). Communication cost (bytes on wire, UNSW mean): FedAvg-type arms 52.4 MB; Corrected 62.9 MB (+20%).

## 7. Gaussian perturbation
AUC cost vs non-noised: Reference −0.0419 (UNSW, 5/5, d_z −3.06), −0.0032 (CIC, 5/5); Corrected −0.0343 / −0.0021. Diagnostic RDP epsilon recorded ≈ 10.0 (δ=1e-5). **This is not certified differential privacy**: the accountant assumes subsampling amplification that deterministic top-k / coverage-aware selection does not provide (`subsampling_amplification_valid=false`, `epsilon_is_certified_guarantee=false` in `privacy_plan.json`). Treat as an empirical noise-injection study only.

## 8. Divergence and stability
Collapsed or diverged runs (last-round AUC <0.8 or loss >100): undefended FedAvg random/top-k (all 10 + 10), CIC momentum0-lr5.0 (3/5), and in the proposed family: UNSW Corrected+Gaussian seed 16 (last AUC 0.686), nat_corrected seed 16 (0.557; best checkpoint at round 6), fail0p3_corrected seed 13 (loss 1188, last AUC 0.770), nat_selection_uniform seed 15 (0.781). The four Reference-family arms (reference, nat_, fail0p0_, fail0p3_) never exceeded a per-run maximum training loss of 3.3 (UNSW) / 1.2 (CIC) and never collapsed; single-factor controls collapsed only for momentum0-lr5.0 on CIC (3/5). Best-checkpoint selection masks these collapses, so report best **and** last-round numbers. Figure 5, 11.

## 9. CIC credibility
CIC AUC ≈0.996 for every protected arm with differences <0.001 — near ceiling, little discriminative power between methods. Known limitations (from `preparation_metadata.json`): labels inferred from class folder names; class-stratified row sampling, not file/device-held-out; feature-identical rows were present across splits before deduplication (25,568 train/val, 34,142 train/test, 32,169 val/test sampled-row hash overlaps → 0 after dedup); no device identifiers. Hence CIC results are probably optimistic and should not be presented as independent-device generalization.

## 10. Limitations / threats to validity
n=5 seeds (min p=0.0625; no multiplicity correction; all tests exploratory); validation-only evidence — no final-test evaluation was performed; single simulated network; threshold tuned to ~0.15 FPR; CIC split independence; Corrected is a bundle of mechanisms; unexplained observation: surrogate weight share is 0.476 for Corrected+Gaussian vs 0.096 for Corrected (not investigated).

## 11. Claim vs evidence (summary; full matrix in `Manuscript_Claim_Evidence_Matrix.md`)
Supported: robust aggregation protects against sign-flip; Reference ≈ clean FedAvg under attack; Gaussian costs accuracy. Not supported: Corrected improves detection/stability; routing/selection policy improves accuracy; any DP guarantee; CIC generalization.
