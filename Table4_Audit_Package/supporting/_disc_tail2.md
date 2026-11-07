

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
