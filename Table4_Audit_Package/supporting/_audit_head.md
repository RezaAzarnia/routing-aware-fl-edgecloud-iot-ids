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

