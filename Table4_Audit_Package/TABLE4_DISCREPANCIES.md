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

| dataset | method | metric | manuscript | locked_analog | locked_mean | locked_sd | difference | relative_pct |
|---|---|---|---|---|---|---|---|---|
| ciciot | FedAvg | F1 | 0.9921 | scenario_fedavg_random | 0.9904 | 0.0010 | 0.0017 | 0.2000 |
| ciciot | FedAvg | ROC-AUC | 0.9935 | scenario_fedavg_random | 0.9930 | 0.0015 | 0.0005 | 0.1000 |
| ciciot | FedAvg | FPR | 0.1453 | scenario_fedavg_random | 0.1400 | 0.0108 | 0.0053 | 3.8000 |
| ciciot | FedAvg | Delay (ms) | 89.3400 | scenario_fedavg_random | 71.2721 | 5.0589 | 18.0679 | 25.4000 |
| ciciot | FedAvg | PDR | 0.7364 | scenario_fedavg_random | 0.7818 | 0.0319 | -0.0454 | -5.8000 |
| ciciot | FedAvg | Path stability | 0.5601 | scenario_fedavg_random | 0.8545 | 0.0228 | -0.2944 | -34.5000 |
| ciciot | FedAvg | Transfer efficiency (Mbit/s) | 6.8100 | scenario_fedavg_random | 9.3832 | 0.5802 | -2.5732 | -27.4000 |
| ciciot | Robust no-DP | F1 | 0.9939 | robust_random_no_imputation | 0.9933 | 0.0003 | 0.0006 | 0.1000 |
| ciciot | Robust no-DP | ROC-AUC | 0.9961 | robust_random_no_imputation | 0.9962 | 0.0003 | -0.0001 | -0.0000 |
| ciciot | Robust no-DP | FPR | 0.1478 | robust_random_no_imputation | 0.1473 | 0.0122 | 0.0005 | 0.3000 |
| ciciot | Robust no-DP | Delay (ms) | 89.6300 | robust_random_no_imputation | 71.2721 | 5.0589 | 18.3579 | 25.8000 |
| ciciot | Robust no-DP | PDR | 0.7275 | robust_random_no_imputation | 0.7818 | 0.0319 | -0.0543 | -6.9000 |
| ciciot | Robust no-DP | Path stability | 0.5466 | robust_random_no_imputation | 0.8545 | 0.0228 | -0.3079 | -36.0000 |
| ciciot | Robust no-DP | Transfer efficiency (Mbit/s) | 6.7600 | robust_random_no_imputation | 9.3832 | 0.5802 | -2.6232 | -28.0000 |
| ciciot | Proposed eps~10 | F1 | 0.9919 | reference_gaussian | 0.9911 | 0.0004 | 0.0008 | 0.1000 |
| ciciot | Proposed eps~10 | ROC-AUC | 0.9934 | reference_gaussian | 0.9930 | 0.0014 | 0.0004 | 0.0000 |
| ciciot | Proposed eps~10 | FPR | 0.1453 | reference_gaussian | 0.1407 | 0.0184 | 0.0046 | 3.3000 |
| ciciot | Proposed eps~10 | Delay (ms) | 65.5100 | reference_gaussian | 65.9000 | 6.1851 | -0.3900 | -0.6000 |
| ciciot | Proposed eps~10 | PDR | 0.8358 | reference_gaussian | 0.8511 | 0.0146 | -0.0153 | -1.8000 |
| ciciot | Proposed eps~10 | Path stability | 0.9124 | reference_gaussian | 0.9231 | 0.0070 | -0.0107 | -1.2000 |
| ciciot | Proposed eps~10 | Transfer efficiency (Mbit/s) | 9.9200 | reference_gaussian | 10.9356 | 0.8955 | -1.0156 | -9.3000 |
| unsw | FedAvg | F1 | 0.7754 | scenario_fedavg_random | 0.7217 | 0.2069 | 0.0537 | 7.4000 |
| unsw | FedAvg | ROC-AUC | 0.8542 | scenario_fedavg_random | 0.8752 | 0.0863 | -0.0210 | -2.4000 |
| unsw | FedAvg | FPR | 0.3456 | scenario_fedavg_random | 0.1464 | 0.0158 | 0.1992 | 136.1000 |
| unsw | FedAvg | Delay (ms) | 99.0400 | scenario_fedavg_random | 81.5278 | 5.5757 | 17.5122 | 21.5000 |
| unsw | FedAvg | PDR | 0.7350 | scenario_fedavg_random | 0.7818 | 0.0319 | -0.0468 | -6.0000 |
| unsw | FedAvg | Path stability | 0.5579 | scenario_fedavg_random | 0.8545 | 0.0228 | -0.2966 | -34.7000 |
| unsw | FedAvg | Transfer efficiency (Mbit/s) | 11.1100 | scenario_fedavg_random | 14.9304 | 0.8362 | -3.8204 | -25.6000 |
| unsw | Robust no-DP | F1 | 0.8383 | robust_random_no_imputation | 0.9526 | 0.0026 | -0.1143 | -12.0000 |
| unsw | Robust no-DP | ROC-AUC | 0.9281 | robust_random_no_imputation | 0.9825 | 0.0018 | -0.0544 | -5.5000 |
| unsw | Robust no-DP | FPR | 0.3463 | robust_random_no_imputation | 0.1431 | 0.0143 | 0.2032 | 141.9000 |
| unsw | Robust no-DP | Delay (ms) | 98.3300 | robust_random_no_imputation | 81.5278 | 5.5757 | 16.8022 | 20.6000 |
| unsw | Robust no-DP | PDR | 0.7183 | robust_random_no_imputation | 0.7818 | 0.0319 | -0.0635 | -8.1000 |
| unsw | Robust no-DP | Path stability | 0.5438 | robust_random_no_imputation | 0.8545 | 0.0228 | -0.3107 | -36.4000 |
| unsw | Robust no-DP | Transfer efficiency (Mbit/s) | 11.1300 | robust_random_no_imputation | 14.9304 | 0.8362 | -3.8004 | -25.5000 |
| unsw | Proposed eps~10 | F1 | 0.8106 | reference_gaussian | 0.9005 | 0.0335 | -0.0899 | -10.0000 |
| unsw | Proposed eps~10 | ROC-AUC | 0.8801 | reference_gaussian | 0.9419 | 0.0166 | -0.0618 | -6.6000 |
| unsw | Proposed eps~10 | FPR | 0.3145 | reference_gaussian | 0.1488 | 0.0102 | 0.1657 | 111.3000 |
| unsw | Proposed eps~10 | Delay (ms) | 74.5300 | reference_gaussian | 76.6499 | 6.5535 | -2.1199 | -2.8000 |
| unsw | Proposed eps~10 | PDR | 0.8348 | reference_gaussian | 0.8511 | 0.0146 | -0.0163 | -1.9000 |
| unsw | Proposed eps~10 | Path stability | 0.9118 | reference_gaussian | 0.9231 | 0.0070 | -0.0113 | -1.2000 |
| unsw | Proposed eps~10 | Transfer efficiency (Mbit/s) | 15.9400 | reference_gaussian | 17.2382 | 1.0719 | -1.2982 | -7.5000 |

