# Recommended manual editing order

0. Work on a copy of your latest `main.tex`. Run `09_code_for_traceability/scripts/supp_final/check_anchors.py main.tex` (optional) to see which patches are already applied; otherwise search each patch's LOCATE text by hand.
1. **Z — Code/Data Availability.** Choose the Zenodo version (recommended v.1.0.5, 10.5281/zenodo.24032087); state that the supplementary experiments are not in the archive.
2. **Author declarations** (funding, competing interests, CRediT, ethics) — authors supply the content.
3. **C2 → C3 → C1** (aggregation description). C2 introduces `\label{sec:aggregation-weights}`.
4. **C4 → C5 → C6** (Table 5 caption/row labels — values untouched; interpretation; Privacy Diagnostics paragraph).
5. **C7, C8** (contribution bullet; first mention of "capped weighting").
6. **C11** (two exact-test sentences; confirm the diagnostic-ε wording is already present).
7. Insert `07_publication_ready_latex/SUPPLEMENTARY_RESULTS_LATEX.tex` (+ chosen tables/figures, labels `sec:supplementary`, `fig:supp-*`, `tab:supp-*`); copy `04_figures/*.pdf`.
8. **C9, C10** (they reference the supplementary section). For C10 first resolve the Figs 3–6 seeds (`01_manuscript_corrections/FIGURES_3_6_SEED_PROVENANCE.md`).
9. Compile (needs `booktabs`); fix undefined references; check page layout and that Tables 4/5 numbers are byte-identical to your pre-edit file.
10. Re-read for forbidden claims: certified DP, adaptive-attack robustness, demonstrated surrogate benefit, significance from unadjusted intervals, archived supplementary results.
