# Independent-review package — SUPP_V1 + SUPP_V2 supplementary experiments

Nothing in this package modifies the manuscript. All experiments are finished (SUPP_V1: 246 verified, frozen; SUPP_V2: 44/44 verified); no experiment was run to produce it.

## Read in this order
1. `SUPPLEMENTARY_EXPERIMENTS_FINAL_REPORT.md` — consolidated findings, unresolved items, readiness.
2. `STATISTICAL_INFERENCE_NOTE.md` — how intervals/tests were computed; resolves the CI-vs-p question (exact sign-flip floor 0.0625 vs t-interval).
3. `FINAL_SCIENTIFIC_QA_REPORT.md` + `FINAL_QA_RESULTS.json` (53/53 pass) + `V2_ABSTENTION_AND_ACCOUNTING_PER_RUN.csv`.
4. `ZENODO_VERIFICATION.md` — v1.0.4 (24031823) vs v.1.0.5 (24032087); supplementary outputs not archived.
5. `SUPPLEMENTARY_EXPERIMENTS_REVIEWER_MAPPING.md` and `FINAL_REVIEWER_AUDIT.md` — 20 comments: 11 CLOSED / 8 PARTIAL / 1 OPEN.
6. `MANUSCRIPT_READINESS_MAP.md` and `MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex` (C1–C11).
7. `SUPPLEMENTARY_RESULTS_LATEX.tex`, `SUPPLEMENTARY_TABLES_GENERATED.tex`, `GENERATED_TABLES.md`, `figures/` (FIG1–FIG7 as PNG/PDF + `*_data.csv`).
8. Data: `SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv` (352 identity rows, run IDs, source, manifest hash), `_SUMMARY.csv`, `_PAIRED_EFFECTS.csv`, `SUPPLEMENTARY_HOLDOUT_*.csv`, `SUPPLEMENTARY_WEIGHT_AUDIT_FINAL.csv`, `SUPPLEMENTARY_EXPERIMENTS_PROVENANCE.json`, `audits/`.
9. `manuscript/` — authoritative source `main.tex`, `references.bib` and `main.pdf` at git HEAD 7d5280d (the PDF predates the corrections).
10. `code/` — `scripts/supp_final` (QA/analysis), `src_v2/` overlay, `manifests/` (locked V1 and V2 manifests).

## Source-version caveat
The manuscript in this ZIP is Git HEAD 7d5280d (cites Zenodo v1.0.4). No accessible file cites v.1.0.5; the latest author-approved file must be patched with `MANUSCRIPT_PATCHES_C1_C11_ANCHORED.tex` after running `code/scripts/supp_final/check_anchors.py`. See `MANUSCRIPT_INTEGRATION_CHECKLIST.md`.

## Integration order for the manuscript
Zenodo/declarations decision → C1–C3 → C4–C6 → C7, C8, C11 → insert supplementary section + C9, C10 → recompile.

## Omitted large artifacts (not in the ZIP; present in the working tree, gitignored)
`results_supplementary_v1/`, `results_supplementary_v2/` (per-run directories: model checkpoints, validation predictions, preprocessors; several GB), `results_phase6c/`, `results_table4_controlled_v2/`, the datasets under `data/`, and the 64 + 12 config YAML files (hashes are in the manifests). Reproduce QA with `python scripts/supp_final/final_qa.py` in the working tree.

## Known caveats
ε values are diagnostic RDP estimates; no adaptive attacker was evaluated; CICIoT2023 sensitivity/scalability use 3 seeds; wall-clock values come from a shared host; author declarations are absent from the manuscript.
