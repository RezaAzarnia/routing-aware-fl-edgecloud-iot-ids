# Phase 9B audit of the revised manuscript (`Phase9_Manuscript_Revision/latex/main.tex`, 24 pages)

Read-only; no training, no experiment, no test-data access. Evidence re-derived independently of the ledger builder.

## 1. Numerical claims
`Phase9B_Review/scripts/verify_manuscript_numbers.py` re-computes every hand-typed in-text number directly from `results_phase6c/*/*/seed_*/` run folders (route/network/fairness metrics, payload bytes), from `posthoc_threshold_fix/phase6c_posthoc_with_deltas.csv` (audited per-run metrics) and from the Phase 7b per-run table: **93 checks, 0 failures** after the two corrections below.
Corrections made by this audit:
* Relative PDR gain of top-k over uniform: **+8.9 %** (not 8.8 %; computed from unrounded values) — main text, CLAIM_EVIDENCE_MATRIX and CHANGELOG fixed.
* Audit effect on last-round metrics: **17** Phase 6C runs change by >0.001 in last-round AUC or F1 (AUC in 12 runs, >0.01 in 7), not "12 runs change materially" — manuscript text and matrix fixed.
Tables 2-8 are generated from the ledgers (no hand-typed table values); Table 1 from the configuration matrix.

## 2. Equations versus code (verified against `src/`)
| Item | Code evidence | Verdict |
|---|---|---|
| Route score $s_{ie}=0.4\bar\ell^{-1}+0.3\bar\rho+0.3\bar q$, argmax over 3 edges; path latency = sum, stability = product, security = min, bandwidth = min | `src/network.py` `update_round`, `_normalize` | match |
| Top-k ranking key $(s,q,-\ell)$; coverage-aware $s-\lambda n_i/(t-1)$, $\lambda=0.5$ | `select_clients`, `select_clients_coverage_aware` (denominator `max(1, round-1)`) | match |
| Link drift ($\sigma=0.025$; stability uses $\sigma/2$, security $\sigma/3$; latency multiplicative clipped to [0.8,1.2]) and outage 0.01 (stability ≤0.05) | `_evolve` | match (text gives only $\sigma$; finer detail not stated) |
| Independent-draw delivery Binomial$(100,\rho)$ + separate Bernoulli$(\rho)$; packet-coupled geometric attempts, ≤3 transmissions, delivered iff all packets, PDR at first transmission, retransmission delay $2\ell$ per round | `simulate_transfer`, `_simulate_coupled` | match |
| Surrogate = coordinate-wise median of healthy updates, ≥2 required, weight $0.5\,n_i$; pre-filter (Reference) vs post-filter from retained genuine updates (Corrected) | `src/recovery.py`, `src/experiment.py` l.847-870 | match |
| MAD filter: keep $d_i\le \mathrm{med}+k(1.4826\,\mathrm{MAD}+10^{-12})$, fallback argmin, weighted mean of kept | `src/aggregation.py` `distance_filter_indices` | match |
| Momentum $v\leftarrow\mu v+\bar\Delta$, $w\leftarrow w+\eta v$; empty round leaves model and buffer unchanged | `src/server.py` `apply_update`; `apply_update` is called only inside `if updates and not aggregation_skipped` | match |
| Gaussian noise std $z\,C\max_i a_i$ (adjacency 1), clip 0.1, per-client cap 0.1 projection | `src/experiment.py` ~l.958-1000, `src/privacy.py` | match |
| Threshold rule (max recall s.t. FPR≤0.15, recall≥0.6; tie-breaks) | `src/metrics.py` `select_decision_threshold` | match |
| Sign-flip update $-5\Delta$ on 2 of 10 selected clients per round (exposure-controlled) | `src/attacks.py`, `src/experiment.py` l.726-733 | match |
Wording fixed: "exposure-controlled (default …)" → used in all arms except natural-attacker arms (the code default is `natural_fixed_clients`).

## 3. Figures and captions
Figures 1-7 were rendered to PNG and inspected: no overlapping or clipped text; captions agree with the data (Fig. 3 "not better in any seed" = 0/5 wins; Fig. 4 AUC panel axis truncated 0.96-0.99 and stated in the caption; Fig. 6 guard removes the seed-17 collapse and creates one in seed 19). Fonts are embedded Type 1/42 in PDF. SVG text is live text (not outlined). Minor: the AUC panel of Fig. 4 uses bars on a truncated axis (stated in caption; dots would be cleaner) — optional.

## 4. Provenance mixing (original / audited / new)
* Every metric in the text and tables is the **audited** value (re-evaluated checkpoints, single decision rule); the original values live only in `ledger_per_run_phase6c.csv` (`*_original` columns) and are named as such.
* Exceptions that quote *original-protocol* numbers, now labelled: (i) §7.3 "4.63 vs 5.93 genuine kept updates, surrogate share 0.096 vs 0.221" comes from the Phase 6C handoff report (training-side quantities, unaffected by the metric defect); (ii) the removed old-manuscript percentages are quoted only as "not retained".
* Phase 6C (seeds 12-16) and Phase 7b (seeds 17-21) are never pooled; Phase 7b arms were re-run, so the two sets are not mixed in any statistic.
* Corrected-versus-Reference numbers differ slightly from the Phase 6C handoff (e.g. UNSW best Δ −0.0082 vs −0.0090) because the handoff used original metrics; the manuscript uses the audited ones.

## 5. Remaining text risks found
1. §Threats (2) and the reproducibility paragraph must not say "never accessed" for the locked test files — fixed (see `LASTACCESSTIME_FORENSICS.md`).
2. Related-work scope and wording corrected (14 full texts, 15 abstracts, 6 metadata-only; "survey" no longer applied to non-surveys; aburukba described as scheduler fault tolerance; liu2026reliability/tang2026fedcst stated as unread).
3. Eight bibliography entries are verified but **uncited** in the text (carillo2026incremental, zhang2026endpca, s2dfl2026, albogami2025deepfl, padmavathi2025trust, wang2026desa, wang2024trust, bayat2025qlearning) — BibTeX omits them from the printed list; cite or drop deliberately.
4. Not an error but a presentational risk: 12-pt single-column preprint layout (24 pages), not a journal template.
