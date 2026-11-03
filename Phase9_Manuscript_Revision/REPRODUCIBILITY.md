# Reproducing the Phase 9 manuscript artifacts (no training is needed)

Everything below reads existing, locked outputs; nothing retrains and nothing writes to `results_*`.

```powershell
$PY = "C:\Users\R_Azarnia\Desktop\IoT-FL-Recovery\venv\Scripts\python.exe"   # Python 3.11 with numpy, pandas, scipy, matplotlib
# 1. Phase 8 audit tables (reads results_phase6c, results_phase7b, posthoc_threshold_fix)
& $PY scripts\phase8\phase8_tables.py
# 2. Ledger + figures (PDF and SVG, with source CSVs)
& $PY Phase9_Manuscript_Revision\scripts\build_ledger_and_figures.py
# 3. LaTeX tables generated from the ledger
& $PY Phase9_Manuscript_Revision\scripts\make_latex_tables.py
# 4. Build the PDF (MiKTeX: pdflatex + bibtex; latexmk needs Perl and is not required)
cd Phase9_Manuscript_Revision\latex
pdflatex main.tex; bibtex main; pdflatex main.tex; pdflatex main.tex
```

Verification of the underlying experiments (read-only):
```powershell
& $PY Phase9_Manuscript_Revision\scripts\verify_runs.py   # Phase 6C 240/240; Phase 7b 40/80 (mandatory tier); Phase 7 13/80 (historical)
& $PY -m pytest tests -q --basetemp=C:/cs/p9      # 155 tests; use a short basetemp on Windows
```
Frozen code states: git tags `phase6c-final-results`, `phase7-guard-v1`, `phase7b-final-results`; Phase 8 commit `740a166`; Phase 9 commit recorded in `PROVENANCE.md`.

Raw datasets and `data/CICIoT2023/` are not part of the repository (git-ignored/untracked). UNSW-NB15 training CSV SHA-256 `bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa`; CICIoT2023 prepared-set content hashes are in `docs/phase6c/EXPERIMENT_MANIFEST.json`. Final-test files are never read by any script in this folder.

Optional (needs authorization, not part of the manuscript): the 15-run Gaussian group-cap experiment (`docs/phase8/NEXT_EXPERIMENT_PLAN.md`) and the final-test evaluation (`FINAL_TEST_EVALUATION_PLAN.md`).