Reading of Section B: for Proposed ε≈10 the network metrics lie 0.6–9 % from the closest executed arm (same simulator family); detection metrics on CICIoT2023 lie within 0.002 for F1/AUC and within 0.006 for FPR (ceiling effect: all robust arms are ≈ 0.993–0.996 AUC, so CICIoT2023 cannot discriminate between methods); on UNSW-NB15 the F1/AUC of Robust no-DP and Proposed ε≈10 are 0.05–0.11 below the executed arms (FedAvg F1 is 0.054 above, AUC 0.021 below, with SD 0.2/0.09 across seeds), and FPR is 2.1–2.4× the validation value for all three (different partition). For FedAvg and Robust no-DP the network metrics are 20–36 % **worse** than the executed random-selection arms because those baselines also lose routed paths (R4).

## C. Claims repeated in the Abstract, Results and Conclusion
Arithmetic recomputed from Table 4 (not from experiments); provenance of the inputs is NOT VERIFIED.

| claim | location | manuscript_pct | recomputed_from_table4_pct | arithmetic_status | provenance_status |
|---|---|---|---|---|---|
| CICIoT2023 delay reduction vs FedAvg | Results (Proposed eps~20) | 26.6000 | 26.5800 | REPRODUCES | NOT VERIFIED (inputs unsourced) |
| CICIoT2023 PDR increase vs FedAvg | Results | 13.4000 | 13.3600 | REPRODUCES | NOT VERIFIED (inputs unsourced) |
| CICIoT2023 path-stability increase vs FedAvg | Results | 62.8000 | 62.8100 | REPRODUCES | NOT VERIFIED (inputs unsourced) |
| CICIoT2023 transfer-efficiency increase vs FedAvg | Results | 46.0000 | 45.8100 | DIFFERS | NOT VERIFIED (inputs unsourced) |
| UNSW-NB15 F1 improvement vs FedAvg | Results/Conclusion (eps~20) | 8.3000 | 8.3200 | REPRODUCES | NOT VERIFIED (inputs unsourced) |
| UNSW-NB15 ROC-AUC improvement vs FedAvg | Results/Conclusion | 6.6000 | 6.6400 | REPRODUCES | NOT VERIFIED (inputs unsourced) |
| UNSW-NB15 delay reduction vs FedAvg | Results/Conclusion | 24.7000 | 24.6800 | REPRODUCES | NOT VERIFIED (inputs unsourced) |
| UNSW-NB15 path-stability increase vs FedAvg | Results/Conclusion | 63.5000 | 63.4500 | REPRODUCES | NOT VERIFIED (inputs unsourced) |

