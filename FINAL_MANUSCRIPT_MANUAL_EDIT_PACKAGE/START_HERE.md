# START HERE — manual manuscript-editing package

Purpose: enough verified evidence and ready LaTeX to correct the authoritative manuscript **by hand**, without access to the Git repository. Nothing in this package has been applied to, compiled into, or compared against your latest manuscript. **No copy of any manuscript is included**; upload your latest `main.tex` (and `references.bib`) next to this package.

## 1. Review order
1. `START_HERE.md` (this file), then `EDITING_ORDER.md`.
2. `01_manuscript_corrections/CORRECTIONS_JUSTIFICATION_AND_PRIORITY.md` — every correction with justification, evidence file and affected claim.
3. `01_manuscript_corrections/MANUSCRIPT_PATCHES_C1_C11_ANCHORED.tex` — the exact LaTeX (anchor-based; includes patch Z). `MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex` has the same text against Git HEAD 7d5280d (line numbers valid only there).
4. `02_supplementary_evidence/SUPPLEMENTARY_EXPERIMENTS_FINAL_REPORT.md`, `06_provenance_and_verification/FINAL_SCIENTIFIC_QA_REPORT.md`, `03_statistics/STATISTICAL_INFERENCE_NOTE.md`.

## 2. Mandatory corrections (see the priority file for all)
C1–C6 (aggregation weights, Table 5 labelling and interpretation), C9 (attack-robustness scope), C11 (statistical wording), Z (Zenodo availability), C10 (Figs 3–6 seeds — unresolved, needs author input).

## 3. Findings that support them
- In the central-DP pipeline, with ≤10 retained updates the weights are exactly 1/n (2,750 of 2,750 such rounds); χrec and sample-size weighting are inert there; the cap does not exist in the non-private path.
- Surrogates carry ≈30 % of the DP weight; surrogate-only rounds 2.8 %; no demonstrated detection benefit of imputation.
- Table 5: "Added Gaussian" is a noise-only contrast; the other two privacy rows are combined (clipping + uniform weights [+ noise]).
- χrec = 0 under DP: abstention only in surrogate-only rounds (seed 13: 1; seed 15: 4); ε diagnostic (release-based 9.86/9.43 vs attempted 9.9993), not certified DP.
- Attacks: FedAvg collapses under sign-flip contamination, the pipeline does not; no benefit without attack; no adaptive attack tested.
- Participation: fairer selection did not raise worst-client held-out recall.

## 4. Original claims affected
"Capped weighting" as a robustness/utility component; χrec "lowers influence"; Table 5 row labels "Clipping + cap" and "Full privacy pipeline" and the 53 %/63 % attribution; the contribution bullet on balancing clipping/capping/noise/momentum; the exact-test sentence "no test can reach p<0.05"; Code/Data Availability (v1.0.4 cited; supplementary not archived).

## 5. Must remain unchanged
Abstract numbers; **all Table 4 v2 values**; **all Table 5 numerical values** (−0.011/−0.093, −0.309/−0.518, −0.0017/−0.0262, −0.0015/−0.0157, −0.0032/−0.0419); ε̂≈9.999, ≈10, ≈20; NSR values; 92 %, 0.167, 0.30, max 1.0, 10 surrogate-only rounds. Reference copies of the Table 4 v2 tables are in `06_provenance_and_verification/table4_v2_reference/`.

## 6. Supplementary findings to incorporate
Main text: T1+FIG1 (attacks), T3+FIG3 (routing×surrogate), the weight findings. Supplementary only: the rest (`01_manuscript_corrections/MAIN_VS_SUPPLEMENTARY.md`). Ready LaTeX: `07_publication_ready_latex/` (labels `sec:supplementary`, `sec:aggregation-weights`; needs `booktabs`, `graphicx`).

## 7. Outstanding author declarations / items (not invented here)
Funding, competing interests, CRediT contributions, ethics/data-use statements; seeds of Figs 3–6; bibliography claim verification (22/35 entries lack DOI/URL); Zenodo choice (cite v.1.0.5, 10.5281/zenodo.24032087, recommended; no release exists containing the supplementary results); adaptive-attack robustness unevaluated. Full list: `08_reviewer_materials/UNRESOLVED_LIMITATIONS.md`.

## 8. Folder map
`01_manuscript_corrections/` patches, justification, checklists, maps · `02_supplementary_evidence/` reports, per-seed/summary/paired/holdout CSVs, weight audit, T1–T6 tables · `03_statistics/` inference note · `04_figures/` FIG1–FIG7 PNG+PDF+data CSV, captions · `05_audits/` weight-cap and noise-confounding audits · `06_provenance_and_verification/` QA report and JSON, provenance, locked manifests, Zenodo and bibliography reports, Table 4 v2 reference · `07_publication_ready_latex/` · `08_reviewer_materials/` 20-comment mapping, audit, limitations · `09_code_for_traceability/` analysis scripts (path `scripts/supp_final/check_anchors.py` mentioned in the checklist = `09_code_for_traceability/scripts/supp_final/check_anchors.py`).
Omitted (large): all `results_*` run directories (checkpoints, predictions), datasets, per-run configs (hashes are in the manifests).
Rule for every edit: comparisons are exploratory (exact sign-flip floor 0.0625 at n = 5; intervals unadjusted for multiplicity).
