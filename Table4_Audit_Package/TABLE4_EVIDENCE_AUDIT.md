# Table 4 evidence audit (audit only; nothing modified, nothing rerun, test data not accessed)

Audit date: 2026-11-07. Manuscript source audited: `Desktop/essay/main paper/main.tex` (modified 2026-11-05 10:28), Table 4 = `\label{tab:overall-results}` (line 2081), Table 3 = `tab:framework-parameters` (line 1684). **The newer manuscript with the integrated controlled-ablation section is not on this machine**; the file above still contains the old ablation figures/table and no controlled-ablation text. If your revised file has a different Table 4, the conclusions below on provenance still hold only if its values equal those parsed here (the parser reads the table from source; see `build_table4_audit.py`).

## Verdict
**Table 4 is NOT VERIFIED for any of its 70 values (5 methods × 2 datasets × 7 metrics), and it cannot remain unchanged.** No executed run, result file, manifest, log, or archive on this machine, in the Git history (33 commits, all branches), in the four ZIP archives, or in the cited Zenodo archive contains its values. The values are also incompatible with the validation-only protocol that the Abstract describes. Details below.

## 1. Authoritative implementation
| Item | Finding |
|---|---|
| Repository | `Desktop/essay/routing-aware-fl-edgecloud-iot-ids`, branch `main`, HEAD `1df63f3` (2026-11-04) |
| Working tree | No tracked-file changes. Untracked: `configs/ablation_v2/`, `scripts/ablation_v2/`, `scripts/audit_table4/`, `Table4_Audit_Package/` (new); ignored result directories (`results_*`) hold the run data |
| Manuscript | Table 4 and the performance figures (fig3–fig8) come from the **original July 2026 study**, not from any locked phase (see §2) |
| Original code | Commit `7c75b2d` (2026-07-02, "initial commit"): `src/`, `configs/`, `scripts/windows/*.bat`, README with the reproduction commands. The Zenodo archive (DOI 10.5281/zenodo.21131047) is a 101 KB download of exactly this commit, **code only, no results** |
| Later code | `5e1e237` even-count median bias fix and DP+median rejection (2026-11-01); `b32242c` data repair/dedup; Phases 5–6C validation-only protocol (`9b87869`, locked manifest `d126e2d`); `f935ee0` matched network traces and packet-coupled delivery; `9df1849` single decision rule for thresholds (metric fix); `740a166` collective surrogate cap; Phase 10 default-off additions. `git diff 7c75b2d HEAD -- src` changes 11 files (+1408/−63 lines): aggregation, config, data, experiment, metrics, network, partitioning, privacy |
| Which code produced which results | Table 4 / figs 3–8, ablation figs, failure figure: **original code (≈ `7c75b2d`) — inferred** from the README and the old suite definitions; there is **no run record** to confirm it. Locked 240 Phase 6C runs (seeds 12–16): manifest code fingerprint `1273afef…` (commit chain `9b87869`→`d126e2d`). Phase 7/7b: seeds 17–21. Controlled ablation v2 (this study's 40 runs): current code |

## 2. Where Table 4 could come from — searches performed
1. README (original) documents: main experiments `--seeds 2,3,4,5,6`, outputs under `results/` (`final_test_metrics.csv`, `round_metrics.csv`, `network_metrics.csv`, …); baselines via `--suite core` (CIC: `ciciot2023_core.yaml`), ε≈10/20 via `ciciot2023_eps10.yaml` / `ciciot2023_eps20.yaml` (`--suite single`); UNSW via `configs/full.yaml --suite core` (seeds 2–6). **There is no `results/` directory anywhere on this machine.**
2. Anchored numeric search (e.g. `0.7364`, `0.5601`, `89.34`, `74.53`, `0.8106`) over every commit of the repository, the working tree (CSV/JSON/MD/TXT/TeX/YAML/log), and the archives `Historical_Evidence_Supplement…zip`, `Phase10_Home_Manuscript_Writing_Package.zip`, `Phase6C_Final_Handoff.zip`, `cloud_transfer.tar`, the Zenodo `rel.zip` and `main paper.zip`: **no artifact contains Table 4 values.** The only matches are the manuscript itself (`main paper.zip`), one unrelated number in a Phase 9 table, and one raw feature value in the UNSW-NB15 training CSV.
3. Other project folders: `Desktop/IoT-FL-Recovery` (venv, a repo copy, the Zenodo download/extract, `pytest_tmp` with unit-test outputs, a participation audit) — no experiment results; `Desktop/New folder` does not exist.
4. Repository result directories (`results_phase6a/6b/6c/7/7b/10`, `results_gpu_bench`, `results_gha_probe`) belong to the validation-only studies; `results_smoke_no_official_test` holds one-round smoke tests only.
5. Plot generation: no script producing figures 3–8 or the failure figure exists in the repository (see the separate Figure 9 audit).

**Consequence:** every number in Table 4 has no identifiable source. Per the provenance rules, matching magnitudes with other runs does not verify them.

## 3. Evidence per Table 4 configuration (executed? what is known?)
| Method | Configuration known from code | Executed run found? | Seeds | Evaluation partition | Checkpoint / threshold | Network / delivery | Privacy |
|---|---|---|---|---|---|---|---|
| FedAvg | `src/suites.py@7c75b2d` `fedavg_scenario`: `routing.enabled=False`, no DP, FedAvg, recovery off, attack 20 % sign-flip + failures on (inferred match to Table 4's "FedAvg"; not documented) | **No** | planned 2–6 | official test file (README, configs `test_csv`) | best round by validation ROC-AUC (`model_selection_metric`); threshold = validation FPR ≤ 0.15 & recall ≥ 0.6 on the same validation set; infeasible fallback = maximise recall under the FPR cap, flagged | `trace_mode` sequential (historical, single shared RNG), independent-draw delivery, random paths when routing is disabled | none |
| DP+FedAvg | `fedavg_dp_scenario`: routing off, recovery off, FedAvg + central Gaussian (ε target 10) | **No** | planned 2–6 | official test | as above | as above | central_client, clipping 0.05/0.10, weight cap 0.1, auto-calibrated σ |
| Robust no-DP | `robust_no_dp_scenario`: routing off, recovery off, distance filter k=2.5, no DP | **No** | planned 2–6 | official test | as above | as above | none |
| Proposed ε≈10 | CIC `configs/ciciot2023_eps10.yaml`; UNSW `configs/full.yaml` (target ε 10). Routing on (top-k), median surrogates, MAD filter, central Gaussian, momentum 0.9, η_s 0.5 | **No** (configs exist, outputs do not) | planned 2–6 | official test (CIC `prepared_paper/test.csv.gz`, 300 000 rows; UNSW 82 332 rows) | as above | top-k routing, independent draws, sequential trace | σ=0.994 (verified by current `calibrate_noise_multiplier`: 0.99390) |
| Proposed ε≈20 | CIC `configs/ciciot2023_eps20.yaml`; **UNSW: no ε≈20 config exists** (only `privacy_sweep`, seeds 2–4, method `privacy_target_epsilon_20`) | **No** | CIC planned 2–6; UNSW ambiguous (3 vs 5 seeds) | official test | as above | as above | σ=0.672 (verified: 0.67172) |
| Modular Edge FL-inspired | **no code, no config, no method name anywhere** (also confirmed in `docs/phase8/ISSUE_RESOLUTION_MATRIX.md` #10) | **Not executed** | — | — | — | — | — |
| MCHFL-style | same as above | **Not executed** | — | — | — | — | — |

The manuscript text (lines 1283–1290, 1308, 1960) says these two methods were compared; Table 4 and every artifact contain no results for them. These claims are unsupported.

Additional old-protocol facts that matter for any comparison with the locked runs: (a) one validation set is used both for checkpoint selection and threshold selection (no separate calibration partition); (b) the test file is used for the reported metrics, with `enable_calibrated_evaluation: true` for UNSW (a secondary protocol that uses part of the test set to calibrate) — it is **unknown which of the two protocols Table 4's UNSW numbers use** (README lists both `standard_operating_points.csv` and `calibrated_operating_points.csv`); (c) the pre-fix metric code clipped scores to (1e-7, 1−1e-7) before comparing with the threshold (a threshold of exactly 1.0 then predicts nothing; Phase 7b fix) — any old result with such a threshold is affected; (d) network traces were not matched across methods (`trace_mode: sequential`).

## 4. Row-level audit (dataset × method × metric)
Every row is **NOT VERIFIED**: there is no source path, run identifier or seed record. The column "closest locked analog" gives, for context only, the mean (SD over seeds 12–16) of the nearest executed validation-only arm; it is **not** a verification and, for several rows, not an equivalent configuration (§5). Detection values are the audited selected-checkpoint report-partition values; network values are means over the selected transfers (`network_metrics.csv`).

| dataset | method | metric | manuscript_value | status | closest_locked_analog |
|---|---|---|---|---|---|
| CICIoT2023 | FedAvg | F1 | 0.9921 | NOT VERIFIED | scenario_fedavg_random: 0.9904 (SD 0.0010), 5 seeds, locked protocol |
| CICIoT2023 | FedAvg | ROC-AUC | 0.9935 | NOT VERIFIED | scenario_fedavg_random: 0.9930 (SD 0.0015), 5 seeds, locked protocol |
| CICIoT2023 | FedAvg | FPR | 0.1453 | NOT VERIFIED | scenario_fedavg_random: 0.1400 (SD 0.0108), 5 seeds, locked protocol |
| CICIoT2023 | FedAvg | Delay (ms) | 89.3400 | NOT VERIFIED | scenario_fedavg_random: 71.2721 (SD 5.0589), 5 seeds, locked protocol |
| CICIoT2023 | FedAvg | PDR | 0.7364 | NOT VERIFIED | scenario_fedavg_random: 0.7818 (SD 0.0319), 5 seeds, locked protocol |
| CICIoT2023 | FedAvg | Path stability | 0.5601 | NOT VERIFIED | scenario_fedavg_random: 0.8545 (SD 0.0228), 5 seeds, locked protocol |
| CICIoT2023 | FedAvg | Transfer efficiency (Mbit/s) | 6.8100 | NOT VERIFIED | scenario_fedavg_random: 9.3832 (SD 0.5802), 5 seeds, locked protocol |
| CICIoT2023 | DP+FedAvg | F1 | 0.9768 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | DP+FedAvg | ROC-AUC | 0.9710 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | DP+FedAvg | FPR | 0.1434 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | DP+FedAvg | Delay (ms) | 88.9600 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | DP+FedAvg | PDR | 0.7144 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | DP+FedAvg | Path stability | 0.5393 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | DP+FedAvg | Transfer efficiency (Mbit/s) | 6.7600 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Robust no-DP | F1 | 0.9939 | NOT VERIFIED | robust_random_no_imputation: 0.9933 (SD 0.0003), 5 seeds, locked protocol |
| CICIoT2023 | Robust no-DP | ROC-AUC | 0.9961 | NOT VERIFIED | robust_random_no_imputation: 0.9962 (SD 0.0003), 5 seeds, locked protocol |
| CICIoT2023 | Robust no-DP | FPR | 0.1478 | NOT VERIFIED | robust_random_no_imputation: 0.1473 (SD 0.0122), 5 seeds, locked protocol |
| CICIoT2023 | Robust no-DP | Delay (ms) | 89.6300 | NOT VERIFIED | robust_random_no_imputation: 71.2721 (SD 5.0589), 5 seeds, locked protocol |
| CICIoT2023 | Robust no-DP | PDR | 0.7275 | NOT VERIFIED | robust_random_no_imputation: 0.7818 (SD 0.0319), 5 seeds, locked protocol |
| CICIoT2023 | Robust no-DP | Path stability | 0.5466 | NOT VERIFIED | robust_random_no_imputation: 0.8545 (SD 0.0228), 5 seeds, locked protocol |
| CICIoT2023 | Robust no-DP | Transfer efficiency (Mbit/s) | 6.7600 | NOT VERIFIED | robust_random_no_imputation: 9.3832 (SD 0.5802), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | F1 | 0.9919 | NOT VERIFIED | reference_gaussian: 0.9911 (SD 0.0004), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | ROC-AUC | 0.9934 | NOT VERIFIED | reference_gaussian: 0.9930 (SD 0.0014), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | FPR | 0.1453 | NOT VERIFIED | reference_gaussian: 0.1407 (SD 0.0184), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | Delay (ms) | 65.5100 | NOT VERIFIED | reference_gaussian: 65.9000 (SD 6.1851), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | PDR | 0.8358 | NOT VERIFIED | reference_gaussian: 0.8511 (SD 0.0146), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | Path stability | 0.9124 | NOT VERIFIED | reference_gaussian: 0.9231 (SD 0.0070), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~10 | Transfer efficiency (Mbit/s) | 9.9200 | NOT VERIFIED | reference_gaussian: 10.9356 (SD 0.8955), 5 seeds, locked protocol |
| CICIoT2023 | Proposed eps~20 | F1 | 0.9928 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Proposed eps~20 | ROC-AUC | 0.9946 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Proposed eps~20 | FPR | 0.1439 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Proposed eps~20 | Delay (ms) | 65.5900 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Proposed eps~20 | PDR | 0.8348 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Proposed eps~20 | Path stability | 0.9119 | NOT VERIFIED | no locked-protocol arm exists |
| CICIoT2023 | Proposed eps~20 | Transfer efficiency (Mbit/s) | 9.9300 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | FedAvg | F1 | 0.7754 | NOT VERIFIED | scenario_fedavg_random: 0.7217 (SD 0.2069), 5 seeds, locked protocol |
| UNSW-NB15 | FedAvg | ROC-AUC | 0.8542 | NOT VERIFIED | scenario_fedavg_random: 0.8752 (SD 0.0863), 5 seeds, locked protocol |
| UNSW-NB15 | FedAvg | FPR | 0.3456 | NOT VERIFIED | scenario_fedavg_random: 0.1464 (SD 0.0158), 5 seeds, locked protocol |
| UNSW-NB15 | FedAvg | Delay (ms) | 99.0400 | NOT VERIFIED | scenario_fedavg_random: 81.5278 (SD 5.5757), 5 seeds, locked protocol |
| UNSW-NB15 | FedAvg | PDR | 0.7350 | NOT VERIFIED | scenario_fedavg_random: 0.7818 (SD 0.0319), 5 seeds, locked protocol |
| UNSW-NB15 | FedAvg | Path stability | 0.5579 | NOT VERIFIED | scenario_fedavg_random: 0.8545 (SD 0.0228), 5 seeds, locked protocol |
| UNSW-NB15 | FedAvg | Transfer efficiency (Mbit/s) | 11.1100 | NOT VERIFIED | scenario_fedavg_random: 14.9304 (SD 0.8362), 5 seeds, locked protocol |
| UNSW-NB15 | DP+FedAvg | F1 | 0.6430 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | DP+FedAvg | ROC-AUC | 0.7467 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | DP+FedAvg | FPR | 0.2412 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | DP+FedAvg | Delay (ms) | 98.8300 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | DP+FedAvg | PDR | 0.7339 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | DP+FedAvg | Path stability | 0.5592 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | DP+FedAvg | Transfer efficiency (Mbit/s) | 11.2200 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Robust no-DP | F1 | 0.8383 | NOT VERIFIED | robust_random_no_imputation: 0.9526 (SD 0.0026), 5 seeds, locked protocol |
| UNSW-NB15 | Robust no-DP | ROC-AUC | 0.9281 | NOT VERIFIED | robust_random_no_imputation: 0.9825 (SD 0.0018), 5 seeds, locked protocol |
| UNSW-NB15 | Robust no-DP | FPR | 0.3463 | NOT VERIFIED | robust_random_no_imputation: 0.1431 (SD 0.0143), 5 seeds, locked protocol |
| UNSW-NB15 | Robust no-DP | Delay (ms) | 98.3300 | NOT VERIFIED | robust_random_no_imputation: 81.5278 (SD 5.5757), 5 seeds, locked protocol |
| UNSW-NB15 | Robust no-DP | PDR | 0.7183 | NOT VERIFIED | robust_random_no_imputation: 0.7818 (SD 0.0319), 5 seeds, locked protocol |
| UNSW-NB15 | Robust no-DP | Path stability | 0.5438 | NOT VERIFIED | robust_random_no_imputation: 0.8545 (SD 0.0228), 5 seeds, locked protocol |
| UNSW-NB15 | Robust no-DP | Transfer efficiency (Mbit/s) | 11.1300 | NOT VERIFIED | robust_random_no_imputation: 14.9304 (SD 0.8362), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | F1 | 0.8106 | NOT VERIFIED | reference_gaussian: 0.9005 (SD 0.0335), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | ROC-AUC | 0.8801 | NOT VERIFIED | reference_gaussian: 0.9419 (SD 0.0166), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | FPR | 0.3145 | NOT VERIFIED | reference_gaussian: 0.1488 (SD 0.0102), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | Delay (ms) | 74.5300 | NOT VERIFIED | reference_gaussian: 76.6499 (SD 6.5535), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | PDR | 0.8348 | NOT VERIFIED | reference_gaussian: 0.8511 (SD 0.0146), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | Path stability | 0.9118 | NOT VERIFIED | reference_gaussian: 0.9231 (SD 0.0070), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~10 | Transfer efficiency (Mbit/s) | 15.9400 | NOT VERIFIED | reference_gaussian: 17.2382 (SD 1.0719), 5 seeds, locked protocol |
| UNSW-NB15 | Proposed eps~20 | F1 | 0.8399 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Proposed eps~20 | ROC-AUC | 0.9109 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Proposed eps~20 | FPR | 0.3333 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Proposed eps~20 | Delay (ms) | 74.6000 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Proposed eps~20 | PDR | 0.8348 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Proposed eps~20 | Path stability | 0.9119 | NOT VERIFIED | no locked-protocol arm exists |
| UNSW-NB15 | Proposed eps~20 | Transfer efficiency (Mbit/s) | 15.9700 | NOT VERIFIED | no locked-protocol arm exists |

(The same table with all columns, including evidence paths and run-ID status, is in `_table4_row_audit.csv`; per-seed executed values of the analog arms, with run IDs, config hashes and paths, are in `TABLE4_VERIFIED_METRICS.csv`.)

## 5. Are the locked Phase 6C arms equivalents of Table 4's rows?
| Table 4 row | Closest executed arm | Equivalent? |
|---|---|---|
| FedAvg | `scenario_fedavg_random` (routing **enabled**, uniform-random selection, no recovery); `clean_fedavg` (routing disabled but no attack) | **No.** Table 4's baseline network metrics (delay 89–99 ms, PDR 0.72–0.74, path stability 0.54–0.56) are those of a **routing-disabled** network (clean_fedavg: 87.0/97.1 ms, 0.706, 0.539), whereas `scenario_fedavg_random` keeps routed paths (71.3/81.5 ms, 0.782, 0.855). The two baselines differ in path assignment, not only in client selection |
| DP+FedAvg | none | No arm exists |
| Robust no-DP | `robust_random_no_imputation` (routing enabled) | **No** (same reason) |
| Proposed ε≈10 | `reference_gaussian` (top-k routing, recovery, MAD filter, central Gaussian, ε̂ 9.9993) | Closest, but differs in split (CIC file-group split vs row-level), attacker assignment (exposure-controlled), evaluation partition (validation vs test), traces (matched vs sequential), code and seeds |
| Proposed ε≈20 | none | No arm exists |

Consequence for the headline network gains: the paper attributes the 26.6 % delay reduction, +13.4 % PDR, +62.8 % path stability and +46 % transfer efficiency (CICIoT2023) to the proposed method versus FedAvg. In the executed locked arms the **same-seed paired effect of routing-aware top-k client selection alone** (reference_gaussian vs scenario_fedavg_random, both with routed paths, 5 seeds) is: delay −5.4 ms (−7.5 %), first-transmission PDR +0.069 (+8.9 %), path stability +0.069 (+8.0 %), transfer efficiency +1.55 Mbit/s (+16.5 %) on CICIoT2023 (all 5/5 seeds in the same direction); UNSW-NB15 similar (`TABLE4_LOCKED_ANALOG_PAIRED_DIFFERENCES.csv`). The much larger Table 4 gains therefore **mix client selection with path assignment (routing disabled ⇒ random paths)**; that attribution is unverified because no executed "routing off" arm with the same protocol exists.

Detection-metric context from the locked arms (paired, 5 seeds): CICIoT2023 reference_gaussian vs `robust_random_no_imputation`: ΔAUC −0.0032 (0/5 seeds higher) — i.e. the private proposed arm is slightly *below* the non-private robust arm (Table 4 shows ε≈20 ≈ equal and ε≈10 below); UNSW-NB15: ΔAUC −0.0406, ΔF1 −0.052 (0/5 higher). UNSW FPR in Table 4 (0.24–0.35) is incompatible with any validation-only arm (0.143–0.149, capped by the FPR rule), confirming that Table 4 reports a different (test) evaluation.

## 6. PDR versus update-delivery success
* In the executed runs PDR (`pdr`) is the packet-level fraction received on the **first** transmission; update delivery (`update_delivered`) is a separate Bernoulli draw with the same probability under the historical `independent_draw` model (correlation between the two per event ≈ 0.03; `phase6c_diagnostics.json`). Their means agree only because both estimate `expected_pdr`: reference PDR 0.8511 vs update-delivery rate 0.8480.
* Table 4 reports **only PDR**, never the update-delivery rate or the number of updates the server actually received (explicit client failures also remove updates: received ≈ 0.75 of selected in the reference). The text equates higher PDR with "improvement in successful update delivery" (results text near line 2058); that is not what PDR measures in this simulator. Under the packet-coupled model the two diverge strongly (PDR 0.834 vs delivered 0.626 for the revised pipeline).
* Network comparisons in Table 4 mix routing-disabled baselines with routed proposed arms (§5) and unmatched traces, so the metric definitions agree but the **conditions are not compatible** for attribution to selection.

## 7. Table 3 versus actual configurations
Table 3 (50/10 clients, T/E = 30/2, B = 256, η = 3e−4, Dirichlet α = 0.5, MLP 128-96-64 dropout 0.2, 3 edges, p_out = 0.01, routing weights 0.4/0.3/0.3, k = 2.5, δ = 1e−5, σ = 0.994/0.672, a_max = 0.1, p_f = 0.1, χ_rec = 0.5, η_s/μ = 0.5/0.9, clip 0.05/0.10, sign-flip 0.2 × 5.0, five seeds, Gaussian server-side DP, coordinate-wise median recovery) **matches** `configs/ciciot2023_eps10.yaml` / `configs/full.yaml` and the current noise calibration. It does **not** state: the evaluation partition (official test files), that baselines disable routing, the delivery model (independent draw), unmatched traces, the old single-validation-set threshold protocol, the attacker assignment, or that the CICIoT2023 split is row-level. It also lists "ablation η_s = 1.0" only in the text (line 2289), while the controlled studies later showed that this changes two factors (momentum and learning rate).

## 8. Abstract, Results and Conclusion numbers
The Abstract in this file already describes the **locked 240-run validation-only study** (0.9838 reference, 0.9843 clean FedAvg, 0.8752–0.8870 undefended FedAvg, PDR 0.782→0.851, 27.2 of 50 clients never selected): these match the executed Phase 6C data (§5 and `TABLE4_VERIFIED_METRICS.csv`). Table 4 and the Results/Conclusion percentages do not: Table 4 gives FedAvg ROC-AUC 0.8542 (UNSW-NB15) while the Abstract gives 0.8752–0.8870 for undefended FedAvg. The manuscript is therefore internally inconsistent (two different experimental programmes).

Percentages quoted in Results and Conclusion, recomputed from Table 4 itself (`TABLE4_CLAIM_ARITHMETIC.csv`): 26.6 %, 13.4 %, 62.8 %, 8.3 %, 6.6 %, 24.7 %, 63.5 % **reproduce arithmetically**; transfer efficiency "46.0 %" recomputes to 45.8 % (Proposed ε≈20 vs FedAvg). NSR reduction 69.7 % (57.21→17.34) reproduces arithmetically. Arithmetic reproducibility says nothing about the underlying measurements, which are unsourced (NOT VERIFIED).

## 9. Cross-check with the 20 InsightAI comments (priority 3, 4, 9, 10, 11, 13, 17)
| # | Status after this audit |
|---|---|
| 3 privacy accounting | σ values reproduce under the current accountant; but every run records `subsampling_amplification_valid=false` (deterministic top-k selection, data-dependent filtering). The reported ε is a diagnostic RDP estimate under a Poisson-sampling assumption with q=0.2 and must not be presented as a guarantee. The ε values in the privacy-cost table (9.58, 9.91, 9.18, 8.42, 20.00) are unsourced; the locked ε̂ is 9.9993 |
| 4 network model | Implemented in `src/network.py`; the router ranks by true link stability, which equals the delivery probability (oracle on success probability); the manuscript table lists parameters only. Table 4's baseline-vs-proposed network contrast conflates routing-disabled paths with selection (§5) |
| 9 thresholds / false alarms | Original protocol: threshold from the same validation set used for checkpoint selection, applied to test; locked protocol: separate calibration partition. UNSW test FPR 0.24–0.35 cannot be rechecked (test locked) and cannot be compared with validation FPR ≈ 0.145 |
| 10 baselines | DP+FedAvg, ε≈20 and the routing-disabled baselines have no executed counterpart; Modular Edge FL-inspired and MCHFL-style were never executed |
| 11 seed uncertainty | Table 4 gives means only, no SD/paired intervals; planned seeds 2–6 are not documented by any run record; sweeps "at least three seeds" |
| 13 communication accounting | Table 4's transfer efficiency and delay are computed over selected transfers incl. undelivered ones; payload bytes are identical across arms (52.36 MB UNSW, 28.61 MB CIC attempted), so no communication-cost claim can come from payload size; the privacy-cost table's communication numbers (23.08–52.39 MB) match neither attempted nor delivered bytes of the locked runs except 28.61 (CIC) and 52.39≈52.36 (UNSW) |
| 17 relative changes | All headline percentages are computed against FedAvg baselines whose network conditions differ from the proposed arm; under executed matched arms the selection-only effects are about one third or less (§5); privacy cost is not matched (ε≈20 and DP+FedAvg unsourced) |
