# Statistical inference: resolution of the "CI excludes 0 vs p cannot be < 0.05" question

**Contrast:** UNSW-NB15 worst eligible-client held-out recall, `part_uniform_indep` minus `part_topk_indep` (SUPP_V1 runs; client holdouts never trained on). Source rows: `SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv` (column `worst_client_recall`), `SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv` (`family=E_participation`).

| seed | top-k / indep. | uniform / indep. | paired difference (uniform − top-k) |
|---|---|---|---|
| 12 | 0.9524 | 0.8000 | −0.1524 |
| 13 | 0.9375 | 0.9259 | −0.0116 |
| 14 | 0.9286 | 0.7143 | −0.2143 |
| 15 | 0.8636 | 0.8000 | −0.0636 |
| 16 | 0.9000 | 0.6543 | −0.2457 |

mean −0.13751, SD 0.09891 (ddof = 1), SE 0.04423, n = 5.

## Methods actually implemented (`scripts/supp_final/analyse_final.py::paired`)
- **Confidence interval:** parametric one-sample t-interval on the paired differences, mean ± t(0.975, df = 4)·SD/√5, t-critical 2.7764 → [−0.2603, −0.0147]. Assumes independent seeds and approximately normal paired differences (not testable with five points; seeds share data splits per seed in pairs only).
- **Hypothesis test (reported):** exact sign-flip (paired randomization) test on the mean difference: all 2⁵ = 32 sign assignments, p = share with |mean| ≥ observed. All five differences are negative, so only the all-negative and all-positive assignments are as extreme: p = 2/32 = **0.0625**, the minimum attainable at n = 5.
- **Not reported in the files, computed here for this note:** one-sample t-test on the same differences, t = −3.109, df = 4, two-sided p = **0.0359**. A 95 % t-interval excluding 0 is equivalent to this t-test having p < 0.05.

## Are the statements consistent?
Yes, but my earlier sentence "no contrast can reach p < 0.05" was **too broad and is corrected**. It is true only for the *exact sign-flip test* (floor 0.0625 at n = 5, 0.25 at n = 3). The t-interval/t-test is a different procedure with a normality assumption and can give p < 0.05 for the same data (here 0.0359). Across the paired-effects table, 338 of 1,743 rows (321 with n = 5, 17 with n = 3) have a t-interval excluding 0, and all of those have t-test p < 0.05 while none has an exact p below 0.0625.

## Correct interpretation (applied to the reports; no observation changed)
- All five seeds show a lower worst-client recall under uniform selection (−0.012 to −0.246): a consistent direction, large and heterogeneous in size.
- The t-interval excludes 0, but (i) the exact test does not support p < 0.05, (ii) normality is unverifiable, and (iii) ≈1,700 comparisons were computed without multiplicity adjustment, so a few interval exclusions are expected by chance. Such rows are labelled "interval excludes zero (unadjusted, exploratory)"; **no claim of statistical significance or superiority** is made. CICIoT2023 shows no such difference (−0.006 [−0.088, +0.076]).
- Files corrected: `SUPPLEMENTARY_EXPERIMENTS_FINAL_REPORT.md` (Statistics paragraph), `SUPPLEMENTARY_RESULTS_LATEX.tex` (opening paragraph), `SUPPLEMENTARY_EXPERIMENTS_REVIEWER_MAPPING.md` (#11), `FINAL_REVIEWER_AUDIT.md` (#15). Table T2's caption already stated "no claim of statistical significance".
