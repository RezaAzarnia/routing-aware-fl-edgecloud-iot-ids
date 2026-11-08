# Manuscript integration checklist and source-version report

## 1. Which main.tex / main.pdf is in the review ZIP?
| item | value |
|---|---|
| `manuscript/main.tex` | git HEAD `7d5280df499e225b936dfbcb5baece79b7d75dba` (branch `main` = `origin/main`, confirmed with `git ls-remote`); file modified 2026-11-07 13:09:21 +0330 (commit 13:11:55 +0330); 97,261 bytes; SHA-256 prefix `4f79c4aa9b9c333b` (full hash in `SHA256_INVENTORY.txt`) |
| `manuscript/main.pdf` | same commit; file written 2026-11-07 13:11:54 +0330; 3,796,475 bytes; SHA-256 prefix `dad1e0638891b44f`; 18 pages |
| working tree | `git status` shows no modification under `manuscript/` |
| Zenodo reference inside it | `\texttt{v1.0.4}`, DOI 10.5281/zenodo.24031823 |

## 2. The v.1.0.5 discrepancy: what I could and could not establish
- **No file I can reach cites v.1.0.5 / 10.5281/zenodo.24032087.** Checked: git HEAD; tag `v.1.0.5` (its own `main.tex`, SHA-256 prefix `460612f4`, also cites v1.0.4 / 24031823); tag `v1.0.4`; the remote (`origin/main` = HEAD, no newer branch); and the manuscript variants in `Downloads` (they cite 24027486 or 21131047 only). The manuscript you call "latest author-reviewed" is therefore **not on this machine or in the GitHub repository**, and Git HEAD must not be treated as that file.
- The patches are therefore **anchor-based, not line-based** (`MANUSCRIPT_PATCHES_C1_C11_ANCHORED.tex`). `scripts/supp_final/check_anchors.py <your main.tex>` prints, per patch, whether it still needs applying, is already applied, or its anchor is missing. Run it on the latest author-approved file first. On Git HEAD all 13 patches apply (none already applied; every anchor found once, except "capped weighting", 9 times). On the older Downloads variants many anchors are missing, as expected for earlier drafts.
- If the latest file differs from HEAD in a targeted paragraph, apply the patch's AFTER text to that paragraph and keep the author's other edits.

## 3. Already present in Git HEAD (do not add again; re-check in the latest file)
- Diagnostic wording for ε in Abstract, Methods, Results and Conclusion.
- Exact sign-flip minimum p = 0.0625 statements (Routing results, Ablation); only these two sentences are refined (C11).
- Conclusion limitation paragraph (simulated network, sign-flip attacker model, validation partitions, ε diagnostic, adaptation as future work).
- Attack-model paragraph: "Other attacks, collusion and adaptive attackers were not evaluated."
- The paragraph after the capped-weight equation already reports 92 %, 0.167, 0.30, max 1.0 and 10 surrogate-only rounds; C3 keeps all of these and adds only the uniform-weight, inertness and abstention content.

## 4. Preserved audited numerics (no patch changes them)
Abstract values; Table 4 v2 (overall results); Table 5 (−0.011/−0.093, −0.309/−0.518, −0.0017/−0.0262, −0.0015/−0.0157, −0.0032/−0.0419; only the caption and the two combined-contrast row labels change, C4); ε̂≈9.999 and ≈10/≈20; NSR values; 92 % / 0.167 / 0.30. QA re-verified the Table 4 v2 (40) and Phase 6C (240) runs against their manifests.

## 5. Statistical language
Everything stays exploratory: exact sign-flip floor 0.0625 at n = 5 (0.25 at n = 3); t-intervals that exclude zero are "unadjusted for multiplicity and exploratory" (about 1,700 comparisons; 338 intervals exclude zero); no significance or superiority claims. See `STATISTICAL_INFERENCE_NOTE.md`.

## 6. Zenodo recommendation (Code and Data Availability)
**Cite the existing latest version, v.1.0.5, DOI 10.5281/zenodo.24032087** (snapshot commit `7d59885`, a descendant of v1.0.4's `e74e2e1`; its tagged tree contains the Table 4 v2 manifest, `TABLE4_V2_PER_SEED/SUMMARY/PAIRED_EFFECTS.csv`, scripts and configs, so the existing Data Availability statement stays true), optionally with the concept DOI 10.5281/zenodo.21131047. The Zenodo version string is `v.1.0.5` (with a dot). Keeping v1.0.4 is also valid, but the DOI and version string must change together. State that the supplementary experiments are **not** in the archive (patch Z). No release was created.

## 7. Integration order
1. Run `check_anchors.py` on the latest author-approved `main.tex`; note patches reported as already applied.
2. Z (availability) and author declarations.
3. C1 → C3 (C2 defines `sec:aggregation-weights`), then C4 → C6, C7, C8, C11.
4. Insert `SUPPLEMENTARY_RESULTS_LATEX.tex` (label `sec:supplementary`) with the chosen tables/figures, then C9 and C10 (they reference it).
5. Recompile (needs `booktabs`), check undefined references and page layout. The shipped `main.pdf` predates all corrections.

## 8. Main text vs supplementary
Main text: C1–C3, C4–C5, C9, and compact T1 + FIG1 and T3 + FIG3. Supplementary: T2/FIG2, T4/FIG4, T5/FIG5, FIG6, FIG7, T6, per-seed CSVs.

## 9. Statements to remove or weaken
"Capped weighting bounds surrogate influence"; any role of χrec or sample size in the DP aggregate; separate attribution to "clipping" and "capping"; generalised robustness; any significance wording derived from intervals; any claim that the supplementary results are archived.

## 10. Outstanding
Author declarations (none in `main.tex`); seeds of existing Figs. 3–6 (placeholder in C10); bibliography and Table 1 verification; adaptive-attack robustness unevaluated; ε diagnostic only; CICIoT2023 sensitivity/scalability n = 3.
