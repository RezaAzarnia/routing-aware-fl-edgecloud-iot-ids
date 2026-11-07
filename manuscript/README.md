# Manuscript (Table 4 v2 revision)

* `main.tex`, `references.bib`, `images/`: corrected manuscript supplied by the author (source file `main_Table4_V2_CopyPaste_Once_18pages.tex`, 7 Nov 2026) with the figure set and bibliography of the matching layout package.
* Build: `latexmk -pdf main.tex` (elsarticle, pdfLaTeX). Result at commit time: 18 pages, no undefined citations or references, no BibTeX warnings. The PDF is not committed (ignored by `.gitignore`).
* Table 4 values equal `Table4_V2_Package/TABLE4_V2_FINAL_TABLE.tex` (40 verified controlled runs, seeds 12-16).
* Zenodo: record 10.5281/zenodo.24027486 (v.1.0.3) snapshots tag `v.1.0.3` = commit `1df63f3`, which predates the Table 4 v2 code, configs, manifest and tables. Code/Data Availability in `main.tex` state exactly this. A new release + Zenodo version is needed before claiming those are archived.
* `Phase9_Manuscript_Revision/latex/` is an earlier manuscript and is left unchanged.
