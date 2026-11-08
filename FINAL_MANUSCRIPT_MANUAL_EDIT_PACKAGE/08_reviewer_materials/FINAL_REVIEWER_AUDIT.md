# Final manuscript and reviewer-readiness audit

Source of truth: `origin/main` at `7d59885` plus the corrections committed with this file. Reviewer report: *InsightAI Manuscript Readiness & Peer-Review Report* (1 Oct 2026, 20 comments, written on an earlier 17-page draft with missing figures and bibliography). Manuscript: `manuscript/main.tex` (compiled PDF: `manuscript/main.pdf`).

Every statement below was checked against code, locked configs, run artifacts or the compiled PDF. Items that need new experiments or author knowledge are labelled as such; none was fabricated.

## 1. Locked-data verification (CICIoT2023 and UNSW-NB15)
| Item | Evidence | Result |
|---|---|---|
| CICIoT2023 split | `data/.../prepared_verified_v2_filegroup/preparation_metadata.json`: `split_mode=file_group`, prepared 926,133 train / 146,626 validation / 300,000 test (reserved); dedup removed 73,867 / 53,374 rows; manifests `docs/phase6c` and `docs/table4_v2` carry train/validation content hashes | **Matches manuscript.** No row-level numbers restored |
| File-group scope | 17 of 34 classes have >= 3 source files and are file-group separated; the other 17 are row-stratified (`ungrouped_classes_row_stratified`) | **Now disclosed** in the manuscript (was missing) |
| Report partition size | CICIoT2023: ~48,875 records per partition, only **1,564 benign** each | **Now disclosed**; FPR is estimated from 1,564 negatives |
| Features | CICIoT2023 39 numerical features; UNSW-NB15 42 raw -> 194 encoded (`dataset_summary.json`) | consistent |
| Seeds | Table 4 v2 manifest and Phase 6C manifest: seeds 12-16, 40 runs, code fingerprint `c8cf7c0c52c34ad0` | consistent with Table 3 |
| **UNSW-NB15 counts** | Manuscript said 149,039 train / 26,302 validation (obsolete historical split). Locked runs: 175,341 official training records -> **150,293 train + 25,048 validation pool** (8,350 / 8,350 / 8,348 calibration / selection / report for seed 12; seed-to-seed differences <= 4 records) | **Inconsistency found and corrected** |
| Test data | `test_data_loaded=false` in all 40 runs; the 82,332-row UNSW test and 300,000-row CICIoT2023 test were never opened | confirmed |

## 2. 20-comment status
Status: CLOSED = resolved from existing verified evidence; PARTIAL = resolved in part, remaining action stated; OPEN = needs new experiments or author input.

