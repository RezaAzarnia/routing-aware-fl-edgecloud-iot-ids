# Manuscript (Table 4 v2 revision)

* `main.tex`, `references.bib`, `images/`: corrected manuscript supplied by the author (source file `main_Table4_V2_CopyPaste_Once_18pages.tex`, 7 Nov 2026) with the figure set and bibliography of the matching layout package.
* Build: `latexmk -pdf main.tex` (elsarticle, pdfLaTeX). Result at commit time: 18 pages, no undefined citations or references, no BibTeX warnings. The PDF is not committed (ignored by `.gitignore`).
* Table 4 values equal `Table4_V2_Package/TABLE4_V2_FINAL_TABLE.tex` (40 verified controlled runs, seeds 12-16).
* Zenodo: release v1.0.4, DOI 10.5281/zenodo.24031823 (tag `v1.0.4`, commit `e74e2e1`), verified to contain the Table 4 v2 manifest, scripts and per-seed/summary/paired tables. Raw per-run outputs are not published. `main.tex` Code/Data Availability state exactly this. No further release was created.
* `Phase9_Manuscript_Revision/latex/` is an earlier manuscript and is left unchanged.
