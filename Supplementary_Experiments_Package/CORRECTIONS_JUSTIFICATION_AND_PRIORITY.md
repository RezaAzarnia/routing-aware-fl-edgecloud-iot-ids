# Corrections C1–C11 and Z — justification, evidence, affected claims, priority

Nothing here has been applied to any manuscript. Evidence paths are relative to this package (`FINAL_MANUSCRIPT_MANUAL_EDIT_PACKAGE/`). Patch text: `01_manuscript_corrections/MANUSCRIPT_PATCHES_C1_C11_ANCHORED.tex` (anchor-based; use this for the latest manuscript) and `MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex` (line-numbered against Git HEAD 7d5280d only).
Statistical rule for all edits: comparisons are exploratory; exact sign-flip floor p = 0.0625 (n = 5); intervals excluding zero are unadjusted for multiplicity.

## Priority A — MANDATORY (the current text is inaccurate or misleading without them)
| ID | Manuscript section (search anchor) | Affected claim | Scientific justification | Evidence |
|---|---|---|---|---|
| C3 | Privacy-Aware Aggregation, paragraph after eq. `eq:capped-weighting` ("When fewer than 1/a_max=10 updates are retained…") | cap "does not prevent" surrogate influence; implies weights are shaped by n_i / χrec | In the central-DP path, with ≤10 retained updates the cap is infeasible and CapNormalize returns exactly 1/n; verified on 2,750 such rounds (max deviation 1.4e-16); sample sizes and χrec therefore cannot influence the applied weights; χrec=0 reproduces the reference bit-for-bit unless a round abstains | `05_audits/AUDIT_capnormalize_unit_test.csv`, `AUDIT_recorded_weights_*.csv`, `02_supplementary_evidence/SUPPLEMENTARY_WEIGHT_AUDIT_FINAL.csv`, `FINAL_SCIENTIFIC_QA_REPORT.md` check 6 |
| C2 | same section, paragraph "Before normalization, the raw aggregation weight…" | text implies a cap in all pipelines | the cap exists only in the central-DP aggregation path; the non-private path uses uncapped n_i·χrec weights (largest share up to 0.51) | `05_audits/AUDIT_recorded_weights_summary.csv` (non-DP arms: 0 uniform rounds), `src/experiment.py` branch at the `private_weights` assignment (described in the audit report) |
| C1 | Failure Recovery and Robust Update Filtering, "The recovered updates are assigned a reduced raw aggregation coefficient…" | χrec "lowers influence" | true only in the non-private path; inert under DP | same as C3; `04_findings/chi0_abstention` (T6): seeds 12/14/16 identical to reference |
| C4 | Table `tab:ablation-summary` caption and rows "Clipping + cap", "Full privacy pipeline" (**numbers unchanged**) | labels imply single-mechanism effects | "Added Gaussian" differs only in noise (identical weights/clipping/traces 5/5); the other two rows also switch from heterogeneous to uniform weights, and enable the DP aggregation path/clipping (95–100 % of updates clipped) | `05_audits/AUDIT_ablation_config_differences.csv`, `AUDIT_ablation_weights_summary.csv`, `AUDIT_ablation_contrasts_auc_best.csv` |
| C5 | text after Table 5 ("The ordered privacy comparison…", "53 % and 63 %") | non-noise stage attributed to "clipping and capped weighting" separately | combined, not separable | same as C4 |
| C6 | Privacy Diagnostics closing paragraph ("Accordingly, privacy-related utility changes…") | same attribution | same | same |
| C9 | Adversarial Robustness subsection (UNSW sign-flip) | robustness evidence is one 20 % setting | add scope: static attacks only; pipeline vs FedAvg gain only under sign-flip contamination; parity without attack; BSF/LF harmless here; no adaptive attacker | `02_supplementary_evidence/TABLE_T1_attack.csv`, `figures/FIG1_*`; paired file `family=A_attack` |
| C11 | Routing results ("no two-sided exact sign-flip test can reach p<0.05") and Ablation ("minimum attainable p-value of 0.0625") | statement is true only for the exact test; t-intervals can exclude 0 | `STATISTICAL_INFERENCE_NOTE.md` (UNSW worst-client recall: t-test p = 0.036 vs exact p = 0.0625) | `03_statistics/STATISTICAL_INFERENCE_NOTE.md` |
| Z | Code Availability / Data Availability | cites v1.0.4; no archive contains the supplementary experiments | Zenodo API: v.1.0.5 (24032087) is the latest; neither version contains SUPP_V1/V2; do not claim they are archived | `06_provenance_and_verification/ZENODO_VERIFICATION.md` |
| C10 | participation / Figs 3–6 | seeds of Figs 3–6 unstated | provenance unresolved (see `FIGURES_3_6_SEED_PROVENANCE.md`); do not guess | same |

## Priority B — STRONGLY RECOMMENDED
| ID | Section | Why | Evidence |
|---|---|---|---|
| C7 | Contributions bullet "Clipping, capped weighting, central Gaussian noise, and server momentum…" | contribution claims a balance among components that were evaluated only as a bundle | as C4 |
| C8 | first mention of "capped weighting" (Abstract, Intro, Method overview, aggregation opening, Simulation) | "capped" is uniform averaging in practice | as C3 |
| (new section) | `SUPPLEMENTARY_RESULTS_LATEX.tex` | answers reviewer comments 5, 7, 12, 13, 15 with 5-seed evidence | `MAIN_VS_SUPPLEMENTARY.md` |
| Surrogate wording | wherever surrogate imputation/recovery is credited with a benefit | no demonstrated detection benefit: imputation ON vs OFF ΔAUC +0.0016 [−0.0036, +0.0068] UNSW, +0.0001 CIC; surrogates carry ≈30 % of weight in the DP pipeline | `TABLE_T3_interaction.csv`, paired file `family=5_surrogate` |

## Priority C — OPTIONAL
Move T2/T4/T5/T6 and FIG2/4/5/6/7 into a Supplementary Material file only; add the abstention/accounting sentence (release-based ε 9.86 / 9.43 vs attempted 9.9993, both diagnostic).

## What must remain unchanged
Abstract numbers; Table 4 v2 values; Table 5 values (−0.011/−0.093, −0.309/−0.518, −0.0017/−0.0262, −0.0015/−0.0157, −0.0032/−0.0419); ε̂≈9.999 / 10 / 20; NSR values; 92 %, 0.167, 0.30, max 1.0, 10 surrogate-only rounds. QA verified Table 4 v2 (40 runs) and Phase 6C (240 runs) byte-unchanged.

## Claims that must not be made
Certified differential privacy; adaptive-attack robustness; a demonstrated detection benefit of surrogate imputation; significance/superiority from unadjusted intervals; that the supplementary results are publicly archived.