## D. Other manuscript-versus-evidence discrepancies found during the audit
| Item | Manuscript | Evidence | Reason |
|---|---|---|---|
| Abstract vs Table 4 (UNSW-NB15 undefended FedAvg ROC-AUC) | Abstract 0.8752–0.8870; Table 4 FedAvg 0.8542 | Executed: `scenario_fedavg_random` 0.8752, `scenario_fedavg_topk` 0.8870 (locked) | Two different experimental programmes in one paper (R2, R4, R7) |
| Abstract vs Methods | "240 validation-only runs" | Methods l. 1366–1371: seeds 2–6 and "applied unchanged to the test set" | Contradictory protocol statements |
| Transfer efficiency gain | 46.0 % | 45.8 % from Table 4's own numbers | Rounding or different inputs; minor |
| Modular Edge FL-inspired, MCHFL-style | "were compared" (l. 1283–1290, 1960) | no code, config or result | Not executed |
| Proposed ε≈20, DP+FedAvg | in Table 4 and the privacy-cost table | no executed arm in any locked phase; no UNSW ε≈20 config | Missing experiment/provenance |
| Privacy-cost table ε (9.58 CIC, 9.91 UNSW) | Table of privacy cost | locked `reference_gaussian`: ε̂ 9.9993 (planned and final); NSR 23.53 (CIC), 35.29 (UNSW) vs 25.28, 37.48 | Different runs/code; unsourced |
| Privacy-cost communication numbers | 23.08–25.75 MB (CIC), 32.83–52.39 MB (UNSW) | executed: attempted payload 28.61 MB (CIC), 52.36 MB (UNSW) for every arm; delivered 24.26 / 44.40 MB (reference_gaussian) | Only 28.61 and 52.39≈52.36 are consistent; other values match neither definition |
| Ablation "No Server Momentum" (η_s = 1.0) | text l. 2289 | controlled study: momentum 0 with unchanged η_s = 0.5 is neutral; η_s = 5 collapses the last round; the original variant changed two factors | Confounded ablation |
| Failure-resilience figure | "PDR and delay remain stable … routing-aware selection limits the effect" | executed runs: PDR and delay are bit-identical for failure probability 0, 0.1, 0.3 (explicit failures do not change the network trace); baseline network failures (≈ 15 %) are present at "0 %" | Construction artefact, see Figure 9 audit |