| # | Comment | Status | Evidence in the repository / manuscript | Exact remaining action |
|---|---|---|---|---|
| 1 | Bibliography and citations | PARTIAL | 35 BibTeX entries, 0 undefined citations, 0 BibTeX warnings; all 35 cited | Authors must verify each application reference and each Table 1 row against the original publication (only 13 of 35 entries carry a DOI); cannot be checked offline |
| 2 | Embed all figures | CLOSED | 8 figures embedded and cited (fig1-fig8); 6 tables, all cited; no placeholders; page layout inspected | Authors to confirm figures 3-6 provenance (see section 4, item 3) |
| 3 | Privacy accounting | CLOSED (as empirical diagnostic) | Abstract, Sections 3.4, 4.8.2 and Conclusion call epsilon a diagnostic RDP estimate under a Poisson approximation that does not hold (`subsampling_amplification_valid=false`); no DP guarantee claimed | A formal DP claim would need a sensitivity proof for the adaptive pipeline and a matching accountant (new theory, not requested for this empirical paper) |
| 4 | Network model | CLOSED | New "Network model" paragraph (topology, uniform ranges, per-round dynamics, outage, score formulas, normalization, delivery/delay model, oracle link state disclosed) and `docs/SIMULATION_SPEC.md`; path stability definition corrected to the implemented 0.5 s + 0.5 persistence score | Realism of the simulator remains a stated limitation |
| 5 | Surrogate imputation vs recovery | PARTIAL | Renamed "median-based surrogate imputation"; measured in the proposed pipeline (300 rounds): surrogate weight share mean 0.30 (median 0.25, max 1.0); only surrogates retained in 10 rounds (3.3%); now disclosed **[Supplementary update]** Five-seed Phase 6C `ctl_imputation_*` arms analysed on both datasets: imputation ON vs OFF dAUC +0.0016 [-0.0036,+0.0068] UNSW, +0.0001 CIC; no demonstrated detection benefit; DP-pipeline surrogate share 0.30 | Evidence is on the Phase 6C (not Table 4 v2) protocol; state surrogate share and absence of demonstrated benefit |
| 6 | Total algorithm and weight cap | CLOSED (algorithm); mandatory text correction | Empty-update branch documented and verified (0 of 1,200 rounds); CapNormalize defined; cap infeasibility quantified (<10 retained updates in 92% of rounds, min 6, max weight 0.167); MAD defined; the false claim that no update can dominate was removed **[Supplementary update]** Verified: cap applied only in central-DP path; weights exactly 1/n for <=10 retained (2,750/2,750 such DP rounds); chi_rec and sample sizes inert there | Apply corrections C1-C3 in `Supplementary_Experiments_Package/MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex` |
| 7 | Participation bias | CLOSED (evidence); manuscript integration pending | Selection Gini, never-selected clients, coverage-aware / UCB / uniform policies, independent vs coupled networks (Figs 3, 5, 6; UNSW) **[Supplementary update]** Six policy/network arms x 5 seeds x 2 datasets, leakage-safe client holdouts, worst/P10/mean held-out recall (T4/Fig4) | State seeds of existing Figs 3-6; integrate supplementary section |
| 8 | Preprocessing provenance | PARTIAL | Counts, dedup, file-group scope, feature counts, partition sizes, hashes in manifests; UNSW 194-feature encoding in code | Class counts per partition for UNSW-NB15 and the Dirichlet partition rule (min 100 samples per client) are in code/configs only; add to the supplement |
| 9 | Threshold selection and FPR | PARTIAL | Rule now stated (calibration partition, FPR <= 0.15, recall >= 0.60, max recall, infeasible fallback); high FPR explained as set by the cap | Operational 1% / 5% FPR results exist in run artifacts (appendix A) but are not in the paper; UNSW recall at 1% FPR is low. Add to the paper (extraction only, no new run) |
| 10 | Baseline identities | CLOSED | Method matrix (`TABLE4_V2_METHOD_MATRIX.csv`); Modular Edge FL-inspired and MCHFL-style stated as *not executed* | none |
| 11 | Uncertainty and significance | CLOSED | mean (SD), 5 paired seeds, t-intervals, exact sign-flip test with the p = 0.0625 floor, per-seed CSV published | No multiplicity correction (results labelled exploratory) |
| 12 | Attacker model and robustness | PARTIAL | Sign-flip transform, 20% exposure-controlled assignment, tau = 5 now defined **[Supplementary update]** Static attacks: SF 10/20/30%, BSF 20%, LF 20%, FedAvg vs reference, 2 datasets, 5 seeds | **No adaptive attack implemented**; scope claims to static non-adaptive attacks |
| 13 | Communication accounting | CLOSED (simulated accounting) | Attempted/delivered/on-wire bytes are in `TABLE4_V2_PER_SEED.csv` **[Supplementary update]** Per-configuration serialized/attempted/delivered/on-wire bytes and wall/CPU/peak memory (T5) | Report with caveat: simulated bytes, shared-host timings |
| 14 | Ablation confounding | CLOSED; mandatory relabelling | Controlled five-seed ablation (Section 4.7, Figs 7/8, Tables 5/6) with matched comparators; momentum deletion holds the server learning rate **[Supplementary update]** Audited: Added Gaussian is a noise-only contrast; Clipping+cap and Full pipeline are combined (clipping + uniform weights) | Relabel Table 5 (C4-C5) |
| 15 | Parameter sensitivity and resources | CLOSED (exploratory resolution) | none **[Supplementary update]** k, chi_rec, alpha, clip sweeps (UNSW n=5, CIC n=3) and scaling N=25/50/100, k=5/10/20 with runtime/memory (T2, T5) | CIC n=3; exact-test floor p=0.0625 although some t-intervals exclude 0 (exploratory, unadjusted); integrate supplementary section |
| 16 | Integration gap | PARTIAL | Table 1 and Section 2.4 present in the compiled paper | Capability/evidence columns require author-verified literature entries |
| 17 | Relative changes and NSR | CLOSED | Every percentage names its baseline (random-path vs routed-path FedAvg); abstract uses absolute values; NSR (ratio) defined and comparisons labelled multi-factor | none |
| 18 | Reproducibility archive | PARTIAL | Zenodo v1.0.4 (10.5281/zenodo.24031823, commit e74e2e1) is the version cited by the manuscript; a later v.1.0.5 (10.5281/zenodo.24032087, commit 7d59885, same concept DOI 10.5281/zenodo.21131047) also exists; neither contains the supplementary outputs (`Supplementary_Experiments_Package/ZENODO_VERIFICATION.md`). v1.0.4 verified to contain the manifest, scripts and per-seed/summary/paired tables; README separates legacy seeds 2-6 from Table 4 v2; `docs/SIMULATION_SPEC.md` | Raw per-run outputs (logs, predictions, accountant outputs) are **not published**; model output dimension and optimizer details (Adam, cross-entropy in code) are not in the paper; the archived `main.tex` predates later corrections (new release needs the authors' approval) |
| 19 | Author declarations | **OPEN (author input)** | Author block with 7 authors and 6 affiliations present | No funding, competing-interest, CRediT contribution, ethics or consent statement; corresponding-author line reads "Co-author: ..." Authors must supply these; none were invented |
| 20 | Title and prose vs evidence | PARTIAL | Abstract and conclusion rewritten to the controlled evidence; UNSW section renamed "Complementary Benchmark Evaluation"; no generalization claim | The title still contains "Secure"; whether to change it is an author decision |

Summary: **CLOSED 8** (comments 2, 3, 4, 6, 10, 11, 14, 17), **PARTIAL 10** (1, 5, 7, 8, 9, 12, 13, 16, 18, 20), **OPEN 2** (15, 19). Comments 5, 12 and 15 need new experiments; 1, 16 and 19 need author input.

## 3. Manuscript and documentation fixes made in this pass (all from existing verified evidence)
1. UNSW-NB15 sample counts replaced by the locked-protocol counts (150,293 / 25,048 with partition sizes).
2. CICIoT2023 preparation: dedup counts, 39 features, file-group scope (17 of 34 classes), 1,564 benign negatives per partition.
3. New Network model and Attack model paragraphs; full specification in `docs/SIMULATION_SPEC.md`.
4. Threshold selection rule, infeasible fallback, checkpoint rule, and the statement that FPR is set by the 0.15 cap.
5. Surrogate weighting and cap: removed the unsupported claim that no update can dominate; added measured cap infeasibility and surrogate weight share; documented the empty-update branch and MAD definition.
6. Path stability definition aligned with the implementation.
7. Code/Data Availability cite Zenodo v1.0.4 (10.5281/zenodo.24031823) and separate published tables from unpublished raw outputs (previous commit); README distinguishes legacy seeds 2-6 from Table 4 v2 (seeds 12-16).
No numerical result, table, figure, reference or locked config was changed.

## 4. Scientific concerns found during this audit (not in the InsightAI report)
1. **Surrogates carry about 30% of the aggregation weight** in the proposed pipeline and the only retained updates in 3.3% of rounds. The framework's recovery component therefore partly replaces genuine information with a median surrogate; its contribution to detection is not isolated at five seeds.
2. **The 0.15 FPR cap drives the headline FPR.** At stricter caps UNSW-NB15 recall drops sharply (appendix A), so the false-alarm cost of the proposed pipeline on UNSW-NB15 is substantial.
3. **Provenance of Figures 3-6.** Their content (four selection policies, independent/coupled networks, Gini, never-selected clients) matches the earlier Phase 10 study (UNSW only, seeds 22-26 in the Phase 10 manifest), whereas Table 3 states main seeds 12-16. The manuscript does not state the seeds of these figures. Authors must confirm and add a statement.
4. The CICIoT2023 report partition has few benign records (1,564), so FPR and F1 are sensitive to the benign sample.

## 5. Compilation
`latexmk -pdf` (elsarticle 5p, pdfLaTeX): **18 pages**, 0 undefined citations or references, 0 multiply-defined labels, 0 BibTeX warnings, 8 figures, 6 tables, 35 references. All 18 pages were rendered (overview montage) and pages 12 and 17 were inspected at full resolution; no placement problems were seen. Pages were not individually proofread at full resolution.

## 6. Verdict
Scientific readiness for submission: **not yet ready for a claims-based journal submission; ready only if framed as an exploratory controlled study with limited resolution.** The text is now internally consistent and honest about evidence, but reviewer-critical items remain: attack robustness beyond one setting (12), parameter sensitivity and scaling (15), a controlled five-seed test of the surrogate component (5), operational-FPR reporting (9), author declarations (19) and verified literature (1, 16). Items 5, 12 and 15 need new experiments.

## Appendix A. Operating points at fixed validation FPR caps (report partition, seeds 12-16)
Extracted from the stored `threshold_diagnostics.json` ("independent_evaluation") of existing runs; no new experiment. Reused Phase 6C arms are **not** audited by the Table 4 v2 QA ledger. Cells where the mean FPR is far above the cap (UNSW 1% column) come from seeds in which the calibration constraint was infeasible.

| dataset | arm | cap 1%: recall (SD) / FPR | cap 5%: recall (SD) / FPR | cap 15%: recall (SD) / FPR |
|---|---|---|---|---|
| ciciot | scenario_fedavg_random | 0.972 (0.002) / 0.010 | 0.978 (0.002) / 0.046 | 0.986 (0.002) / 0.140 |
| ciciot | t4_e1_fedavg_random_path | 0.972 (0.002) / 0.009 | 0.979 (0.003) / 0.047 | 0.987 (0.002) / 0.144 |
| ciciot | robust_random_no_imputation | 0.976 (0.001) / 0.010 | 0.984 (0.001) / 0.051 | 0.992 (0.000) / 0.147 |
| ciciot | t4_e2_robust_random_path | 0.975 (0.001) / 0.009 | 0.983 (0.001) / 0.046 | 0.991 (0.000) / 0.148 |
| ciciot | t4_e3_dpfedavg_random_path | 0.759 (0.192) / 0.010 | 0.901 (0.099) / 0.050 | 0.971 (0.017) / 0.148 |
| ciciot | reference | 0.976 (0.001) / 0.010 | 0.984 (0.001) / 0.051 | 0.992 (0.000) / 0.144 |
| ciciot | reference_gaussian | 0.972 (0.001) / 0.010 | 0.980 (0.001) / 0.049 | 0.987 (0.001) / 0.141 |
| ciciot | t4_e4_proposed_eps20 | 0.973 (0.001) / 0.010 | 0.980 (0.001) / 0.048 | 0.988 (0.002) / 0.147 |
| unsw | scenario_fedavg_random | 0.250 (0.239) / 0.007 | 0.359 (0.252) / 0.045 | 0.636 (0.255) / 0.146 |
| unsw | t4_e1_fedavg_random_path | 0.223 (0.223) / 0.008 | 0.356 (0.218) / 0.044 | 0.623 (0.266) / 0.145 |
| unsw | robust_random_no_imputation | 0.666 (0.107) / 0.006 | 0.866 (0.028) / 0.045 | 0.971 (0.011) / 0.143 |
| unsw | t4_e2_robust_random_path | 0.854 (0.132) / 0.306 | 0.808 (0.126) / 0.040 | 0.951 (0.036) / 0.142 |
| unsw | t4_e3_dpfedavg_random_path | 0.270 (0.421) / 0.197 | 0.469 (0.119) / 0.053 | 0.765 (0.075) / 0.153 |
| unsw | reference | 0.747 (0.040) / 0.009 | 0.885 (0.022) / 0.049 | 0.975 (0.007) / 0.145 |
| unsw | reference_gaussian | 0.594 (0.399) / 0.183 | 0.674 (0.085) / 0.054 | 0.878 (0.061) / 0.149 |
| unsw | t4_e4_proposed_eps20 | 0.393 (0.093) / 0.011 | 0.725 (0.056) / 0.053 | 0.887 (0.062) / 0.145 |


## 7. Supplementary-experiment update (SUPP_V1 + SUPP_V2; added after the pass above)
Status counts after the supplementary experiments: **11 CLOSED, 8 PARTIAL, 1 OPEN** (comment 19, author input). Full per-comment mapping: `Supplementary_Experiments_Package/SUPPLEMENTARY_EXPERIMENTS_REVIEWER_MAPPING.md`; QA: `FINAL_SCIENTIFIC_QA_REPORT.md` (53/53 checks pass).
Not closed: adaptive-attack robustness (comment 12 is PARTIAL: no adaptive attack was implemented); formal differential privacy (epsilon is a diagnostic RDP estimate). The concern in section 4 item 1 is now quantified: in the central-DP pipeline weights are exactly uniform (chi_rec and sample sizes inert), surrogates carry about 30% of the weight, and surrogate-only rounds are 2.8%. Concern 3 (seeds of Figs 3-6) remains until the authors add a statement. Required manuscript corrections are listed in `MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex`; the manuscript was not modified.
