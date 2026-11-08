# Manuscript readiness map (manuscript/main.tex at HEAD 7d5280d; NOT modified)

Line numbers refer to `manuscript/main.tex` at HEAD. Corrections C1–C11 are in `MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex`.

## 1. C1–C11 → exact manuscript locations
| C | Section (line) | Action | Type |
|---|---|---|---|
| C1 | Failure Recovery and Robust Update Filtering (line 848, χrec sentence) | replace sentence: cap/χrec role differs between non-private and DP path | weaken/qualify |
| C2 | Privacy-Aware Aggregation (lines 958–963, raw weights; add label `sec:aggregation-weights`) | state that the cap exists only in the central-Gaussian path; non-private weights uncapped | rewrite |
| C3 | (line 992, after eq. `eq:capped-weighting`) | add: weights exactly 1/n for ≤10 retained; χrec/sample size inert; surrogate share 0.30; abstention rule; "3.3 % of rounds" | replace paragraph |
| C4 | Other Components and Privacy-Pipeline Effects, Table `tab:ablation-summary` (lines ~2100–2118) | rename "Clipping + cap" / "Full privacy pipeline"; caption: Gaussian-only vs combined | relabel |
| C5 | same subsection (lines ~2121–2135) | rewrite interpretation paragraph: only "Added Gaussian" is single-mechanism | replace |
| C6 | Privacy Diagnostics (lines ~2232–2238, "Accordingly…") | replace paragraph; keep ε diagnostic wording | replace |
| C7 | Contributions, bullet at line 273 | "capped (in practice uniform…) weighting … evaluated as a bundle" | weaken |
| C8 | Abstract (lines 85–92), (line 248), Proposed Method overview (line 660), opening (line 931), Simulation (line 1252) | first mention qualifies "capped weighting" for the DP path | qualify |
| C9 | "Adversarial Robustness under Sign-flip Poisoning" (line 1855) and Conclusion (line 2241 ff.) | add static-attack scope, FedAvg-vs-pipeline contrast, no-attack parity, ~30 % surrogate share, no adaptive attack; new Limitations paragraph (there is no Limitations section — create one before the Conclusion) | add |
| C10 | Routing results / Figs 3–6 (lines ~1874–2010, captions) | state seeds of Figs 3–6; refer to supplementary participation study | add |
| C11 | Abstract (line 90) and Conclusion (~2248) | numbers unchanged; add "diagnostic" next to ε and "static" next to robustness | wording only |
| (new) | Code Availability (2273–2281) and Data Availability (2283–2294) | see item 4 below (Zenodo) | author decision |

## 2. Statements to remove or weaken
- "capped weighting limits/bounds influence" (line 848 context and any similar) — only true in the DP path and there it is uniform averaging.
- Any implication that χrec or sample-size weighting shapes the DP aggregate (Failure Recovery and Privacy-Aware Aggregation sections, Table 3 `a_max`/`χrec` rows at ~1693: add "inert in the DP pipeline").
- "Clipping and capped weighting contribute…" as separate mechanisms (C4–C6).
- Any sentence reading the sign-flip result as general robustness; scope to static attacks.
- Any "significant"/"superior" language derived from intervals; the exact test floor is 0.0625 (see `STATISTICAL_INFERENCE_NOTE.md`).

## 3. Numerical results that must stay unchanged
Abstract and Conclusion headline values (CICIoT2023 F1 0.9914 / AUC 0.9937 at ε̂≈20; delay 87.3 ms comparison; UNSW F1 0.9065), Table 4 v2 values, Table 5 numbers (−0.011/−0.093, −0.309/−0.518, −0.0017/−0.0262, −0.0015/−0.0157, −0.0032/−0.0419 — only labels change), ε̂≈9.999, NSR values, the 92 % rounds with <10 retained, max weight 0.167, surrogate share 0.30. QA verified Table 4 v2 and Phase 6C evidence are byte-unchanged (40 + 240 runs re-verified).

## 4. Zenodo / availability (author decision)
Manuscript cites v1.0.4 (10.5281/zenodo.24031823). A later v.1.0.5 (10.5281/zenodo.24032087) also exists. Neither contains the supplementary experiments. Do not state that supplementary results are archived until a release containing them is made (not done). See `ZENODO_VERIFICATION.md`.

## 5. What to integrate in the main paper vs keep supplementary
Main paper (short, one new subsection "Supplementary controlled experiments" or a compact Table + 2 figures): T1 + FIG1 (attack robustness, with the FedAvg collapse and no-attack parity); T3 + FIG3 (routing × surrogate, replaces the unresolved surrogate claim); T6 (χrec=0 abstention + accounting) only as a sentence; the uniform-weight finding as text (C1–C3).
Supplementary only: T2 + FIG2 (sensitivity), T4 + FIG4 (participation, held-out recall), T5 + FIG5 (scalability/cost; wall-times are shared-host indicative), FIG6, FIG7, per-seed/paired CSVs, audits.

## 6. Outstanding author declarations and reviewer limitations
- Missing: funding, competing interests, CRediT contributions, ethics/data-use statements (comment 19; no such section exists in `main.tex`).
- Bibliography claims and Table 1 capability entries need author verification (comments 1, 16).
- Adaptive-attack robustness not evaluated (comment 12 PARTIAL); formal DP not proven; reserved test sets unmeasured; CICIoT2023 official provenance unverified; CIC sensitivity/scalability n = 3; coupled-network driver used holdout labels (disclosed); Figs 3–6 seeds unstated.
- `manuscript/main.pdf` at HEAD was compiled before these corrections; recompile after integration.

## 7. Integration order
1. Decide Zenodo/availability wording (item 4 above) and add author declarations.
2. Apply C1→C3 (aggregation description) — they define label `sec:aggregation-weights` used by the supplementary text.
3. Apply C4→C6 (Table 5/Privacy Diagnostics), then C7–C8, C11.
4. Insert `SUPPLEMENTARY_RESULTS_LATEX.tex` (+ chosen tables/figures; copy `figures/` and add `\usepackage{booktabs}` if absent) and C9–C10.
5. Recompile, check labels/refs, rerun page review.
